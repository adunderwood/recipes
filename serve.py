#!/usr/bin/env python3
"""
Local preview server for the generated recipe site.

Supports extensionless recipe URLs by rewriting `/slug` to `/slug.html`
when the matching HTML file exists inside the public directory.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


PUBLIC_DIR = Path(__file__).resolve().parent / "public"


class RecipeRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_GET(self):
        self.path = self._rewrite_extensionless_path(self.path)
        super().do_GET()

    def do_HEAD(self):
        self.path = self._rewrite_extensionless_path(self.path)
        super().do_HEAD()

    def _rewrite_extensionless_path(self, request_path: str) -> str:
        parsed = urlsplit(request_path)
        request_target = Path(unquote(parsed.path.lstrip("/")))

        # Let directory requests and explicit file extensions behave normally.
        if not parsed.path or parsed.path.endswith("/") or request_target.suffix:
            return request_path

        html_target = PUBLIC_DIR / f"{request_target}.html"
        if not html_target.exists():
            return request_path

        rewritten_path = f"{parsed.path}.html"
        if parsed.query:
            rewritten_path += f"?{parsed.query}"
        return rewritten_path


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RecipeRequestHandler)
    print("Serving recipe site at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
