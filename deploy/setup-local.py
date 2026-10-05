"""Install the localhost-only nginx site in Ubuntu/WSL. Run as root.

Generates a fresh local password on first setup; never prints or commits it.
"""
from pathlib import Path
import grp
import json
import os
import pwd
import secrets

import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deploy/nginx-local.conf"
TARGET = Path("/etc/nginx/conf.d/central-operacoes.conf")
AUTH = Path("/etc/nginx/central_operacoes.htpasswd")
USERNAME = os.environ.get("CENTRAL_HTTP_USER", "central_user")


def resolve_account():
    username = os.environ.get("CENTRAL_OS_USER") or os.environ.get("SUDO_USER")
    return pwd.getpwnam(username) if username else pwd.getpwuid(os.getuid())


def render_nginx(template: str, site: Path) -> str:
    marker = "root /var/www/central/site;"
    if template.count(marker) != 1:
        raise ValueError("Template nginx precisa conter exatamente um caminho raiz padrão.")
    if "$" in str(site):
        raise ValueError("Caminho raiz nginx não pode conter o caractere $.")
    return template.replace(marker, f"root {json.dumps(str(site), ensure_ascii=False)};")


def main():
    if os.geteuid() != 0:
        raise SystemExit("Execute como root no Ubuntu/WSL.")
    account = resolve_account()
    directory = Path(account.pw_dir) / ".config/central_operacoes_agente"
    directory.mkdir(parents=True, exist_ok=True)
    os.chown(directory, account.pw_uid, account.pw_gid)
    os.chmod(directory, 0o700)
    credential = directory / "credentials"
    if not AUTH.exists():
        password = secrets.token_urlsafe(24)
        subprocess.run(["htpasswd", "-i", "-B", "-c", str(AUTH), USERNAME],
                       input=password + "\n", text=True, stdout=subprocess.DEVNULL, check=True)
        credential.write_text(f"Usuário: {USERNAME}\nSenha: {password}\n", encoding="utf-8")
        os.chown(credential, account.pw_uid, account.pw_gid)
        os.chmod(credential, 0o600)
    os.chown(AUTH, 0, grp.getgrnam("www-data").gr_gid)
    os.chmod(AUTH, 0o640)
    TARGET.write_text(render_nginx(SOURCE.read_text(encoding="utf-8"), ROOT / "site"), encoding="utf-8")
    default = Path("/etc/nginx/sites-enabled/default")
    if default.is_symlink():
        default.unlink()  # Avoid exposing nginx's stock port-80 welcome page.
    subprocess.run(["nginx", "-t"], check=True)
    if Path("/run/nginx.pid").exists():
        subprocess.run(["nginx", "-s", "reload"], check=True)
    else:
        subprocess.run(["nginx"], check=True)
    print("Central local em http://localhost:8088/")
    if credential.exists():
        print(f"Credenciais iniciais (podem estar desatualizadas após troca de senha): {credential}")
    else:
        print("Credenciais iniciais removidas; o hash de autenticação existente foi preservado.")


if __name__ == "__main__":
    main()