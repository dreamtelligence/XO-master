import http.client
import importlib.util
import io
import json
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dev_server", ROOT / "dev_server.py")
dev_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev_server)


class PrivateModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp.name) / "missing.json"
        self.server = dev_server.create_server(0, self.config_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, method="GET", headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_clone_without_credentials_cannot_use_modal(self):
        for service in dev_server.UPLOAD_ROUTES:
            self.assertEqual(self.request(f"/api/modal/{service}/health")[0], 503)
        self.assertEqual(self.request("/")[0], 200)

    def test_only_public_frontend_files_are_served(self):
        for path in ("/.git/config", "/.env.local", "/dev_server.py", "/api/../dev_server.py", "/%2e%2e/.config/dreamtelligence-xo/modal.json"):
            self.assertIn(self.request(path)[0], (400, 404))
        self.assertEqual(self.request("/dreamtelligence-redesign.css")[0], 200)

    def test_cross_origin_and_dns_rebinding_are_rejected(self):
        for headers in ({"Host": "attacker.example"}, {"Origin": "https://attacker.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"}):
            self.assertEqual(self.request("/api/modal/separation/", "POST", headers, b"audio")[0], 403)

    def test_commerce_api_is_disabled(self):
        for name in ("credits", "paywall", "webhook", "create-checkout-session"):
            self.assertEqual(self.request(f"/api/{name}", "POST", body=b"{}")[0], 410)

    def test_config_permissions_and_upstream_validation(self):
        config = {"token_id": "wk-test", "token_secret": "ws-private", "services": {"separation": "https://test.modal.run"}}
        self.config_path.write_text(json.dumps(config))
        self.config_path.chmod(0o644)
        with self.assertRaises(ValueError):
            dev_server.load_config(self.config_path)
        self.config_path.chmod(0o600)
        self.assertEqual(dev_server.load_config(self.config_path), config)
        for url in ("http://test.modal.run", "https://attacker.example", "https://test.modal.run.evil", "https://user:pass@test.modal.run", "https://test.modal.run?target=evil"):
            config["services"]["separation"] = url
            self.config_path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                dev_server.load_config(self.config_path)

    def test_proxy_injects_server_credentials_without_exposing_them(self):
        self.server.modal_config = {"token_id": "wk-owner", "token_secret": "ws-private", "services": {"separation": "https://test.modal.run"}}
        response = unittest.mock.Mock(status=200)
        body = io.BytesIO(b"audio-result")
        response.read.side_effect = body.read
        response.getheader.side_effect = lambda key: {"Content-Type": "audio/wav", "Content-Length": "12", "Modal-Secret": "ws-private"}.get(key)
        with patch.object(dev_server.http.client, "HTTPSConnection") as upstream:
            upstream.return_value.getresponse.return_value = response
            status, headers, data = self.request("/api/modal/separation/download/job/final_stems/vocals.wav", headers={"Modal-Secret": "attacker", "Authorization": "Bearer attacker", "Range": "bytes=0-11"})
            forwarded = dict(call.args for call in upstream.return_value.putheader.call_args_list)
            self.assertEqual(forwarded["Modal-Secret"], "ws-private")
            self.assertNotIn("Authorization", forwarded)
            self.assertEqual(forwarded["Range"], "bytes=0-11")
        self.assertEqual((status, data), (200, b"audio-result"))
        self.assertNotIn("Modal-Secret", headers)
        self.assertNotIn(b"ws-private", self.request("/")[2])
        self.assertIn("connect-src 'self'", headers["Content-Security-Policy"])

    def test_private_proxy_limits_uploads_and_routes(self):
        self.server.modal_config = {"token_id": "wk-owner", "token_secret": "ws-private", "services": {"separation": "https://test.modal.run"}}
        with patch.object(dev_server.http.client, "HTTPSConnection") as upstream:
            self.assertEqual(self.request("/api/modal/separation/", "POST", {"Content-Length": str(dev_server.MAX_UPLOAD + 1)})[0], 413)
            self.assertEqual(self.request("/api/modal/separation/debug/secrets")[0], 404)
            self.assertEqual(self.request("/api/modal/separation/not-an-upload", "POST", body=b"audio")[0], 405)
            upstream.assert_not_called()

    def test_all_modal_web_apps_require_edge_auth(self):
        apps = list(ROOT.glob("modal_app_*.py"))
        self.assertEqual(len(apps), 5)
        for path in apps:
            self.assertIn("@modal.asgi_app(requires_proxy_auth=True)", path.read_text())
            self.assertNotIn("@modal.asgi_app()", path.read_text())

    def test_inactive_marketing_and_payment_scripts_do_not_render(self):
        class ActiveHTML(HTMLParser):
            def __init__(self):
                super().__init__()
                self.templates = 0
                self.tags = []
                self.text = []

            def handle_starttag(self, tag, attrs):
                if tag == "template":
                    self.templates += 1
                elif not self.templates:
                    self.tags.append((tag, dict(attrs)))

            def handle_endtag(self, tag):
                if tag == "template":
                    self.templates -= 1

            def handle_data(self, text):
                if not self.templates:
                    self.text.append(text)

        html = (ROOT / "index.html").read_text()
        parsed = ActiveHTML()
        parsed.feed(html)
        self.assertEqual(parsed.templates, 0)
        self.assertNotIn("nav", [tag for tag, _ in parsed.tags])
        scripts = [attrs.get("src", "") for tag, attrs in parsed.tags if tag == "script"]
        self.assertFalse(any("stripe.com" in url or "supabase-js" in url for url in scripts))
        active_ids = {attrs.get("id") for _, attrs in parsed.tags}
        self.assertFalse({"pricing", "features", "authModal", "auth-buttons"} & active_ids)
        self.assertIn("const COMMERCE_ENABLED = false;", html)
        self.assertIn("const ACCOUNTS_ENABLED = false;", html)


if __name__ == "__main__":
    unittest.main()
