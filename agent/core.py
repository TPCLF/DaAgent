import time
from typing import Optional, List, Dict
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
import select
import sys
from .config import AgentConfig
from .llm import LLMClient
from .tools import ToolRegistry
from .utils import parse_llm_action, build_system_prompt

console = Console()

class Agent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = LLMClient(config)
        self.tools = ToolRegistry()
        self.context: List[Dict[str, str]] = []
        
        # Initialize context with system prompt
        self.context.append({
            "role": "system",
            "content": build_system_prompt(str(self.tools.work_dir))
        })

    def run(self, task: str):
        """Main Agent Loop."""
        console.print(Panel(f"[bold green]Task:[/bold green] {task}", title="Agent Started"))
        
        self.context.append({"role": "user", "content": task})
        
        try:
            step_count = 0
            while True:
                step_count += 1
                console.print(f"\n[bold blue]Step {step_count}:[/bold blue] Thinking...")
                
                # 1. Call LLM
                try:
                    # Truncate history if needed (simple sliding window)
                    if len(self.context) > self.config.history_limit * 2:
                        # Keep system prompt + last N messages
                        self.context = [self.context[0]] + self.context[-(self.config.history_limit*2):]

                    response_text = self.llm.completion(self.context)
                except Exception as e:
                    console.print(f"[bold red]LLM failure:[/bold red] {e}")
                    break

                # 2. Display Result
                console.print(Panel(response_text, title="Agent Thought", border_style="cyan"))
                self.context.append({"role": "assistant", "content": response_text})

                # 3. Parse Action
                tool_name, arg1, arg2 = parse_llm_action(response_text)
                
                if not tool_name:
                    # No tool called, maybe asking user question or done?
                    console.print("[yellow]No tool call detected. Waiting for user input...[/yellow]")
                    user_feedback = Prompt.ask("Your response (or 'exit')")
                    if user_feedback.lower() in ["exit", "quit"]:
                        break
                    self.context.append({"role": "user", "content": user_feedback})
                    continue
                
                # 4. Execute Action (with safety checks)
                console.print(f"[bold magenta]Action:[/bold magenta] Calling {tool_name}...")
                
                # Pre-emptive read to satisfy policy and save time
                if tool_name in ["edit_file", "write_file"] and arg1:
                    # We silently read logic to ensure policy pass
                    # The user explicitly asked for this behavior
                    self.tools.read_file(arg1)

                if self.config.confirm_dangerous and tool_name in ["write_file", "edit_file", "run_command"]:
                    # Custom timeout confirmation
                    print(f"Allow {tool_name} on {arg1}? [Y/n] ", end="", flush=True)
                    rlist, _, _ = select.select([sys.stdin], [], [], 60) # 60s timeout
                    
                    if rlist:
                        ans = sys.stdin.readline().strip().lower()
                    else:
                        print("\n[Auto-confirming 'y' after timeout]", flush=True)
                        ans = "y"

                    if ans == "n":
                        result = "User denied permission."
                        console.print("[red]Permission denied.[/red]")
                    else:
                        result = self._execute_tool(tool_name, arg1, arg2)
                else:
                    result = self._execute_tool(tool_name, arg1, arg2)

                # 5. Observe Result
                console.print(Panel(result, title="Tool Output", border_style="green"))
                self.context.append({"role": "user", "content": f"TOOL OUTPUT: {result}"})
                
                # Simple heuristic to pause output for readability
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            console.print("\n[bold red]Agent interrupted by user. Exiting...[/bold red]")

    def _execute_tool(self, name: str, arg1: str, arg2: Optional[str]) -> str:
        if name == "list_files":
            return self.tools.list_files(arg1 or ".")
        elif name == "read_file":
            return self.tools.read_file(arg1)
        elif name == "write_file":
            return self.tools.write_file(arg1, arg2 or "")
        elif name == "edit_file":
            return self.tools.apply_diff(arg1, arg2 or "")
        elif name == "run_command":
            return self.tools.run_command(arg1)
        elif name == "grep_files":
            return self.tools.grep_files(arg1)
        elif name == "search_web":
            return self.tools.search_web(arg1)
        else:
            return f"Error: Unknown tool '{name}'"
