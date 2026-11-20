# Cronograma realizado — Brasil em Dados SC

O que foi feito, cartão a cartão. Reconstruído em 20/11/2026 a partir do `git log` e de `docs/decisoes.md`. O plano original está em [cronograma_previsto.md](cronograma_previsto.md), congelado.

- **"Feito em":** data do último commit do cartão, no fuso America/Sao_Paulo. Consulta usada: `TZ=America/Sao_Paulo git log --date=format-local:'%d/%m/%Y %H:%M'`.
- **Atribuição dos commits:** as mensagens não citam o cartão. Cada commit foi atribuído pelo cartão que ele marcou como ✅ no cronograma e pelos arquivos que alterou.
- **Datas não confirmadas:** nenhuma até aqui. Todo cartão concluído tem commit.

## Resumo (até 20/11/2026)

| | Previsto | Realizado |
|---|---|---|
| Cartões D01–D30 | 30 cartões em 30 dias de trabalho (11/11 a 15/12) | 26 concluídos e 4 absorvidos, em 6 dias com commits (11, 12, 14, 17, 18 e 20/11) |
| Cartões pendentes | — | 12 (D31 a D42) |
| Fechamento do MVP | D39, em 26/12 | Em andamento |

Os dias de trabalho realizados contam só os dias com commit; um dia de trabalho sem commit não aparece no git. Cada cartão previa 3 horas.

### Mudanças de escopo relevantes

- **Setores do PIB fora do MVP** (D10, 12/11):
  - o valor adicionado por setor virou extensão, porque a série setorial termina em 2021 e a pergunta central não inclui a estrutura produtiva;
  - a tabela candidata 5964 foi descartada, porque é da PeNSE 2015.
- **Agentes para o desenvolvimento** (D01, 11/11):
  - os agentes de IA apoiam o desenvolvimento: subagents do Claude Code e o agente de verificação com o Agent SDK;
  - o agente de perguntas de negócio para usuários finais virou extensão.
- **`dim_serie` separada da `dim_indicador`** (ajuste na revisão do dicionário, D10, 12/11):
  - a origem técnica (tabela ou variável, unidade de origem, fator de conversão, data de referência) foi para uma dimensão própria, e cada linha da fato aponta para a sua série;
  - isso permite um `pop_censo` único com duas origens (1378 e 4709).
- **GOLD em views** (D30, 18/11): a camada GOLD são views recriadas por `aplicar_gold`, e não tabelas, e fica fora do controle `ddl_aplicado`.
- **Cartões absorvidos:**
  - o controle de execução (D15) entrou no padrão de coleta (D11);
  - as normalizações da SILVER (D23–D25) entraram na carga da fato (D21), que faz o parse em memória, sem tabela de estágio.
- **Ordem diferente do plano:**
  - a GOLD (D30) foi feita antes do Agent SDK (D28–D29);
  - a autenticação do agente passou a ser pelo plano Pro, sem chave de API e sem teto de gasto (decisão de 20/11).

## Cartões

| Cartão | Título | Situação | Prevista | Principais entregas | Commits |
|---|---|---|---|---|---|
| D01 | Definir objetivo, escopo e critérios de sucesso | Feito em 11/11/2026 | 11/11/2026 | `docs/escopo_mvp.md` e decisão D01 | `b2af207` |
| D02 | Criar repositório e estrutura de pastas | Feito em 11/11/2026 | 12/11/2026 | Estrutura de pastas, `.gitignore` e decisão D02 (dados brutos fora do git) | `b2af207` |
| D03 | Configurar ambiente Python | Feito em 11/11/2026 | 13/11/2026 | `requirements.txt`, `pyproject.toml` e teste do ambiente | `ef5bafc` |
| D04 | Configurar Claude Code no projeto | Feito em 11/11/2026 | 14/11/2026 | `CLAUDE.md`, `.claude/settings.json` (negação de leitura do `.env`) e cronograma | `80b0ea5` |
| D05 | Criar subagents pesquisador-de-fontes e revisor-de-codigo | Feito em 12/11/2026 | 16/11/2026 | Os dois subagents, testados numa primeira investigação da 6579 | `560e5c9` |
| D06 | Mapear API de Localidades IBGE | Feito em 12/11/2026 | 17/11/2026 | `docs/fontes/ibge_localidades.md`, amostra em `tests/fixtures/` e decisão D06 | `36f2b73` |
| D07 | Investigar SIDRA: população | Feito em 12/11/2026 | 18/11/2026 | `docs/fontes/sidra_6579.md`, convenções de sinais do SIDRA e decisão D07 (`sinal_origem`) | `560e5c9`, `0770138`, `0e3cd36` |
| D08 | Investigar SIDRA: Censo 2010 e 2022 | Feito em 12/11/2026 | 19/11/2026 | `sidra_1378.md`, `sidra_4709.md`, datas de referência dos censos e decisão D08 | `b2603dc`, `3e43009` |
| D09 | Investigar SIDRA: PIB e PIB per capita | Feito em 12/11/2026 | 20/11/2026 | `sidra_5938.md`, per capita pela API de Pesquisas, conversão para reais e decisão D09 | `be729fc`, `e77134e` |
| D10 | Investigar setores e consolidar dicionário | Feito em 12/11/2026 | 21/11/2026 | `docs/dicionario_dados.md`, setores fora do MVP, `dim_serie` e decisão D10 | `2f389cd` |
| D11 | Desenhar padrão de coleta e rastreabilidade | Feito em 14/11/2026 | 23/11/2026 | `docs/padrao_coleta.md` (RAW imutável, metadados, controle de execução) e decisão D11 | `fca6017`, `f0705bd` |
| D12 | Criar extrator de municípios | Feito em 14/11/2026 | 24/11/2026 | Módulos comuns de coleta (HTTP, RAW, controle, catálogo) e extrator da API de Localidades | `b52240f`, `df7b4b2` |
| D13 | Criar extrator de população | Feito em 14/11/2026 | 25/11/2026 | Extratores SIDRA com validação de conteúdo e linha de comando `extract` | `b52240f`, `df7b4b2` |
| D14 | Criar extrator de PIB | Feito em 14/11/2026 | 26/11/2026 | Extrator da 5938 e da API de Pesquisas (indicador 47001) | `b52240f`, `df7b4b2` |
| D15 | Criar controle de execução | Absorvido pelo D11 | 27/11/2026 | Controle de execução definido no padrão de coleta e implementado nos módulos comuns | `fca6017`, `b52240f` |
| D16 | Criar subagent escritor-de-testes e testar falhas | Feito em 14/11/2026 | 28/11/2026 | Subagent escritor-de-testes, testes de falhas de coleta e HTTP, códigos conferidos no cadastro e decisão D16 | `776c49d` |
| D17 | Criar banco e usuário de projeto | Feito em 17/11/2026 | 30/11/2026 | `00_banco_e_usuarios.sql`, conexões `bed_app` e `bed_readonly` e decisão D17 | `b93bca1` |
| D18 | Criar dim_municipio e dim_indicador | Feito em 17/11/2026 | 01/12/2026 | Schemas e dimensões com restrições, `aplicar_ddl` com `ddl_aplicado` e decisão D18/D19 | `7927d9b` |
| D19 | Criar fato_indicador_municipio e controle | Feito em 17/11/2026 | 02/12/2026 | Fato com FK composta para a série, `controle_execucao` e regras de dados no banco | `7927d9b` |
| D20 | Carregar dimensões | Feito em 17/11/2026 | 03/12/2026 | Carga idempotente das dimensões (RAW e catálogo), atributos imutáveis e decisão D20 | `ae9a70c` |
| D21 | Carregar a fato e o controle a partir da RAW | Feito em 18/11/2026 | 04/12/2026 | Carga da fato com conversão em `Decimal`, carga do controle e decisão D21 | `2a942eb` |
| D22 | Criar subagent revisor-de-qualidade-de-dados | Feito em 18/11/2026 | 05/12/2026 | Subagent somente leitura (`bed_readonly`, `SET TRANSACTION READ ONLY`) | `310b5d1`, `1a9e7a5` |
| D23 | Normalizar população | Absorvido pelo D21 | 07/12/2026 | Normalização feita na carga da fato | `2a942eb` |
| D24 | Normalizar PIB municipal | Absorvido pelo D21 | 08/12/2026 | Normalização feita na carga da fato | `2a942eb` |
| D25 | Tratar população censitária e estimada | Absorvido pelo D21 | 09/12/2026 | Censo e estimativa separados pelo `tipo_medida` desde a carga | `2a942eb` |
| D26 | Validar qualidade e criar testes automatizados | Feito em 18/11/2026 | 10/12/2026 | 14 testes de qualidade (T1 a T16, sem T9 e T12), alertas investigados em fontes oficiais, regras 12 e 13 e decisão D26 | `310b5d1`, `1a9e7a5`, `4fe3c4f`, `08539dc` |
| D27 | Criar subagent documentador e documentar limitações | Feito em 18/11/2026 | 11/12/2026 | Subagent documentador, `docs/limitacoes.md`, `docs/metodologia.md` e README | `79e09ae` |
| D28 | Estudar ciclo básico do Agent SDK em Python | Feito em 20/11/2026 | 12/12/2026 | Autenticação pelo plano Pro, `scripts/estudo_agent_sdk.py` com a trava de credenciais e `docs/estudo_agent_sdk.md` | `bc87853`, `769081d` |
| D29 | Construir agente de verificação do pipeline | Feito em 20/11/2026 | 14/12/2026 | `python -m brasil_em_dados.verificacao`: executor determinístico, agente Sonnet com ferramentas de leitura, relatório em `reports/` e decisão D29 | `a76cd5b` |
| D30 | Construir camada GOLD | Feito em 18/11/2026 | 15/12/2026 | Sete views em `sql/gold/`, `aplicar_gold` e decisão D30 | `f4eb2bd` |
| D31 | Analisar população e evolução municipal | Pendente | 16/12/2026 | — | — |
| D32 | Analisar PIB e estrutura econômica | Pendente | 17/12/2026 | — | — |
| D33 | Produzir EDA e conclusões | Pendente | 18/12/2026 | — | — |
| D34 | Definir narrativa e KPIs | Pendente | 19/12/2026 | — | — |
| D35 | Construir dashboard Power BI | Pendente | 21/12/2026 | — | — |
| D36 | Construir app Streamlit | Pendente | 22/12/2026 | — | — |
| D37 | Validar consistência entre dashboards | Pendente | 23/12/2026 | — | — |
| D38 | Revisão final com subagents | Pendente | 24/12/2026 | — | — |
| D39 | Pipeline do zero, README e portfólio | Pendente | 26/12/2026 | — | — |
| D40 | Publicar Streamlit (extensão) | Pendente | 28/12/2026 | — | — |
| D41 | Reserva | Pendente | 29/12/2026 | — | — |
| D42 | Reserva | Pendente | 30/12/2026 | — | — |

Commit fora de cartão: `12d0db4` (12/11/2026), um ajuste do texto do cronograma (fonte do quadro e datas previstas).

## Como registrar um cartão concluído

No commit que conclui o cartão, troque "Pendente" por "Feito em DD/MM/AAAA" e preencha as principais entregas. Um commit não sabe o próprio hash, então os hashes entram no commit seguinte. O `cronograma_previsto.md` não é alterado.
