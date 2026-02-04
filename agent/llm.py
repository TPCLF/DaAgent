import httpx
from typing import List, Dict, Any, Optional
from rich.console import Console
from .config import AgentConfig

console = Console()

class LLMClient:
    """Client for interacting with the Local LLM (Ollama/OpenAI compatible)."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = httpx.Client(
            base_url=config.api_base,
            headers={"Authorization": f"Bearer {config.api_key}"},
            # Robust timeout: wait for connection based on config, but wait forever for read (thinking)
            timeout=httpx.Timeout(connect=config.timeout, read=None, write=60.0, pool=60.0)
        )

    def completion(self, messages: List[Dict[str, str]], stop: Optional[List[str]] = None) -> str:
        """Get a completion from the model."""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        try:
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            console.print(f"[bold red]LLM Error:[/bold red] {e}")
            raise

    def check_health(self) -> bool:
        """Verify connection to the model."""
        try:
            # Simple list models call or empty completion to check
            self.client.get("/models")
            return True
        except Exception:
            return False
