"""Publish a reviewed JSON document to the portal, then commit and push it.

python scripts/publish.py C:/path/to/draft.json
Draft fields: id, module, title, summary, timestamp (with timezone), relevant,
body, media (list of local paths), and optional REAL metrics only.
Never publish secrets or private raw tool output without review.
"""
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.portal import publish

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) != 2:
        print('Uso: python scripts/publish.py CAMINHO-DO-JSON', file=sys.stderr)
        return 2
    draft = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    if not isinstance(draft, dict):
        raise ValueError('JSON deve conter um objeto de publicação.')
    item = publish(ROOT / 'site', draft)
    subprocess.run([sys.executable, str(ROOT / 'scripts/release.py'),
                    f"feat: publicar {item['id']}"], cwd=ROOT, check=True)
    print(f"Publicação: {item['url'] or '#atividade'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
