import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from persistent_conversation_agent.embeddings import OpenAIEmbedding


def test_openai_embedding_adapter_over_local_http():
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["auth"] = self.headers["Authorization"]
            seen["body"] = json.loads(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            body = json.dumps({"data": [{"embedding": [0.25, 0.75]}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        adapter = OpenAIEmbedding(
            "test-key", "test-embedding", f"http://localhost:{server.server_port}/v1"
        )
        assert adapter.embed("hello") == [0.25, 0.75]
        assert seen == {
            "path": "/v1/embeddings",
            "auth": "Bearer test-key",
            "body": {"model": "test-embedding", "input": "hello"},
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_rejects_deceptive_plain_http_host():
    adapter = OpenAIEmbedding("test-key", base_url="http://localhost.evil.example/v1")
    with pytest.raises(ValueError):
        adapter.embed("hello")
