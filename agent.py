import sys
import json
import re
import os
from .tools import Toolbox
from .llm import LLMClient
from .prompts import (
    SYSTEM_PROMPT, 
    IDENTIFY_FILES_PROMPT, 
    PLAN_TASK_PROMPT, 
    GENERATE_DIFF_PROMPT, 
    WRITE_FILE_PROMPT,
    format_file_context
)

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

class DaAgent:
    def __init__(self, config):
        self.config = config
        self.toolbox = Toolbox()
        self.llm = LLMClient(config)
        self.history = []
        self.project_root = os.getcwd()

    def print_step(self, step, msg):
        print(f"{BOLD}{BLUE}[{step}]{RESET} {msg}")

    def log(self, msg):
        if self.config.verbose:
            print(f"{YELLOW}[LOG]{RESET} {msg}")

    def ask_tool_confirm(self, tool_name, args):
        if self.config.auto_continue:
            return True
        print(f"{YELLOW}Agent wants to execute:{RESET} {tool_name} with {args}")
        ans = input(f"{BOLD}Allow? [y/N]: {RESET}").strip().lower()
        return ans == "y"

    def run(self, task):
        self.print_step("INIT", f"Task: {task}")
        step_count = 0
        
        while step_count < 10: # Safety limit for now
            step_count += 1
            print(f"\n{BOLD}--- Cycle {step_count} ---{RESET}")
            
            # 1. Identify Context
            self.print_step("CONTEXT", "Identifying relevant files...")
            # We list files first to give the model a hint
            all_files = self.toolbox.call("list_files", path=".")
            prompt = IDENTIFY_FILES_PROMPT.format(task=task) + f"\n\nAvailable Files:\n{all_files}"
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm.chat(messages)
            
            # Simple heuristic parsing
            try:
                # Find JSON array
                match = re.search(r"\[.*\]", response, re.DOTALL)
                if match:
                    files_to_read = json.loads(match.group(0))
                else:
                    files_to_read = []
            except:
                self.log(f"Failed to parse file list: {response}")
                files_to_read = []

            self.log(f"Relevant files: {files_to_read}")

            # 2. Read Files
            file_context = {}
            for fpath in files_to_read:
                content = self.toolbox.call("read_file", path=fpath)
                if not content.startswith("Error"):
                    file_context[fpath] = content
            
            # 3. Plan
            self.print_step("PLAN", "Generating plan...")
            formatted_context = format_file_context(file_context)
            plan_prompt = PLAN_TASK_PROMPT.format(task=task, file_context=formatted_context)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": plan_prompt}
            ]
            plan = self.llm.chat(messages)
            print(f"{GREEN}{plan}{RESET}")

            # 4. Action Decision (User Loop or Auto)
            # For simplicity in this version, we act on the plan immediately if it involves code.
            # We assume the plan implies "Go modify X".
            # We ask the user or model for the NEXT concrete action? 
            # To be "disciplined", let's ask the model "Based on the plan, what is the single next file to Create or Modify?"
            
            action_prompt = f"""
            Based on the plan:
            {plan}
            
            What is the NEXT SINGLE file to create or modify?
            Return JSON: {{"action": "create"|"modify", "path": "filename"}}
            If verification/command is needed instead, return: {{"action": "command", "command": "shell command"}}
            If done, return {{"action": "finish"}}
            """
            
            messages.append({"role": "assistant", "content": plan})
            messages.append({"role": "user", "content": action_prompt})
            
            action_resp = self.llm.chat(messages)
            
            try:
                # Naive JSON extract
                match = re.search(r"\{.*\}", action_resp, re.DOTALL)
                if match:
                    action_data = json.loads(match.group(0))
                else:
                    self.print_step("ERROR", "Model failed to decide check logs.")
                    self.log(action_resp)
                    continue
            except:
                 self.log(f"JSON parse error on action: {action_resp}")
                 continue

            action_type = action_data.get("action")
            target_path = action_data.get("path")
            
            if action_type == "finish":
                print(f"{GREEN}Agent considers task complete.{RESET}")
                break
                
            elif action_type == "create":
                self.print_step("EXEC", f"Creating {target_path}")
                # Ask for content
                create_prompt = WRITE_FILE_PROMPT.format(task=task, filepath=target_path)
                # New context window for coding to avoid pollution
                code_messages = [
                     {"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": create_prompt}
                ]
                content_resp = self.llm.chat(code_messages)
                # Extract code block
                code_match = re.search(r"```.*?\n(.*?)```", content_resp, re.DOTALL)
                if code_match:
                    new_content = code_match.group(1)
                else:
                    new_content = content_resp # Fallback
                
                if self.ask_tool_confirm("write_file", target_path):
                    res = self.toolbox.call("write_file", path=target_path, content=new_content)
                    print(res)

            elif action_type == "modify":
                self.print_step("EXEC", f"Modifying {target_path}")
                # Use diff
                current_content = file_context.get(target_path, "")
                if not current_content:
                    # try reading again if missed
                    current_content = self.toolbox.call("read_file", path=target_path)
                
                diff_prompt = GENERATE_DIFF_PROMPT.format(task=task, filepath=target_path, file_content=current_content)
                code_messages = [
                     {"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": diff_prompt}
                ]
                diff_resp = self.llm.chat(code_messages)
                
                # Extract diff block
                diff_match = re.search(r"```.*?\n(.*?)```", diff_resp, re.DOTALL)
                if diff_match:
                    diff_content = diff_match.group(1)
                else:
                    diff_content = diff_resp

                if self.ask_tool_confirm("apply_diff", target_path):
                     res = self.toolbox.call("apply_diff", path=target_path, diff_content=diff_content)
                     print(res)

            elif action_type == "command":
                cmd = action_data.get("command")
                self.print_step("EXEC", f"Running command: {cmd}")
                if self.ask_tool_confirm("run_command", cmd):
                    out = self.toolbox.call("run_command", command=cmd)
                    print(out)

            # 5. Review / Continue
            if not self.config.auto_continue:
                cont = input(f"\n{BOLD}Continue to next step? [Y/n/finish]: {RESET}").lower()
                if cont == "finish" or cont == "n":
                    break
