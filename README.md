# Central de Operações

Portal estático para reunir publicações e acompanhar rotinas locais. Usa HTML, CSS, JavaScript e scripts Python, com nginx e autenticação Basic Auth no Ubuntu/WSL.

Este repositório é um **esqueleto reutilizável**: o catálogo e o painel de jobs começam vazios, sem histórico de uma instalação particular. O código foi desenvolvido com assistência de IA; alterações precisam passar por revisão, testes e verificação do destino Git antes de serem publicadas.

## O que o projeto faz

- Organiza publicações por módulo, com busca por título/nome/módulo e ordenação por data.
- Cria páginas dedicadas para publicações relevantes e incorpora imagens ou vídeos.
- Copia mídia com nomes derivados de hash, evitando colisões e preservando arquivos imutáveis.
- Espelha metadados de execuções de cron a partir de um ledger compatível, sem copiar prompts, saídas brutas ou erros sensíveis.
- Usa revalidação de cache para páginas/dados e referências CSS/JS versionadas por commit.

O portal não tem backend HTTP próprio nem banco de dados de publicações: lê arquivos JSON. O coletor depende do formato esperado de `executions.db` e dos arquivos de jobs, não é um conector universal para qualquer agente. Tokens, custos e duração só aparecem quando há uma fonte real.

## Configuração

| Variável | Finalidade | Padrão |
|---|---|---|
| `CENTRAL_HTTP_USER` | Nome do usuário de Basic Auth na primeira instalação | `central_user` |
| `CENTRAL_OS_USER` | Conta Linux que recebe as credenciais locais | `SUDO_USER` ou a conta do processo |
| `CENTRAL_GIT_REMOTE` | URL exata do `origin` autorizado para release | Sem padrão: envio recusado até configurar |
| `HERMES_HOME` | Diretório do agente/ledger consultado por `sync_cron.py` | `%LOCALAPPDATA%/agente` |

`deploy/setup-local.py` calcula o caminho de `site/` a partir do checkout e grava a configuração renderizada **fora do Git**. Não é necessário criar uma conta Linux chamada `usuario` nem editar o template com um caminho pessoal. Por segurança, caminhos de instalação contendo `$` são recusados, pois o nginx os interpretaria como variáveis.

As variáveis precisam estar disponíveis ao processo que as usa. Para o Agendador do Windows, configure-as no ambiente do usuário antes de instalar a tarefa. Definir uma variável apenas no shell atual não a disponibiliza à tarefa.

## Instalação local

Requisitos: Python 3, Git e, no Ubuntu/WSL, nginx e `htpasswd` (pacote `apache2-utils`). Execute os comandos Linux na raiz do checkout acessível ao Ubuntu:

```bash
python3 -m unittest discover -s tests -v
sudo env CENTRAL_OS_USER="$(id -un)" python3 deploy/setup-local.py
```

O instalador gera uma senha na primeira instalação, sem imprimi-la, e guarda as credenciais em `~/.config/central_operacoes_agente/credentials`, fora do repositório, com permissão `0600`. A autenticação efetiva usa `/etc/nginx/central_operacoes.htpasswd`. O instalador não troca senhas já existentes; alterar `CENTRAL_HTTP_USER` sozinho não migra uma instalação antiga.

- URL local: `http://localhost:8088/`.
- Validar configuração: `sudo nginx -t`.
- Iniciar nginx, se necessário: `sudo nginx`.
- Alterar a senha sem colocá-la na linha de comando: `sudo htpasswd -B /etc/nginx/central_operacoes.htpasswd central_user`, substituindo o usuário se você configurou outro.

No WSL2 em modo NAT, o nginx escuta nas interfaces da VM para permitir o encaminhamento de localhost do Windows. Basic Auth não substitui HTTPS: não exponha essa porta à rede externa com portproxy/firewall sem rever a instalação. Domínio, TLS e subdomínios não estão configurados neste esqueleto.

## Publicação e release

Prepare um JSON revisado **fora do repositório**, com `id` (slug), `module` (`operacoes`, `rotinas`, `conteudos`, `dashboards`, `relatorios` ou `pesquisas`), `title`, `summary`, `timestamp` ISO-8601 com fuso, `relevant` (booleano), `body` opcional e `media` (lista de caminhos de arquivos locais). Informe métricas somente quando medidas.

Antes de qualquer envio, confira o destino e autorize sua URL exata. Exemplo de configuração no shell Linux:

```bash
git remote get-url origin
export CENTRAL_GIT_REMOTE="$(git remote get-url origin)"
python3 scripts/publish.py caminho/para/entrada-revisada.json
# Para alterações gerais, após revisão do diff:
python3 scripts/release.py "Descrição da alteração"
```

**Esses comandos fazem commit e push.** `release.py` recusa o envio quando `CENTRAL_GIT_REMOTE` está ausente ou não corresponde ao `origin`. Atribuir a variável não substitui a revisão do destino. No modo geral, o script inclui todas as alterações não ignoradas; mantenha trabalhos não relacionados fora desse checkout.

Um repositório público expõe os arquivos publicados independentemente do Basic Auth local. Para usar dados operacionais privados, configure uma cópia com remoto privado. Nunca publique credenciais, prompts, saídas brutas, erros sensíveis ou mídia sem autorização.

## Cron e monitoria (opcionais)

`python deploy/install-sync.py`, executado no Windows, instala a tarefa **AgenteCentralSync**. Ela consulta o ledger `executions.db` e os arquivos de jobs a cada minuto enquanto o usuário está conectado. Execuções terminais viram publicações deduplicadas; o painel mostra estado dos jobs. O primeiro ciclo também indexa execuções anteriores disponíveis no ledger.

A instalação da tarefa é opcional e **não foi realizada para preparar este esqueleto**. Configure o diretório do agente e o remoto adequado antes de ativá-la. Alterações detectadas passam pelos testes e por `scripts/release.py`; sem remoto autorizado, o envio é recusado.

- Consultar a tarefa: `schtasks /query /tn AgenteCentralSync /v /fo list`.
- Log do coletor: `%LOCALAPPDATA%/agente/central-operacoes-sync.log`.
- Sem sessão Windows ativa, não há sincronização. O agente precisa estar ativo para executar seus próprios jobs.
- Outros trabalhos não são capturados automaticamente: publique entregas relevantes com `scripts/publish.py`.

## Testes

```bash
python3 -m unittest discover -s tests -v
# Verificar também que o esqueleto ainda não tem histórico de uso:
CENTRAL_CHECK_TEMPLATE_DATA=1 python3 -m unittest discover -s tests -v
```

A verificação de catálogo vazio é opt-in, para não bloquear publicações legítimas depois da instalação. Os testes do instalador usam APIs Linux e devem rodar no Ubuntu/WSL.

## Estrutura

- `site/` — portal estático, catálogo JSON, status e publicações.
- `scripts/portal.py` — validação de entradas, geração de páginas e coleta de metadados.
- `scripts/publish.py` — publicação de conteúdo revisado.
- `scripts/sync_cron.py` — espelhamento opcional de execuções.
- `scripts/release.py` — testes, commits, versionamento de assets e push protegido por remoto explícito.
- `deploy/` — template nginx, instalação local e tarefa Windows opcional.
- `tests/` — testes do portal, observabilidade e configuração do esqueleto.

## Design

Adaptação do sistema utilizando modelos do https://getdesign.md/design-md/ para uma superfície operacional. Na fonte usamos Helvetica/Arial.
