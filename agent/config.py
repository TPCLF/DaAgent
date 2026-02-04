import os
from pydantic import BaseModel, Field

class AgentConfig(BaseModel):
    """Configuration for the CLI Agent."""
    
    # Model Settings
    model: str = Field(default="llama3.1", description="Name of the model to use (e.g. llama3, mistral)")
    api_base: str = Field(default="http://localhost:11434/v1", description="Base URL for the OpenAI-compatible API")
    api_key: str = Field(default="ollama", description="API Key (dummy for Ollama)")
    temperature: float = Field(default=0.0, description="Sampling temperature")
    max_tokens: int = Field(default=4096, description="Max tokens per response")
    timeout: float = Field(default=1200000, description="Request timeout in seconds")
    
    # Safety Settings
    confirm_dangerous: bool = Field(default=True, description="Ask before executing shell commands or writing files")
    diff_only: bool = Field(default=False, description="If True, only show diffs, do not apply edits directly without confirmation")
    
    # System Settings
    history_limit: int = Field(default=20, description="Number of turns to keep in context")

    @staticmethod
    def from_env() -> "AgentConfig":
        """Load config from environment variables."""
        return AgentConfig(
            model=os.getenv("AGENT_MODEL", "llama3.1"),
            api_base=os.getenv("AGENT_API_BASE", "http://localhost:11434/v1"),
            api_key=os.getenv("AGENT_API_KEY", "ollama"),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "4096")),
            timeout=float(os.getenv("AGENT_TIMEOUT", "120.0")),
            confirm_dangerous=os.getenv("AGENT_CONFIRM", "true").lower() == "true",
            diff_only=os.getenv("AGENT_DIFF_ONLY", "false").lower() == "true",
        )
