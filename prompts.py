# Prompts optimized for small local models

SYSTEM_PROMPT = """You are DaAgent, a disciplined CLI coding assistant.
You strictly follow instructions and perform work in small, verified steps.
You effectively use the provided tools to read code, plan changes, and apply fixes.
You DO NOT write long explanations. You focus on code and shell commands.
"""

IDENTIFY_FILES_PROMPT = """
Task: {task}

Which files in the current directory are relevant to this task?
Use 'list_files' to check potential locations if unsure.
Reply with a JSON list of file paths ONLY.
Example: ["src/main.py", "README.md"]
If no files exist or need to be created, return [].
"""

PLAN_TASK_PROMPT = """
Task: {task}
Context Files:
{file_context}

Create a minimal step-by-step plan to complete the task.
Focus on:
1. What to separate into file creation vs modification.
2. What commands to run to verify (if applicable).

Keep it short (max 5 steps).
"""

GENERATE_DIFF_PROMPT = """
Task: {task}
File to Modify: {filepath}
File Content:
{file_content}

Instruction:
Generate a valid Unified Diff to apply the changes required for the task.
- Use `--- a/{filepath}` and `+++ b/{filepath}` headers.
- Include enough context lines (3 lines) for `patch` to work.
- Do NOT rewrite the whole file unless it is very small (< 50 lines).
- Output ONLY the code block with the diff.
"""

WRITE_FILE_PROMPT = """
Task: {task}
File to Create: {filepath}

Instruction:
Output the full content of the file.
Output ONLY the code block.
"""

# Helper to format file context
def format_file_context(files_content):
    out = ""
    for path, content in files_content.items():
        out += f"--- {path} ---\n"
        # Truncate if too long (simple heuristic for now)
        if len(content) > 4000:
            out += content[:1000] + "\n...[truncated]...\n" + content[-1000:]
        else:
            out += content
        out += "\n"
    return out
