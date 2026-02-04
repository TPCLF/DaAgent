import os
import argparse

class Config:
    def __init__(self):
        self.api_base = os.getenv("DA_AGENT_API_BASE", "http://localhost:11434")
        self.model = os.getenv("DA_AGENT_MODEL", "qwen2.5-coder:latest")
        self.temperature = float(os.getenv("DA_AGENT_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("DA_AGENT_MAX_TOKENS", "4096"))
        self.context_window = int(os.getenv("DA_AGENT_CONTEXT_WINDOW", "8192"))
        self.auto_continue = os.getenv("DA_AGENT_AUTO", "false").lower() == "true"
        self.verbose = os.getenv("DA_AGENT_VERBOSE", "false").lower() == "true"
        self.timeout = int(os.getenv("DA_AGENT_TIMEOUT", "120"))

    @classmethod
    def from_args(cls, args):
        cfg = cls()
        if args.model:
            cfg.model = args.model
        if args.api_base:
            cfg.api_base = args.api_base
        if args.temperature is not None:
            cfg.temperature = args.temperature
        if args.auto:
            cfg.auto_continue = True
        return cfg

def get_arg_parser():
    parser = argparse.ArgumentParser(description="DaAgent: A Local CLI Coding Agent")
    parser.add_argument("task", nargs="*", help="The coding task to perform (string)")
    parser.add_argument("--model", "-m", help="Ollama model name (default: qwen2.5-coder:latest)")
    parser.add_argument("--api-base", help="Ollama API URL (default: http://localhost:11434)")
    parser.add_argument("--temperature", "-t", type=float, help="Model temperature")
    parser.add_argument("--auto", "-y", action="store_true", help="Auto-continue without user confirmation")
    parser.add_argument("--init", action="store_true", help="Initialize a .da_agent config in current directory")
    return parser
