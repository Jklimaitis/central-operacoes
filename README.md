# Central de Operações

Portal estático local para indexar publicações, rotinas, conteúdos e incidentes. O feed usa dados reais; não exibe contagens ou custos inventados. Não há cron jobs cadastrados nesta instalação no momento inicial.

## Fluxo de publicação

- A página inicial tem busca por nome/título/módulo, filtro de módulo e ordenação por data (mais recentes primeiro); miniatura no card para imagens publicadas. Publicações relevantes têm página HTML dedicada com texto e mídia embutida (imagens ou vídeos).
- Prepare um JSON revisado **fora do repositório** com `id` (slug), `module` (`operacoes`, `rotinas`, `conteudos`, `dashboards`, `relatorios`, `pesquisas`), `title`, `summary`, `timestamp` com fuso ISO-8601, `relevant` (booleano), `body` (opcional) e `media` (lista de caminhos de arquivos locais). Informe `duration_seconds`, `model`, `tokens`, `cost_usd` somente se medidos/conhecidos. Ex.: `python scripts/publish.py caminho/para/entrada-revisada.json`. O comando copia mídia com nome hash, cria a publicação, testa, commita e envia ao Git privado.
- Revise privacidade e segredos antes de publicar. Mídia enviada ao Git privado e servida sob Basic Auth; não use imagens/dados sensíveis sem autorização. Hashes identificam arquivos imutáveis; dados e HTML continuam revalidados. O catálogo preserva todas as entradas e ordena por instante UTC decrescente.
- Sem domínio, os módulos ficam em caminhos de `localhost:8088/`. Para futuros `briefing.DOMINIO.com`, `ads.DOMINIO.com` e `gestao.DOMINIO.com`, será necessário domínio, DNS, TLS e configuração de proxy; não estão ativos agora.

## Cron e monitoria

- `python deploy/install-sync.py` instala a tarefa **TarefaSync** no Agendador do Windows. Ela consulta o ledger `executions.db` e os jobs do perfil Agente padrão **a cada minuto enquanto o usuário está conectado ao Windows**. Cada execução terminal (concluída, falha ou desconhecida) vira uma publicação deduplicada, e o painel mostra estado, falhas, execuções em curso e próxima execução dos jobs.
- Cada alteração detectada é testada, commitada e enviada ao repositório privado por `scripts/release.py`; novas publicações aparecem após o próximo ciclo e atualização automática da página. O primeiro ciclo também indexa execuções anteriores disponíveis no ledger.
- Por segurança, o espelho copia apenas metadados de execução: nunca copia prompts, saída bruta ou erros que possam conter segredos. O histórico completo permanece no Agente: `ferramenta de cron do agente` e `~/.agente/cron/output/` (equivalente do perfil ativo). Modelo é mostrado quando registrado no job; tokens/custos sem fonte confiável aparecem como não informados.
- Se a tarefa falhar, consulte `%LOCALAPPDATA%\\agente\\central-operacoes-sync.log` e `schtasks /query /tn TarefaSync /v /fo list`. Como o coletor depende da sessão do Windows, quando o PC estiver desligado/desconectado não há sincronização. O gateway Agente precisa estar ativo para executar cron jobs (`status do agente de cron`).
- Outros trabalhos do Agente **não são capturados automaticamente** neste estágio: publique entregas relevantes com `scripts/publish.py`. Subdomínios, captura integral de passos, telemetria de tokens/custo de todas as chamadas e alertas externos requerem integrações futuras; não confunda ausência de card com ausência de atividade.

## Ambiente local

- URL: `http://localhost:8088/` (nginx no Ubuntu/WSL; WSL2 em modo NAT encaminha o localhost do Windows para a porta 8088). O processo escuta nas interfaces **da VM WSL**, protegidas por Basic Auth; não configure portproxy/firewall para expor a porta à rede externa.
- Usuário HTTP: `usuario`. O arquivo `~/.config/central_operacoes_agente/credentials` existia na instalação inicial, mas pode ter sido removido após a troca da senha. A autenticação efetiva está no hash de `/etc/nginx/central_operacoes.htpasswd`; a senha atual não pode ser lida desse hash. Nunca coloque senha no Git.
- Para iniciar nginx: `wsl -d Ubuntu -u root -- nginx` (ou `sudo nginx` dentro do Ubuntu).
- Para validar nginx: `wsl -d Ubuntu -u root -- nginx -t`.
- Para trocar a senha sem expô-la na linha de comando: no Ubuntu execute `sudo htpasswd -B /etc/nginx/central_operacoes.htpasswd usuario`, digite e confirme a senha nos prompts ocultos. Não é necessário recarregar o nginx. Evite reutilizar uma senha compartilhada em chat.
- Sem VPS/domínio/TLS neste estágio. Para publicar futuramente, configure domínio, HTTPS e revise políticas de acesso.

## Estrutura

- `site/` — HTML, CSS, JS e futuro diretório `data/`; servido pelo nginx.
- `deploy/nginx-local.conf` — Basic Auth, ETag e revalidação sem cache para HTML/CSS/JS/data; cache curto apenas para imagens imutáveis.
- `scripts/release.py` — registra alterações no Git, carimba CSS/JS com SHA de commit, testa e faz push.
- `tests/` — verificações do portal.

## Regra obrigatória de atualização

**Toda modificação, inclusão ou remoção no projeto deve ser commitada e enviada ao repositório privado** `seu-usuario/seu-repo`. Depois de alterar, execute `python scripts/release.py "Descrição da alteração"`; confirme o push e o carregamento local. Não versionar credenciais, `.htpasswd`, tokens ou dados privados.

## Design

Adaptação do sistema em https://getdesign.md/design-md/meta/DESIGN.md para uma superfície operacional: canvas branco, cinzas suaves, tinta escura, azul cobalto em detalhes, cantos amplos e botões pill. A fonte Optimistic VF é proprietária e não está incluída; usamos Helvetica/Arial.
