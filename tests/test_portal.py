from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortalTests(unittest.TestCase):
    def test_home_is_portuguese_welcome_with_landmarks(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        self.assertIn('lang="pt-BR"', html)
        self.assertIn('name="viewport"', html)
        self.assertIn("Central de Operações", html)
        self.assertIn("Bem-vindo", html)
        self.assertIn("<main", html)
        self.assertIn("<nav", html)

    def test_assets_are_commit_versioned(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'css/main\.css\?v=[0-9a-f]{7,40}')
        self.assertRegex(html, r'js/main\.js\?v=[0-9a-f]{7,40}')

    def test_responsive_design_and_accessibility(self):
        css = (ROOT / "site/css/main.css").read_text(encoding="utf-8")
        self.assertIn("#0064e0", css)
        self.assertIn("#f1f4f7", css)
        self.assertIn("@media (max-width:", css)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_nginx_auth_and_revalidation(self):
        config = (ROOT / "deploy/nginx-local.conf").read_text(encoding="utf-8")
        self.assertIn("auth_basic_user_file", config)
        self.assertIn("etag on;", config)
        self.assertRegex(config, r'Cache-Control.*no-cache.*must-revalidate')
        self.assertIn('location ~* "^/media/[0-9a-f]{64}', config)
        self.assertIn('max-age=604800, immutable', config)
        self.assertIn("listen 8088;", config)

    def test_release_script_stamps_commit(self):
        script = (ROOT / "scripts/release.py").read_text(encoding="utf-8")
        self.assertIn("rev-parse", script)
        self.assertIn("git", script)
        self.assertIn("push", script)


if __name__ == "__main__":
    unittest.main()
