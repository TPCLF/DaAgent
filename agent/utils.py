from typing import List, Dict, Any, Optional, Tuple

def parse_llm_action(response_text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parses the LLM output to identify tool calls.
    Returns (tool_name, argument_1, argument_2)
    
    Expected format in the response:
    TOOL: <name>
    ARG1: <arg1>
    ARG2: <arg2> (optional)
    """
    lines = response_text.strip().splitlines()
    tool = None
    arg1 = None
    arg2 = ""
    
    # Very simple parsing logic for robustness with small models
    # We look for the last occurrence of TOOL: to act upon
    # This allows the model to "think" before acting.
    
    for i, line in enumerate(lines):
        if line.startswith("TOOL:"):
            tool = line.split(":", 1)[1].strip()
            # Look ahead for args
            # Look ahead for args
            if i + 1 < len(lines) and lines[i+1].startswith("ARG1:"):
                arg1 = lines[i+1].split(":", 1)[1].strip()
                # Check for continuation of ARG1 (multiline)
                j = i + 2
                while j < len(lines) and not lines[j].startswith("ARG2:") and not lines[j].startswith("TOOL:"):
                     # Special case for edit_file: if we see the start of a diff block, it's ARG2
                     if tool == "edit_file" and lines[j].startswith("<<<<<<< SEARCH"):
                         break
                     
                     # It's part of ARG1 if it's not a keyword
                     arg1 += "\n" + lines[j]
                     j += 1
                
                # Check for ARG2
                if j < len(lines):
                    if lines[j].startswith("ARG2:"):
                        arg2 = lines[j].split(":", 1)[1].strip()
                        # continuation for ARG2
                        k = j + 1
                        while k < len(lines) and not lines[k].startswith("TOOL:"):
                            arg2 += "\n" + lines[k]
                            k += 1
                    elif tool == "edit_file" and lines[j].startswith("<<<<<<< SEARCH"):
                        # Implicit ARG2 start for edit_file
                        arg2 = lines[j]
                        k = j + 1
                        while k < len(lines) and not lines[k].startswith("TOOL:"):
                            arg2 += "\n" + lines[k]
                            k += 1
    
    return tool, arg1, arg2

def build_system_prompt(work_dir: str) -> str:
    return f"""You are a Local CLI Coding Agent working in {work_dir}.
You must strictly follow this cycle:
1. THINK: Analyze the situation. (Use 'search_web' to verify documentation or syntax if unsure)
2. ACT: Call a tool using the format below.

TOOLS AVAILABLE:
- list_files (ARG1: path)
- read_file (ARG1: path)
- write_file (ARG1: path, ARG2: content)
- edit_file (ARG1: path, ARG2: Search/Replace Block)
- run_command (ARG1: shell command)
- grep_files (ARG1: pattern)
- search_web (ARG1: query)

FORMATTING:
To call a tool, end your message with:
TOOL: <tool_name>
ARG1: <argument_1>
ARG2: <argument_2 (if needed)>

EDITING RULES:
- You MUST read a file before editing it.
- Use 'edit_file' for existing files. Use the format:
<<<<<<< SEARCH
<exact lines to replace>
=======
<new lines>
>>>>>>> REPLACE
- Keep edits atomic. Avoid rewriting entire files if possible.

Be concise. Focus on the task."""
