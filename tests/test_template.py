import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemplateTests(unittest.TestCase):
    def test_setup_has_generic_username(self):
        with patch.dict(os.environ, {}, clear=True):
            setup = load('deploy/setup-local.py', 'setup_default')
        self.assertEqual(setup.USERNAME, 'central_user')

    def test_setup_uses_installation_context(self):
        setup = load('deploy/setup-local.py', 'setup_context')
        self.assertTrue(callable(getattr(setup, 'resolve_account', None)), 'Missing generic OS-account resolution')
        self.assertTrue(callable(getattr(setup, 'render_nginx', None)), 'Missing installation-path rendering')
        with patch.dict(os.environ, {}, clear=True):
            process_account = setup.resolve_account()
            self.assertEqual(process_account.pw_uid, os.getuid())
        selected_account = setup.pwd.getpwnam('root')
        for variable in ('CENTRAL_OS_USER', 'SUDO_USER'):
            with self.subTest(variable=variable), patch.dict(os.environ, {variable: selected_account.pw_name}, clear=True):
                self.assertEqual(setup.resolve_account(), selected_account)
        template = (ROOT / 'deploy/nginx-local.conf').read_text(encoding='utf-8')
        rendered = setup.render_nginx(template, Path('/srv/central portal/site'))
        self.assertIn('root "/srv/central portal/site";', rendered)
        self.assertIn('auth_basic_user_file /etc/nginx/central_operacoes.htpasswd;', rendered)
        with self.assertRaises(ValueError):
            setup.render_nginx('server {}', Path('/srv/site'))


    def test_render_nginx_rejects_dollar_signs_in_site_path(self):
        setup = load('deploy/setup-local.py', 'setup_dollar_path')
        template = (ROOT / 'deploy/nginx-local.conf').read_text(encoding='utf-8')
        for site in ('/srv/$uri/site', '/srv/$unknown/site'):
            with self.subTest(site=site), self.assertRaises(ValueError):
                setup.render_nginx(template, Path(site))


    def test_release_requires_explicit_matching_remote(self):
        release = load('scripts/release.py', 'release_config')
        self.assertTrue(callable(getattr(release, 'remote_is_allowed', None)), 'Missing configurable remote guard')
        remote = 'https://github.com/example/central-template.git'
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(release.remote_is_allowed(remote))
        with patch.dict(os.environ, {'CENTRAL_GIT_REMOTE': remote}, clear=True):
            self.assertTrue(release.remote_is_allowed(remote))
            self.assertFalse(release.remote_is_allowed('https://github.com/example/other.git'))


    def test_sources_do_not_embed_local_paths_or_private_emails(self):
        import re
        patterns = [
            re.compile(r'(?:[A-Za-z]:[/\\]Users[/\\]|/mnt/[a-z]/Users/|/home/)[A-Za-z0-9_.-]+/'),
            re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
        ]
        allowed = {'.md', '.py', '.conf', '.html', '.js', '.css', '.json'}
        violations = []
        for path in sorted(ROOT.rglob('*')):
            if not path.is_file() or path.suffix not in allowed or '.git' in path.parts or '__pycache__' in path.parts:
                continue
            text = path.read_text(encoding='utf-8')
            if any(pattern.search(text) for pattern in patterns):
                violations.append(str(path.relative_to(ROOT)))
        self.assertEqual(violations, [], 'Local home paths or private emails remain in source files')


    @unittest.skipUnless(os.environ.get("CENTRAL_CHECK_TEMPLATE_DATA") == "1", "Starter-data check is opt-in after publications are added")
    def test_template_starts_without_usage_history(self):
        catalog = json.loads((ROOT / 'site/data/catalog.json').read_text(encoding='utf-8'))
        status = json.loads((ROOT / 'site/data/status.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog, {'version': 1, 'items': []}, 'Historical publications remain')
        self.assertEqual(status, {'version': 1, 'jobs': []})
        self.assertEqual(list((ROOT / 'site/publicacoes').glob('*.html')), [])


if __name__ == '__main__':
    unittest.main()
