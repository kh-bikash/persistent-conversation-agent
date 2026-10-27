from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class OpenAIEmbedding:
    api_key: str
    model: str = "text-embedding-3-small"
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 30

    @property
    def model_id(self) -> str:
        return "openai:" + self.model

    @classmethod
    def from_env(cls) -> OpenAIEmbedding:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("Set OPENAI_API_KEY for live embeddings")
        return cls(
            key,
            os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    def embed(self, text: str) -> list[float]:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" and not (
            parsed.scheme == "http"
            and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("Embedding endpoint must use HTTPS or localhost")
        request = Request(
            self.base_url.rstrip("/") + "/embeddings",
            data=json.dumps({"model": self.model, "input": text}).encode(),
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.load(response)
        vector = [float(value) for value in data["data"][0]["embedding"]]
        if not vector:
            raise ValueError("Embedding response was empty")
        return vector
