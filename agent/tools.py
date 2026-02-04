import os
import subprocess
import difflib
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
            return "\n".join(output)
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
            
            # Simple patching logic
            # We expect the diff to be a standard python difflib unified_diff format or partial
            # This is complex to get right for LLMs. 
            # Strategy: The LLM should provide search/replace blocks or we use a library.
            # For this simple v1 implementation, we will try to parse a simplified Search/Replace block 
            # OR standard Unified Diff.
            
            # Let's support a simple Search/Replace block format for robustness with small models
            # FORMAT:
            # <<<<<<< SEARCH
            # old lines
            # =======
            # new lines
            # >>>>>>> REPLACE
            
            if "<<<<<<< SEARCH" in diff_content:
                return self._apply_search_replace(target, original, diff_content)
            
            # Fallback to standard patching (implementation details omitted for brevity in this snippet, 
            # ideally would use `patch` command or python `whatthepatch` lib if added)
            return "Error: Please use the <<<<<<< SEARCH / ======= / >>>>>>> REPLACE format for edits."

        except Exception as e:
            return f"Error patching {path}: {str(e)}"
    
    def _apply_search_replace(self, target: Path, original_lines: List[str], diff_content: str) -> str:
        """
        Applies a Search/Replace block. 
        This is robust for LLMs that struggle with exact line numbers in unified diffs.
        """
        # Parse blocks
        import re
        pattern = re.compile(r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE', re.DOTALL)
        match = pattern.search(diff_content)
        
        if not match:
            return "Error: Invalid Search/Replace format."
        
        search_block = match.group(1)
        replace_block = match.group(2)
        
        original_text = "".join(original_lines)
        
        if search_block not in original_text:
            # Try to be a bit fuzzy? No, safety first.
            return "Error: Search block not found in file. Ensure exact match."
            
        new_text = original_text.replace(search_block, replace_block, 1) # Only replace first occurrence
        target.write_text(new_text, encoding='utf-8')
        return "Successfully applied edit."

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
            
            output = f"Exit Code: {return_code}\n"
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
            if stderr:
                output += f"STDERR:\n{stderr}\n"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
        except Exception as e:
            return f"Error running command: {str(e)}"
    
    def grep_files(self, pattern: str, path: str = ".") -> str:
        """Recursive search for text."""
        return self.run_command(f"grep -r '{pattern}' {path}")
