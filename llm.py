import json
import urllib.request
import urllib.error
import sys

class LLMClient:
    def __init__(self, config):
        self.config = config
        self.api_url = f"{config.api_base}/api/chat"

    def chat(self, messages, stop=None):
        """
        Sends a chat request to the Ollama API.
        messages: list of dicts {'role': 'user', 'content': '...'}
        """
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_ctx": self.config.context_window,
                "num_predict": self.config.max_tokens,
            }
        }
        
        if stop:
            payload["options"]["stop"] = stop

        if self.config.verbose:
            print(f"\n[DEBUG] Sending to LLM ({self.config.model})...")

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url, 
            data=data, 
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result.get("message", {}).get("content", "")
                if self.config.verbose:
                    print(f"[DEBUG] LLM Response chars: {len(content)}")
                return content
        except urllib.error.URLError as e:
            return f"Error communicating with LLM: {str(e)}. check OLLAMA_HOST/api_base."
        except Exception as e:
            return f"Error: {str(e)}"
