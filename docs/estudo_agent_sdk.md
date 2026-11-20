# Estudo do Claude Agent SDK (D28)

Anotações para construir o agente de verificação do D29. Versão estudada: `claude-agent-sdk` 0.2.186 (Python), consultada em 2026-11-20. O exemplo executável está em `scripts/estudo_agent_sdk.py`.

## O que é

O Agent SDK é o Claude Code empacotado como biblioteca. O pacote Python traz um executável do Claude Code dentro da roda (`win_amd64`), então não é preciso instalar o CLI à parte. O SDK conversa com esse executável, que roda o laço do agente: pergunta ao modelo, executa ferramentas e devolve o resultado.

**Autenticação:**

- O SDK lê o login guardado pelo Claude Code em `%USERPROFILE%\.claude\.credentials.json`. Com o plano Pro, o consumo sai dos limites da assinatura (decisão de 2026-11-20).
- Estas fontes passam na frente da assinatura, e o script de estudo para se encontrar qualquer uma delas definida:
  - variáveis de nuvem (`CLAUDE_CODE_USE_BEDROCK`, `_VERTEX`, `_FOUNDRY`, `_ANTHROPIC_AWS`);
  - `ANTHROPIC_AUTH_TOKEN`;
  - `ANTHROPIC_API_KEY`;
  - `apiKeyHelper` nas configurações.
- A mensagem inicial da sessão traz `apiKeySource`. O valor `none` confirma que nenhuma chave de API está em uso.

## `query()` × `ClaudeSDKClient`

| | `query()` | `ClaudeSDKClient` |
|---|---|---|
| Sessão | nova a cada chamada | a mesma entre perguntas |
| Conversa | uma troca (o agente pode dar vários passos dentro dela) | várias trocas com contexto |
| Interromper | não | sim (`interrupt()`) |
| Uso típico | tarefa única, roteiro automatizado | conversa, decisão que depende da resposta |

As duas formas devolvem um iterador assíncrono de mensagens:

- `SystemMessage`, cujo `init` traz o modelo, as ferramentas e a origem da chave;
- `AssistantMessage`, com blocos `TextBlock` e `ToolUseBlock`;
- `ResultMessage`, a última.

Para o agente de verificação, que faz uma tarefa e termina, `query()` basta.

## `ClaudeAgentOptions` (campos usados aqui)

- **`system_prompt`:** um texto próprio substitui o prompt do Claude Code. Também aceita o preset `claude_code`, com `append`, ou um arquivo.
- **`tools`:** define quais ferramentas embutidas *existem* no contexto. `tools=[]` remove todas.
- **`allowed_tools`:** *pré-aprova* ferramentas, mas não restringe nada. Uma ferramenta fora da lista continua disponível e cai na regra de permissão.
- **`disallowed_tools`:**
  - um nome puro (`"Bash"`) remove a ferramenta do contexto;
  - uma regra com escopo (`"Bash(rm *)"`) nega as chamadas que casam com ela, em qualquer modo.
- **`permission_mode`:**
  - `default`: chamada sem aprovação vai para o callback `can_use_tool`;
  - `dontAsk`: tudo que pediria permissão é negado;
  - `acceptEdits`: aprova edições de arquivo;
  - `plan`, `auto`;
  - `bypassPermissions`: aprova quase tudo, e `allowed_tools` *não* o limita.
- **`cwd`:** diretório de trabalho. Leituras dentro dele não pedem permissão, o que é mais um motivo para tirar as ferramentas embutidas.
- **`max_turns`:** limite de turnos do laço.
- Também úteis: `setting_sources=[]` (não carrega `CLAUDE.md`, `settings.json` nem agentes do projeto), `mcp_servers`, `max_budget_usd` (teto da *estimativa* de custo) e `model`.

Ordem de avaliação de uma chamada de ferramenta: hooks → regras de negação → regras de pergunta → modo de permissão → regras de permissão → `can_use_tool`.

## Ferramentas próprias

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

@tool("resultado_testes", "Lê o resumo da última execução do pytest", {},
      annotations=ToolAnnotations(readOnlyHint=True))
async def resultado_testes(args):
    return {"content": [{"type": "text", "text": "..."}]}

servidor = create_sdk_mcp_server(name="verificacao", tools=[resultado_testes])
```

- O servidor MCP roda dentro do mesmo processo Python, sem processo à parte.
- O nome visto pelo modelo é `mcp__<chave em mcp_servers>__<nome>`, por exemplo `mcp__verif__resultado_testes`.
- Para devolver erro, o handler retorna `"is_error": True`. Uma exceção não tratada também vira erro para o modelo, e o laço continua.
- `readOnlyHint` é só metadado e não impede escrita. Quem garante a leitura é o próprio código do handler.

## Restringir o agente às ferramentas próprias

```python
ClaudeAgentOptions(
    tools=[],                                  # nenhuma ferramenta embutida (Bash, Read, Edit, Agent...)
    disallowed_tools=["mcp__claude_ai_*"],     # conectores da conta do claude.ai (ver abaixo)
    mcp_servers={"verif": servidor},
    allowed_tools=["mcp__verif__resultado_testes", ...],  # lista explícita, sem curinga
    permission_mode="dontAsk",                 # o que não estiver pré-aprovado é negado
    setting_sources=[],                        # nada de settings, hooks ou MCP do projeto
)
```

**Achado da execução de 2026-11-20:** com login do plano, os conectores da conta do claude.ai (no caso, o Claude Docs, com ferramentas de criar e apagar documentos) entram no contexto mesmo com `tools=[]` e `setting_sources=[]`. A regra `disallowed_tools=["mcp__claude_ai_*"]` os removeu: a lista `tools` da mensagem `init` ficou vazia. O D29 deve conferir essa lista no `init` e parar se aparecer qualquer ferramenta fora das próprias.

São quatro camadas:

- `tools=[]` tira as ferramentas embutidas do contexto;
- a negação de `mcp__claude_ai_*` tira os conectores da conta;
- `allowed_tools` aprova só as próprias;
- `dontAsk` nega o resto sem perguntar.

Não usar `bypassPermissions`. Como reforço, `disallowed_tools=["Bash", "Write", "Edit"]` não custa nada. A gravação do relatório pode ser uma ferramenta própria que escreve só em `reports/`, com o nome do arquivo montado pelo código e não pelo modelo.

## Medir o consumo de uma execução

A `ResultMessage` final traz:

- `usage`: tokens de entrada, saída e cache, só do laço principal;
- `model_usage`: tokens e custo por modelo, incluindo subagentes. É o campo preferido para totais;
- `total_cost_usd`: custo estimado;
- `num_turns`, `duration_ms`, `duration_api_ms` e `session_id`.

Cuidados:

- `total_cost_usd` e `costUSD` são **estimativas locais a preço de API**. No plano Pro não há cobrança por uso: o consumo sai do limite da assinatura, e a página de suporte não informa quanto do limite cada execução gasta.
- O `output_tokens` das `AssistantMessage` intermediárias é provisório, e o valor certo vem na `ResultMessage`.
- Mensagens com o mesmo `message_id` contam uma vez só.
- Os resultados de erro (`error_max_turns`, `error_during_execution`) também trazem uso.

Na execução de estudo, uma pergunta de uma frase gerou duas chamadas de modelo: a do Opus 5.5 com a resposta e uma do Haiku 5.5, auxiliar interna do Claude Code. As duas aparecem em `model_usage`, e a estimativa total foi de US$ 0,03, a preço de API.

Para o D29, o relatório pode registrar `num_turns`, `usage`, `model_usage` e a estimativa, rotulada como estimativa.

## Plano aprovado para o D29 (2026-11-20)

O plano foi implementado no D29. As diferenças em relação a ele estão na decisão D29, em `docs/decisoes.md`: `gravar_relatorio` virou `entregar_relatorio`, e entrou `saida_passo`.

1. **Executor determinístico** em `src/brasil_em_dados/verificacao/`:
   - roda sempre o `pytest`;
   - roda a coleta, a carga e o `aplicar_gold` só com as flags `--coleta`, `--carga` e `--gold`, nunca a pedido do agente;
   - guarda as saídas em `reports/execucao_<timestamp>/`.
2. **Ferramentas próprias, todas de leitura:**
   - `resultado_testes`;
   - `controle_execucao` e `consulta_qualidade(nome)`: rodam como `bed_readonly`, com `SET TRANSACTION READ ONLY`, como o revisor-de-qualidade-de-dados. A `consulta_qualidade` só aceita nomes de um catálogo fixo em `sql/verificacao/`;
   - `relatorio_anterior`.

   A única escrita é a de `gravar_relatorio`. O caminho dela é montado pelo código, `reports/verificacao_AAAAMMDDTHHMMSS.md`, e um arquivo existente nunca é sobrescrito.
3. **Configuração do agente:**
   - opções `tools=[]`, `disallowed_tools=["mcp__claude_ai_*"]`, `allowed_tools` com a lista explícita, `permission_mode="dontAsk"`, `setting_sources=[]` e `max_turns`;
   - ao iniciar, a trava de credenciais;
   - a lista `tools` do `init` é conferida, e o agente para se houver ferramenta inesperada.
4. **O relatório registra:**
   - as flags que o executor recebeu;
   - o usuário do banco com que cada passo rodou (`bed_app` nos testes de integração e na carga; `bed_readonly` nas ferramentas do agente);
   - turnos, tokens e a estimativa de custo.
5. **Divisão de papéis:** o executor decide se cada passo passou ou falhou. O agente resume e cita a ferramenta de cada número.
6. **Riscos:**
   - a URL e a senha do banco nunca aparecem no texto devolvido ao modelo;
   - dados lidos são tratados como dados, nunca como instruções;
   - o login expira, e cada execução consome o limite do plano.

## Fontes consultadas (2026-11-20)

- https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- https://code.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/agent-sdk/quickstart
- https://code.claude.com/docs/en/agent-sdk/python
- https://code.claude.com/docs/en/agent-sdk/custom-tools
- https://code.claude.com/docs/en/agent-sdk/permissions
- https://code.claude.com/docs/en/agent-sdk/cost-tracking
- https://code.claude.com/docs/en/authentication
- https://pypi.org/project/claude-agent-sdk/0.2.186/
