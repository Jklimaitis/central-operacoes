"""Validated, atomic publication store for the local operations portal."""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

MODULES = {'operacoes', 'rotinas', 'conteudos', 'dashboards', 'relatorios', 'pesquisas'}
MEDIA_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.mp4', '.webm'}


def atomic_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_catalog(site: Path) -> list:
    path = site / 'data/catalog.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        raise ValueError('Catálogo inválido; não sobrescrever.')
    return data['items']


def write_catalog(site: Path, items: list) -> None:
    ordered = sorted(items, key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')).astimezone(timezone.utc), reverse=True)
    atomic_json(site / 'data/catalog.json', {'version': 1, 'items': ordered})


def _copy_media(site: Path, sources: list[str]) -> list[str]:
    result = []
    for raw in sources:
        path = Path(raw)
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            raise ValueError(f'Mídia local inexistente ou formato não permitido: {raw}')
        hasher = sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        relative = f'media/{digest}{path.suffix.lower()}'
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(path, target)
        result.append(relative)
    return result


def _detail_html(entry: dict) -> str:
    title = escape(entry['title'])
    body = escape(entry.get('body') or entry['summary']).replace('\n', '<br>')
    gallery = []
    for media in entry.get('media', []):
        src = '../' + media  # produced by _copy_media from a hash + safe extension
        if Path(media).suffix in {'.mp4', '.webm'}:
            gallery.append(f'<video controls preload="metadata" src="{src}"></video>')
        else:
            gallery.append(f'<a href="{src}" target="_blank" rel="noopener"><img src="{src}" alt="Mídia de {title}" loading="lazy"></a>')
    info = ' · '.join(filter(None, [entry.get('module'), entry.get('timestamp'), entry.get('status')]))
    metadata = ' · '.join(filter(None, [
        f"{entry['duration_seconds']} s" if entry.get('duration_seconds') is not None else None,
        f"Modelo: {entry['model']}" if entry.get('model') else None,
        f"Tokens: {entry['tokens']}" if entry.get('tokens') is not None else None,
        f"Custo: {entry['cost_usd']} USD" if entry.get('cost_usd') is not None else None,
    ]))
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} · Central de Operações</title><link rel="stylesheet" href="../css/main.css"></head>
<body><a class="skip-link" href="#conteudo">Pular para o conteúdo</a><main class="detail content" id="conteudo"><a class="back-link" href="/">← Voltar à visão geral</a><p class="section-overline">{escape(info)}</p><h1>{title}</h1><p class="intro">{escape(entry['summary'])}</p><div class="detail-body">{body}</div><p class="detail-metadata">{escape(metadata) if metadata else 'Métricas não informadas'}</p><div class="detail-gallery">{''.join(gallery)}</div><footer class="footer">Central de Operações</footer></main></body></html>
'''


def publish(site: Path, payload: dict) -> dict:
    entry = dict(payload)
    identifier = entry.get('id', '')
    if not isinstance(identifier, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', identifier):
        raise ValueError('ID deve ser slug minúsculo com letras, números e hífens.')
    if entry.get('module') not in MODULES:
        raise ValueError('Módulo inválido.')
    if not isinstance(entry.get('title'), str) or not entry['title'].strip() or len(entry['title']) > 160:
        raise ValueError('Título inválido.')
    if not isinstance(entry.get('summary'), str) or not entry['summary'].strip():
        raise ValueError('Resumo obrigatório.')
    ts = datetime.fromisoformat(str(entry.get('timestamp', '')).replace('Z', '+00:00'))
    if ts.tzinfo is None:
        raise ValueError('Data/hora precisa incluir fuso horário.')
    entry['timestamp'] = ts.isoformat()
    entry['media'] = _copy_media(site, entry.get('media', []))
    entry['relevant'] = bool(entry.get('relevant', False))
    entry['url'] = f"/publicacoes/{identifier}.html" if entry['relevant'] else None
    items = read_catalog(site)
    previous = next((item for item in items if item['id'] == identifier), None)
    if previous is not None and previous != entry:
        raise ValueError(f'ID já publicado com outro conteúdo: {identifier}')
    if previous is None:
        if entry['relevant']:
            detail = site / 'publicacoes' / f'{identifier}.html'
            detail.parent.mkdir(parents=True, exist_ok=True)
            detail.write_text(_detail_html(entry), encoding='utf-8')
        write_catalog(site, [*items, entry])
    return entry
