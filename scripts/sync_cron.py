"""Mirror Agente's terminal cron execution ledger into the local portal.

Only job names and execution metadata are copied; raw output, prompts and error
strings remain in Agente's own local ledger. A minute-level Windows Task Scheduler
job invokes this script and each changed snapshot is committed/pushed.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import traceback

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.portal import atomic_json, publish, read_catalog

ROOT = Path(__file__).resolve().parents[1]
CRON = Path(os.environ.get('HERMES_HOME', Path(os.environ.get('LOCALAPPDATA', '')) / 'agente')) / 'cron'
TERMINAL = {'completed', 'failed', 'unknown'}


def _jobs(path: Path) -> list:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(raw, list):
        return raw
    jobs = raw.get('jobs', [])
    return list(jobs.values()) if isinstance(jobs, dict) else jobs


def _rows(db: Path) -> list[dict]:
    if not db.exists():
        return []
    connection = sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in connection.execute(
            'SELECT id, job_id, status, claimed_at, started_at, finished_at FROM executions ORDER BY claimed_at'
        )]
    except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc).lower():
            return []
        raise
    finally:
        connection.close()


def _seconds(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        a = datetime.fromisoformat(start.replace('Z', '+00:00'))
        b = datetime.fromisoformat(end.replace('Z', '+00:00'))
        return max(0, round((b - a).total_seconds()))
    except (ValueError, TypeError):
        return None


def collect(site: Path, db: Path, jobs_path: Path) -> bool:
    jobs = _jobs(jobs_path)
    rows = _rows(db)
    by_id = {str(job['id']): job for job in jobs}
    existing = {x['id'] for x in read_catalog(site)}
    changed = False
    for row in rows:
        if row['status'] not in TERMINAL:
            continue
        raw_id = str(row['id'])
        # Agente IDs are normally UUID-like. Validate before embedding in the slug.
        import hashlib
        suffix = raw_id if __import__('re').fullmatch(r'[a-z0-9-]{1,70}', raw_id) else hashlib.sha256(raw_id.encode()).hexdigest()[:24]
        identifier = 'cron-' + suffix
        if identifier in existing:
            continue
        job = by_id.get(str(row['job_id']), {})
        name = job.get('name') or str(row['job_id'])
        outcome = {'completed': 'concluída', 'failed': 'falhou', 'unknown': 'estado desconhecido'}[row['status']]
        entry = dict(
            id=identifier, module='rotinas', title=f'{name} — execução {outcome}',
            summary=f'Execução {outcome}. ID: {raw_id}.',
            body=f'Job: {row["job_id"]}\nExecução: {raw_id}\nStatus: {row["status"]}\n'
                 'Saída detalhada e erros permanecem no histórico local do Agente: ferramenta de cron do agente.',
            timestamp=row['finished_at'] or row['started_at'] or row['claimed_at'],
            status=row['status'], duration_seconds=_seconds(row['started_at'], row['finished_at']),
            model=job.get('model'), tokens=None, cost_usd=None,
            relevant=row['status'] != 'completed', source='cron', job_id=str(row['job_id']),
        )
        publish(site, entry)
        existing.add(identifier)
        changed = True
    states = []
    for job in jobs:
        job_id = str(job['id'])
        history = [r for r in rows if str(r['job_id']) == job_id and r['status'] in TERMINAL]
        latest = max(history, key=lambda r: r['finished_at'] or r['claimed_at']) if history else None
        states.append(dict(id=job_id, name=job.get('name') or job_id,
                           state=job.get('state') or ('active' if job.get('enabled', True) else 'paused'),
                           next_run_at=job.get('next_run_at'),
                           last_status=latest['status'] if latest else job.get('last_status'),
                           last_run_at=latest['finished_at'] if latest else job.get('last_run_at'),
                           running=sum(r['status'] in ('running', 'claimed') and str(r['job_id']) == job_id for r in rows),
                           failure_streak=job.get('failure_streak', 0)))
    states.sort(key=lambda x: (x['name'].casefold(), x['id']))
    target = site / 'data/status.json'
    status = {'version': 1, 'jobs': states}
    if not target.exists() or json.loads(target.read_text(encoding='utf-8')) != status:
        atomic_json(target, status)
        changed = True
    return changed


def main() -> int:
    try:
        changed = collect(ROOT / 'site', CRON / 'executions.db', CRON / 'jobs.json')
        pending = subprocess.check_output(
            ['git', 'status', '--porcelain', '--', 'site/data/catalog.json',
             'site/data/status.json', 'site/publicacoes/cron-*.html'],
            cwd=ROOT, text=True).strip()
        unpushed = subprocess.check_output(
            ['git', 'rev-list', '--count', 'origin/main..HEAD'], cwd=ROOT, text=True).strip()
        if changed or pending or unpushed != '0':
            subprocess.run([sys.executable, str(ROOT / 'scripts/release.py'),
                            'chore: registrar estado e execuções de cron', '--cron-sync'], cwd=ROOT, check=True)
            print('Cron sincronizado e publicado.')
        else:
            print('Cron sem novidades.')
        return 0
    except Exception:
        log = Path(os.environ['LOCALAPPDATA']) / 'agente' / 'central-operacoes-sync.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('a', encoding='utf-8') as out:
            out.write(datetime.now().isoformat() + '\n' + traceback.format_exc() + '\n')
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
