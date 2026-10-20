"""Local test partner sites for the console: a Shopify-style jeweller and a non-Shopify jeweller."""
import http.server
import os
import threading
from urllib.parse import urlparse, parse_qs

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixture")
PORT = 8799


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        if self.path.startswith("/store"):
            self.send_header("X-ShopId", "99")
        super().end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.endswith("/products.json"):
            page = parse_qs(u.query).get("page", ["1"])[0]
            f = os.path.join(ROOT, u.path.lstrip("/").replace("products.json", f"products_page_{page}.json"))
            if not os.path.exists(f) and page == "1" and "limit=3" not in u.query:
                return self.send_error(404)
            if "limit=3" in u.query:
                f = os.path.join(ROOT, u.path.lstrip("/").replace("products.json", "products_page_1.json"))
                if not os.path.exists(f):
                    return self.send_error(404)
            body = open(f, "rb").read() if os.path.exists(f) else b'{"products": []}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        if not u.path.endswith("/") and "." not in os.path.basename(u.path):
            self.path = u.path + "/"
        return super().do_GET()


def start():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
