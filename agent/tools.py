import os
import subprocess
import difflib
import json
from typing import List, Optional, Tuple
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax

console = Console()

class ToolRegistry:
    """
    Manages available tools and tracks state (e.g. which files have been read).
    Enforces 'Read-Before-Write' safety.
    """
    def __init__(self, work_dir: str = "."):
        self.work_dir = Path(work_dir).resolve()
        self.read_files = set()  # Tracks absolute paths of files that have been read

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to work_dir."""
        p = (self.work_dir / path).resolve()
        if not str(p).startswith(str(self.work_dir)):
            # Simple jailbreak protection, though we are local agent so less critical
            # but good for safety.
            pass 
        return p

    def list_files(self, path: str = ".") -> str:
        """List files in a directory."""
        target = self._resolve_path(path)
        if not target.exists():
            return f"Error: {path} does not exist."
        
        try:
            # Git-style ignore could be added here, for now simple list
            files = [f.name for f in target.iterdir()]
            output = []
            for f in sorted(files):
                is_dir = (target / f).is_dir()
                output.append(f"{f}{'/' if is_dir else ''}")
            return "\\n".join(output)
        except Exception as e:
            return f"Error listing {path}: {str(e)}"

    def read_file(self, path: str) -> str:
        """Read a file's content. Marks it as 'read'."""
        target = self._resolve_path(path)
        if not target.exists():
            return f"Error: File {path} not found."
        
        if target.is_dir():
            return f"Error: {path} is a directory."

        try:
            content = target.read_text(encoding='utf-8')
            self.read_files.add(str(target))
            return content
        except Exception as e:
            return f"Error reading {path}: {str(e)}"

    def write_file(self, path: str, content: str) -> str:
        """Write content to a file. Requires file to be read first if it exists."""
        target = self._resolve_path(path)
        
        # Policy: Must read before write/modify
        if target.exists() and str(target) not in self.read_files:
            return f"POLICY ERROR: You must read '{path}' before writing to it."
        
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
            # Auto-mark as read since we just wrote it
            self.read_files.add(str(target))
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing to {path}: {str(e)}"

    def apply_diff(self, path: str, diff_content: str) -> str:
        """Apply a unified diff to a file."""
        target = self._resolve_path(path)
        
        if not target.exists():
            return f"Error: Cannot apply diff, file {path} does not exist."

        if str(target) not in self.read_files:
            return f"POLICY ERROR: You must read '{path}' before applying updates."

        try:
            original = target.read_text(encoding='utf-8').splitlines(keepends=True)
            
            # Use regex to just find the blocks, ignore exact marker count/spacing in pre-check
            import re
            # Match roughly <<<< SEARCH ... ==== ... >>>> REPLACE
            # We use this check to trigger the block parser
            if re.search(r'<{3,}\s*SEARCH', diff_content):
                return self._apply_search_replace(target, original, diff_content)
            
            return "Error: Please use the <<<<<<< SEARCH / ======= / >>>>>>> REPLACE format for edits."

        except Exception as e:
            return f"Error patching {path}: {str(e)}"
    
    def _apply_search_replace(self, target: Path, original_lines: List[str], diff_content: str) -> str:
        """
        Applies a Search/Replace block with valid whitespace matching and robust parsing.
        """
        import re
        # Robust regex:
        # 1. <{3,} allows 3 or more <
        # 2. \s* allows spaces before SEARCH
        # 3. (?: .*)? allows trailing text on marker line
        # 4. \s* after marker consumes newline
        pattern = re.compile(
            r'<{3,}\s*SEARCH(?:[^\n]*)\n(.*?)\n={3,}(?:[^\n]*)\n(.*?)\n>{3,}\s*REPLACE', 
            re.DOTALL
        )
        match = pattern.search(diff_content)
        
        if not match:
            # Fallback for when there is NO newline after markers (rare but happens)
            # Try looser match
            pattern_loose = re.compile(
                r'<{3,}\s*SEARCH.*?\n(.*?)\n={3,}.*?\n(.*?)\n>{3,}\s*REPLACE', 
                re.DOTALL
            )
            match = pattern_loose.search(diff_content)

        if not match:
             return "Error: Invalid Search/Replace format. Ensure you have the headers exactly."
        
        search_block = match.group(1)
        replace_block = match.group(2)
        
        original_text = "".join(original_lines)
        
        # 1. Try exact match
        if search_block in original_text:
            new_text = original_text.replace(search_block, replace_block, 1)
            target.write_text(new_text, encoding='utf-8')
            return "Successfully applied edit (exact match)."

        # 2. Try normalized whitespace match
        def normalize(text):
            return "\\n".join([line.strip() for line in text.splitlines() if line.strip()])
            
        norm_search = normalize(search_block)
        
        src_lines = [line.strip() for line in original_lines]
        search_lines = [line.strip() for line in search_block.splitlines()]
        search_lines_no_empty = [l for l in search_lines if l]
        
        if not search_lines_no_empty:
             return "Error: Search block is empty or only whitespace."

        found_at_line = -1
        n_search = len(search_lines)
        
        # Heuristic: try to align the stripped search block with stripped source lines
        # We need to match the sequence of search_lines (which includes empty lines? no, let's match non-empty)
        # Actually, let's stick to the sliding window of exact lines (stripped) we used before
        # But we must be careful about whether search_lines includes the empty ones.
        
        # If search block has:
        # Line A
        #
        # Line B
        #
        # It's safest to match that exact sequence of (A, empty, B).
        
        for i in range(len(src_lines) - n_search + 1):
             window = src_lines[i:i+n_search]
             if window == search_lines:
                 found_at_line = i
                 break
        
        if found_at_line != -1:
             prefix = original_lines[:found_at_line]
             # We need to know how many lines to replace in ORIGINAL. 
             # n_search is just the number of lines in search block. 
             # Does it map 1:1 to original lines? Yes, because we mapped src_lines 1:1.
             suffix = original_lines[found_at_line+n_search:]
             
             new_content = "".join(prefix) + replace_block + "\\n" + "".join(suffix)
             target.write_text(new_content, encoding='utf-8')
             return "Successfully applied edit (whitespace-relaxed match)."

        return "Error: Search block not found in file. Ensure exact match (or check your indentation)."

    def run_command(self, command: str) -> str:
        """Run a shell command."""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=self.work_dir, 
                capture_output=True, 
                text=True,
                timeout=60 # Safety timeout
            )
            stdout = result.stdout
            stderr = result.stderr
            return_code = result.returncode
            
            output = f"Exit Code: {return_code}\\n"
            if stdout:
                output += f"STDOUT:\\n{stdout}\\n"
            if stderr:
                output += f"STDERR:\\n{stderr}\\n"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
        except Exception as e:
            return f"Error running command: {str(e)}"
    
    def grep_files(self, pattern: str, path: str = ".") -> str:
        """Recursive search for text."""
        return self.run_command(f"grep -r '{pattern}' {path}")

    def search_web(self, query: str) -> str:
        """Search the internet for documentation or help using ddgr (CMD line)."""
        if not query or not query.strip():
            return "Error: Empty search query."

        # Check if ddgr is installed
        check = subprocess.run("which ddgr", shell=True, capture_output=True, text=True)
        if check.returncode != 0:
             user_bin = os.path.expanduser("~/.local/bin/ddgr")
             if os.path.exists(user_bin):
                 cmd_base = user_bin
             else:
                return "Error: `ddgr` tool not found. Please install it with `pip install --user ddgr`."
        else:
            cmd_base = "ddgr"

        try:
            # -n 3: 3 results
            # --json: json output
            # --unsafe: might help with some blocks? No, let's keep it safe.
            # Use valid header to avoiding blocking? ddgr handles this usually.
            command = [cmd_base, "--json", "-n", "3", query]
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # If ddgr returns non-zero, it might be connectivity or no results handling difference
                if "No results" in result.stderr or not result.stderr.strip():
                     return "No results found (or search failed silentley)."
                return f"Error searching web: {result.stderr}"
            
            if not result.stdout.strip():
                 return "No results found."

            data = json.loads(result.stdout)
            if not data:
                return "No results found."
            
            output = [f"Search Results for '{query}':"]
            for r in data:
                title = r.get('title', 'No Title')
                url = r.get('url', 'No URL')
                snippet = r.get('abstract', '')
                output.append(f"- {title}: {url}\\n  {snippet}")
            return "\\n".join(output)
            
        except json.JSONDecodeError:
            # If ddgr returns non-JSON text (sometimes happens on error), return raw
            return f"Error parsing search results. Raw output: {result.stdout[:500]}..."
        except Exception as e:
            return f"Error searching web: {str(e)}"
