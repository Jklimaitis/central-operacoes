import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.portal import publish, read_catalog, write_catalog
from scripts.sync_cron import collect


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        (self.root / 'publicacoes').mkdir()
        (self.root / 'media').mkdir()
        (self.root / 'index.html').write_text('<link href="css/main.css?v=abc1234">', encoding='utf-8')
        write_catalog(self.root, [])

    def test_publications_sorted_deduplicated_and_detail_escaped(self):
        old = dict(id='relatorio-a', module='relatorios', title='<Relatório> & análise',
                   summary='Resumo', body='<script>alert(1)</script>',
                   timestamp='2026-09-26T12:00:00-03:00', relevant=True)
        new = dict(id='relatorio-b', module='relatorios', title='Mais recente',
                   summary='Resumo novo', timestamp='2026-09-27T14:00:00-03:00')
        publish(self.root, old)
        publish(self.root, new)
        publish(self.root, old)
        self.assertEqual([x['id'] for x in read_catalog(self.root)], ['relatorio-b', 'relatorio-a'])
        detail = (self.root / 'publicacoes/relatorio-a.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;', detail)
        self.assertNotIn('<script>alert(1)', detail)
        self.assertIn('css/main.css', detail)
        self.assertFalse((self.root / 'publicacoes/relatorio-b.html').exists())

    def test_media_hash_and_invalid_paths(self):
        image = self.root / 'original.png'
        image.write_bytes(b'example image bytes')
        entry = dict(id='arte', module='conteudos', title='Imagem', summary='Criativo',
                     timestamp='2026-09-27T13:00:00Z', relevant=True,
                     media=[str(image)])
        result = publish(self.root, entry)
        self.assertRegex(result['media'][0], r'^media/[0-9a-f]{64}\.png$')
        self.assertTrue((self.root / result['media'][0]).exists())
        with self.assertRaises(ValueError):
            publish(self.root, dict(entry, id='../escape'))
        with self.assertRaises(ValueError):
            publish(self.root, dict(entry, id='bad', media=['https://example.org/image.png']))

    def test_cron_terminal_rows_all_published_once_without_raw_errors(self):
        db = self.root / 'executions.db'
        c = sqlite3.connect(db)
        c.execute('CREATE TABLE executions (id TEXT, job_id TEXT, status TEXT, claimed_at TEXT, started_at TEXT, finished_at TEXT, error TEXT)')
        c.executemany('INSERT INTO executions VALUES (?,?,?,?,?,?,?)', [
            ('run1', 'job1', 'completed', '2026-09-27T11:59:59Z', '2026-09-27T12:00:00Z', '2026-09-27T12:00:04Z', None),
            ('run2', 'job1', 'failed', '2026-09-27T12:59:59Z', '2026-09-27T13:00:00Z', '2026-09-27T13:00:02Z', 'SENSITIVE_TOKEN'),
            ('run3', 'job1', 'running', '2026-09-27T13:59:59Z', '2026-09-27T14:00:00Z', None, None),
        ])
        c.commit()
        c.close()
        jobs = self.root / 'jobs.json'
        jobs.write_text(json.dumps({'jobs': [{'id':'job1','name':'Revisão diária','state':'active', 'next_run_at':'2026-09-28T12:00:00Z'}]}), encoding='utf-8')
        self.assertTrue(collect(self.root, db, jobs))
        self.assertFalse(collect(self.root, db, jobs))
        entries = read_catalog(self.root)
        self.assertEqual([x['id'] for x in entries], ['cron-run2', 'cron-run1'])
        self.assertEqual(entries[0]['duration_seconds'], 2)
        self.assertNotIn('SENSITIVE_TOKEN', (self.root / 'data/catalog.json').read_text(encoding='utf-8'))
        state = json.loads((self.root / 'data/status.json').read_text(encoding='utf-8'))
        self.assertEqual(state['jobs'][0]['last_status'], 'failed')
        self.assertEqual(state['jobs'][0]['running'], 1)

    def test_empty_cron_state(self):
        db = self.root / 'executions.db'
        sqlite3.connect(db).close()
        self.assertTrue(collect(self.root, db, self.root / 'jobs.json'))
        self.assertEqual(json.loads((self.root / 'data/status.json').read_text())['jobs'], [])


if __name__ == '__main__':
    unittest.main()
