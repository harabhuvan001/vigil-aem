"""Optional deterministic loopback mock service using only Python's standard library."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        status = {"/health": 200, "/503": 503, "/401": 401}.get(self.path, 404)
        body = json.dumps({"status": status, "fixture_only": True}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    # Container port is published on host loopback by Compose.
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
