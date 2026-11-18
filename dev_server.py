"""Private local UI and Modal proxy. Credentials never enter the browser or repo."""

import argparse
import http.client
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = Path.home() / ".config/dreamtelligence-xo/modal.json"
STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/dreamtelligence-redesign.css": "dreamtelligence-redesign.css",
    "/header.webp": "header.webp",
}
UPLOAD_ROUTES = {
    "separation": "/",
    "mastering": "/master",
    "transcription": "/transcribe",
    "enhancement": "/upload/enhancement",
    "generation": "/",
}
MAX_UPLOAD = 110 * 1024 * 1024


def load_config(path):
    if not path.exists():
        return None
    if path.stat().st_mode & 0o077:
        raise ValueError("Modal-Konfiguration benötigt Dateirechte 600.")
    config = json.loads(path.read_text())
    if not config.get("token_id", "").startswith("wk-") or not config.get("token_secret", "").startswith("ws-"):
        raise ValueError("Ungültige private Modal-Konfiguration.")
    for service, url in config["services"].items():
        target = urlsplit(url)
        if (service not in {*UPLOAD_ROUTES, "audiosr"} or target.scheme != "https"
                or not (target.hostname or "").endswith(".modal.run")
                or target.port or target.username or target.password
                or target.path not in ("", "/") or target.query or target.fragment):
            raise ValueError("Ungültiger Modal-Zielserver.")
    return config


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # No audio filenames, query strings or credentials in access logs.

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'self'")
        super().end_headers()

    def error(self, status, message):
        data = json.dumps({"detail": message}, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def dispatch(self):
        port = self.server.server_port
        hosts = {f"localhost:{port}", f"127.0.0.1:{port}"}
        if self.headers.get("Host") not in hosts:
            return self.error(403, "Nur lokaler Zugriff erlaubt.")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers['Host']}":
            return self.error(403, "Fremder Ursprung abgelehnt.")
        if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
            return self.error(403, "Fremder Browserzugriff abgelehnt.")
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        if parsed.scheme or parsed.netloc or "\\" in path or any(p in (".", "..") for p in path.split("/")):
            return self.error(400, "Ungültiger Pfad.")
        if path.startswith("/api/modal/"):
            return self.proxy(path, parsed.query)
        if path.startswith("/api/"):
            return self.error(410, "Zahlungen und Credits sind deaktiviert.")
        filename = STATIC_FILES.get(path)
        if not filename or self.command not in ("GET", "HEAD"):
            return self.error(404, "Nicht gefunden.")
        data = (ROOT / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(filename)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def proxy(self, path, query):
        parts = path.split("/", 4)
        service = parts[3]
        route = "/" + (parts[4] if len(parts) == 5 else "")
        if service not in UPLOAD_ROUTES:
            return self.error(404, "Unbekannter Dienst.")
        config = self.server.modal_config
        if not config or service not in config["services"]:
            return self.error(503, "Private Modal-Konfiguration fehlt. Siehe docs/PRIVATE_MODE.md.")
        if self.command == "POST":
            if route != UPLOAD_ROUTES[service]:
                return self.error(405, "Route nicht freigegeben.")
            length = self.headers.get("Content-Length", "")
            if not length.isdecimal() or self.headers.get("Transfer-Encoding"):
                return self.error(411, "Content-Length erforderlich.")
            length = int(length)
            if length > MAX_UPLOAD:
                return self.error(413, "Audiodatei zu groß.")
        elif self.command in ("GET", "HEAD"):
            if route not in ("/health", "/models") and not route.startswith(("/status/", "/download/", "/preview/")):
                return self.error(404, "Route nicht freigegeben.")
            length = 0
        else:
            return self.error(405, "Methode nicht erlaubt.")
        headers = {
            "Modal-Key": config["token_id"],
            "Modal-Secret": config["token_secret"],
            "Accept": self.headers.get("Accept", "*/*"),
        }
        for name in ("Content-Type", "Range"):
            if name in self.headers:
                headers[name] = self.headers[name]
        if self.command == "POST":
            headers["Content-Length"] = str(length)
        target = urlsplit(config["services"][service])
        connection = http.client.HTTPSConnection(target.hostname, timeout=120)
        response_started = False
        try:
            connection.putrequest(self.command, route + ("?" + query if query else ""))
            for name, value in headers.items():
                connection.putheader(name, value)
            connection.endheaders()
            while length:
                chunk = self.rfile.read(min(length, 64 * 1024))
                if not chunk:
                    raise ValueError("Unvollständiger Upload")
                connection.send(chunk)
                length -= len(chunk)
            response = connection.getresponse()
            self.send_response(response.status)
            for name in ("Content-Type", "Content-Disposition", "Content-Length", "Content-Range", "Accept-Ranges"):
                if response.getheader(name) is not None:
                    self.send_header(name, response.getheader(name))
            self.end_headers()
            response_started = True
            if self.command != "HEAD":
                while chunk := response.read(64 * 1024):
                    self.wfile.write(chunk)
        except (OSError, ValueError, http.client.HTTPException):
            if not response_started:
                self.error(502, "Modal-Anfrage fehlgeschlagen.")
        finally:
            connection.close()

    do_GET = dispatch
    do_HEAD = dispatch
    do_POST = dispatch
    do_OPTIONS = dispatch
    do_PUT = dispatch
    do_DELETE = dispatch


def create_server(port=8765, config_path=CONFIG_PATH):
    config = load_config(config_path)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.modal_config = config
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    with create_server(args.port, args.config) as server:
        print(f"Dreamtelligence: http://localhost:{server.server_port} (nur lokal)", flush=True)
        if not server.modal_config:
            print("Modal deaktiviert: private Konfiguration fehlt.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
