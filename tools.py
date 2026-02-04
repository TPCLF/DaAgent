import os
import subprocess
import difflib
import sys

def read_file(path):
    """Reads a file from the filesystem."""
    try:
        resolved_path = os.path.abspath(path)
        if not os.path.exists(resolved_path):
            return f"Error: File not found at {resolved_path}"
        with open(resolved_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

def write_file(path, content):
    """Writes content to a file, creating directories if needed."""
    try:
        resolved_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
        with open(resolved_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {resolved_path}"
    except Exception as e:
        return f"Error writing file {path}: {str(e)}"

def list_files(path=".", depth=2):
    """Lists files in a directory recursively up to a certain depth."""
    file_list = []
    base_depth = path.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(path):
        curr_depth = root.count(os.sep)
        if curr_depth - base_depth >= depth:
            del dirs[:] # Stop recursing
            continue
        # Skip hidden folders
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if not f.startswith("."):
                file_list.append(os.path.join(root, f))
    return "\n".join(file_list)

def run_command(command):
    """Runs a shell command and returns output."""
    try:
        # Timeout to prevent hanging commands
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=os.getcwd()
        )
        output = f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {str(e)}"

def search_files(term, path="."):
    """Simple grep-like search."""
    try:
        command = f"grep -rnC 2 '{term}' {path} --exclude-dir=.*"
        return run_command(command)
    except Exception as e:
        return f"Error searching: {str(e)}"
        
def apply_unified_diff(path, diff_content):
    """Applies a unified diff to a file."""
    # This is a critical and fragile part. 
    # For a robust CLI, we might want to rely on the 'patch' command if available,
    # or implement a strict python patcher.
    # Given the requirements for 'small model friendliness', the model might generate slightly broken diffs.
    # We will try to use the 'patch' command first as it's standard on linux.
    
    # 1. Check if file exists
    if not os.path.exists(path):
        return f"Error: Cannot apply diff, target file {path} does not exist."
    
    # 2. write diff to temp file
    diff_path = f"{path}.patch.tmp"
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write(diff_content)
        
    # 3. run patch command
    # -u: unified
    # -N: ignore patches already applied
    # -p0: assume full path or relative path matches
    # We try typical patch levels
    
    # Actually, simpler: write the diff, run patch.
    # The model should provide a proper diff header `--- a/file +++ b/file` or just the hunk.
    # If the model provides just the hunk, `patch` might struggle without filenames.
    # Custom pure-python patching is safer for "fuzzy" model outputs but harder to write perfectly.
    # Let's try `patch` utility first.
    
    cmd = f"patch -u {path} -i {diff_path}"
    result = run_command(cmd)
    
    # cleanup
    if os.path.exists(diff_path):
        os.remove(diff_path)
        
    return result

class Toolbox:
    def __init__(self):
        self.tools = {
            "read_file": read_file,
            "write_file": write_file,
            "list_files": list_files,
            "run_command": run_command,
            "search_files": search_files,
            "apply_diff": apply_unified_diff
        }

    def call(self, tool_name, **kwargs):
        if tool_name not in self.tools:
            return f"Error: Tool {tool_name} not found."
        return self.tools[tool_name](**kwargs)
