"""Commit changes, stamp asset URLs with a real Git commit, test, push.

Usage: python scripts/release.py "What changed"
Never includes local credentials. The asset commit precedes the HTML stamp commit
because a commit cannot contain its own final SHA.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "site" / "index.html"
ASSETS = ("css/main.css", "js/main.js")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def commit_if_staged(message: str) -> bool:
    if not git("diff", "--cached", "--name-only"):
        return False
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    return True


def remote_is_allowed(remote: str) -> bool:
    expected = os.environ.get("CENTRAL_GIT_REMOTE", "").strip()
    return bool(expected) and remote == expected


def main() -> int:
    cron_sync = len(sys.argv) == 3 and sys.argv[2] == '--cron-sync'
    if (len(sys.argv) not in (2, 3) or not sys.argv[1].strip()
            or (len(sys.argv) == 3 and not cron_sync)):
        print('Uso: python scripts/release.py "Descrição" [--cron-sync]', file=sys.stderr)
        return 2
    if not remote_is_allowed(git("remote", "get-url", "origin")):
        print("Recusado: configure CENTRAL_GIT_REMOTE com a URL exata do origin autorizado.", file=sys.stderr)
        return 2
    if cron_sync:
        # The minute-level observer must never commit unrelated user work-in-progress.
        paths = ['site/data/catalog.json', 'site/data/status.json'] + [
            str(path.relative_to(ROOT)).replace('\\', '/')
            for path in (ROOT / 'site/publicacoes').glob('cron-*.html')
        ]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=True)
    else:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    staged = git("diff", "--cached", "--name-only").splitlines()
    if cron_sync and any(name not in paths for name in staged):
        print('Recusado: alterações de outra tarefa já estavam no índice Git.', file=sys.stderr)
        return 2
    for name in staged:
        basename = Path(name).name.lower()
        if basename in {".env", "credentials", "credentials.txt"} or basename.endswith(".htpasswd"):
            print(f"Recusado: credencial em staged: {name}", file=sys.stderr)
            return 2
    # Avisar se há arquivos fora do escopo esperado
    ALLOWED_PREFIXES = ("site/", "scripts/", "tests/", "deploy/")
    ALLOWED_FILES = {"AGENTS.md", "README.md", ".gitignore"}
    for name in staged:
        top = name.split("/")[0] + "/" if "/" in name else name
        if top not in ALLOWED_PREFIXES and name not in ALLOWED_FILES:
            print(f"Aviso: arquivo fora do escopo esperado: {name}", file=sys.stderr)
    commit_if_staged(sys.argv[1].strip())
    if not cron_sync:
        version = git("rev-parse", "--short=8", "HEAD")
        html = HTML.read_text(encoding="utf-8")
        for asset in ASSETS:
            html, count = re.subn(rf'(?P<asset>{re.escape(asset)})\?v=[0-9a-f]{{7,40}}',
                                  lambda match: f'{match.group("asset")}?v={version}', html)
            if count != 1:
                raise RuntimeError(f"Referência versionada ausente ou duplicada: {asset}")
        if html != HTML.read_text(encoding="utf-8"):
            HTML.write_text(html, encoding="utf-8")
            subprocess.run(["git", "add", "site/index.html"], cwd=ROOT, check=True)
            commit_if_staged(f"chore: versionar assets no HTML ({version})")
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    if not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful():
        print("Testes falharam: push não realizado.", file=sys.stderr)
        return 1
    subprocess.run(["git", "push", "-u", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print(f"Publicado: commit {git('rev-parse', '--short', 'HEAD')}" +
          ('' if cron_sync else f'; assets v={version}'))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())