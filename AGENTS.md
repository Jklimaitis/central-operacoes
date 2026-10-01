# Central de Operações — regras do projeto

- Antes de alterar o portal, confira o design system indicado em README.md e preserve acessibilidade, responsividade, cabeçalhos de cache e autenticação no nginx.
- Toda alteração no projeto deve terminar com testes, commit e push para o repositório privado `seu-usuario/seu-repo`. Use `python scripts/release.py "mensagem"` e verifique `git status` e o commit remoto.
- Para novos CSS/JS, atualize as referências versionadas no HTML com o SHA do commit que contém os assets. `scripts/release.py` automatiza isso.
- Nunca coloque senhas, arquivos de autenticação ou tokens no Git. Credenciais locais ficam somente fora do repositório.
- Módulos novos devem entrar como navegação real, sem cartões vazios de métricas inventadas.
- Todo conteúdo/mídia criado deve virar publicação no módulo adequado; dashboards, pesquisas e análises entram após avaliação de relevância. `scripts/publish.py` recebe JSON revisado e faz commit+push. Inclua mídia local (hash copiado), página dedicada quando relevante e métricas somente com fonte real; nunca publique senhas/prompts/erros brutos.
- Cron jobs criados neste perfil são espelhados automaticamente pelo Agendador do Windows `AgenteCentralSync` a cada minuto, desde que haja sessão Windows ativa. Após criar um cron, confira `listar jobs de cron do agente`, a tarefa agendada e o card/status após a primeira execução; não declare observabilidade completa antes de verificar.
- Feed e módulos em ordem decrescente por data, filtros de módulo/nome e opção de ordem crescente; usar exclusivamente componentes/tokens de `https://getdesign.md/design-md/meta/DESIGN.md`. Subdomínios aguardam domínio/DNS/TLS; por ora usar caminhos locais.
- O observador de cron só copia metadados do ledger; o histórico completo permanece no Agente. Outros trabalhos não são capturados automaticamente; publicar manualmente com a skill.