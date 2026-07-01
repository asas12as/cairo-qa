import json
import os
import requests


OLLAMA_API_URL = "https://ollama.com/v1/chat/completions"


class OllamaLLM:
    def __init__(self, config):
        raw = config._cfg.get("ollama", {})
        self.api_key = raw.get("api_key") or os.environ.get("OLLAMA_API_KEY", "")
        self.model = raw.get("model") or "llama3.1-8b"
        self.base_url = raw.get("base_url") or OLLAMA_API_URL

    def load(self):
        if not self.api_key:
            raise ValueError("OLLAMA_API_KEY not set in config or environment")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, messages, max_tokens=512, temperature=0.1):
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        resp = requests.post(self.base_url, headers=self._headers(), json=body, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def chat_stream(self, messages, max_tokens=512, temperature=0.1):
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        resp = requests.post(self.base_url, headers=self._headers(), json=body, stream=True, timeout=60)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    data = decoded[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]

    def unload(self):
        pass
