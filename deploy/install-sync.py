"""Install minute-level Windows Task Scheduler sync for the active user.

No password is stored. Runs while o usuário is signed into Windows, with network
access to the private Git remote. After reboot, sign in to resume collection.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TASK = 'AgenteCentralSync'


def main():
    python = Path(sys.executable)
    script = ROOT / 'scripts' / 'sync_cron.py'
    action = f'"{python}" "{script}"'
    subprocess.run(['schtasks.exe', '/Create', '/F', '/SC', 'MINUTE', '/MO', '1',
                    '/TN', TASK, '/TR', action, '/IT'], check=True)
    subprocess.run(['schtasks.exe', '/Query', '/TN', TASK], check=True)
    print('Coletor ativo enquanto você estiver conectado ao Windows.')


if __name__ == '__main__':
    main()