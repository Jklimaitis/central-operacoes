# Central de Operações — regras do projeto

- Este checkout é o esqueleto público. Não confundir com uma instalação privada nem copiar dados de uso, credenciais ou configurações pessoais para ele.
- Antes de alterar o portal, confira o design system indicado em README.md e preserve acessibilidade, responsividade, cabeçalhos de cache e autenticação no nginx.
- Toda alteração autorizada deve terminar com testes e revisão do diff. Antes de commit/push, confira `origin`; `CENTRAL_GIT_REMOTE` deve conter sua URL exata. Nunca publique para outro remoto por semelhança de nome.
- Use `python scripts/release.py "mensagem"` somente quando o envio estiver autorizado. O modo geral inclui todas as alterações não ignoradas; preserve trabalhos não relacionados. Depois confira `git status` e o commit remoto.
- Para novos CSS/JS, atualize as referências versionadas no HTML com o SHA do commit que contém os assets. `scripts/release.py` automatiza isso.
- Nunca coloque senhas, arquivos de autenticação, tokens, caminhos pessoais ou dados privados no Git. Credenciais e configurações renderizadas ficam fora do repositório.
- O instalador calcula o caminho de `site/` pelo checkout e resolve a conta Linux por `CENTRAL_OS_USER`, `SUDO_USER` ou usuário do processo. Não fixe nomes de contas nem caminhos de instalação no template.
- Módulos novos devem entrar como navegação real, sem cartões de métricas inventadas. Inclua custos, tokens e duração somente com fonte registrada.
- `scripts/publish.py` recebe JSON revisado e faz commit+push. Revise conteúdo e mídia antes; Basic Auth local não protege os arquivos enviados a um remoto público. Dados operacionais privados exigem uma cópia com destino privado.
- O Agendador do Windows `AgenteCentralSync` é opcional; não o instale durante manutenção do código sem autorização específica. Após uma instalação autorizada, verifique tarefa, ledger e card/status antes de declarar observabilidade funcionando.
- O observador de cron copia apenas metadados do ledger; o histórico completo permanece no agente. Outros trabalhos não são capturados automaticamente.
- Feed e módulos em ordem decrescente por data, filtros de módulo/nome e opção de ordem crescente; preserve os componentes/tokens de `https://getdesign.md/design-md/meta/DESIGN.md`. Subdomínios aguardam domínio/DNS/TLS.
- Execute `python3 -m unittest discover -s tests -v` no Ubuntu/WSL. Na preparação do esqueleto, rode também com `CENTRAL_CHECK_TEMPLATE_DATA=1`; depois de publicações legítimas, não exija catálogo vazio nos testes normais.
