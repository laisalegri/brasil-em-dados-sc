# CLAUDE.md — Brasil em Dados SC

Contexto, regras e comandos para o Claude Code neste repositório. Leia também `docs/escopo_mvp.md`, `docs/decisoes.md` e `docs/cronograma.md` antes de propor mudanças de escopo ou de modelagem.

## O projeto

Pipeline de dados públicos do IBGE sobre os 295 municípios de Santa Catarina (UF 42), de 2010 a 2023: população (censo e estimativa), PIB nominal e PIB per capita oficial. Arquitetura RAW → SILVER → GOLD em Python + PostgreSQL local, com EDA em Jupyter e dashboards em Power BI e Streamlit.

É um projeto de portfólio e de aprendizado. A autora trabalha 3 horas por dia, seguindo cartões D01–D42 (Trello). Ao começar uma tarefa, pergunte qual é o cartão do dia se não estiver claro.

O cronograma dos cartões está em `docs/cronograma.md`. Ao concluir um cartão, marque ✅ na linha dele (troque ⬜ por ✅).

## Estrutura

- `src/brasil_em_dados/` — pacote Python: `extract/` (coleta das APIs), `load/` (carga no PostgreSQL), `transform/` (normalização)
- `sql/ddl/`, `sql/silver/`, `sql/gold/` — scripts SQL por camada
- `data/raw/`, `data/processed/` — gerados pelo pipeline, não versionados
- `tests/` — pytest
- `notebooks/` — EDA
- `dashboards/powerbi/`, `dashboards/streamlit/`
- `docs/` — escopo, decisões, dicionário de dados, metodologia
- `.claude/agents/` — subagents do projeto (versionados)
- `reports/` — relatórios do agente de verificação, não versionados

## Ambiente e comandos (Windows, PowerShell)

```powershell
.venv\Scripts\Activate.ps1        # ativar o ambiente
pip install -r requirements.txt    # dependências
pip install -e .                   # pacote local em modo editável
pytest                             # todos os testes
pytest tests/test_x.py -v          # um arquivo de teste
```

- Python 3.11+. Use sempre o `.venv` da raiz.
- Credenciais ficam em `.env` (modelo em `.env.example`), lidas com `python-dotenv`.

## Fontes de dados

- API de Localidades: `https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios`
- API SIDRA: `https://apisidra.ibge.gov.br/`. Tabelas candidatas: 6579 (estimativas, var. 9324), 1378 (Censo 2010), 4709 (Censo 2022, var. 93), 5938 (PIB, var. 37), 5964 (setores, extensão).
- Antes de escrever um extrator, valide metadados, filtros, unidades e anos disponíveis. Tabelas e variáveis só são consideradas confirmadas quando registradas em `docs/`.

## Regras de dados (não negociáveis)

1. Código IBGE do município é texto de 7 dígitos e é a chave em todas as camadas. Nome de município nunca é chave.
2. Censo e estimativa nunca se misturam sem rótulo: toda linha de população tem `tipo_medida`.
3. PIB é nominal. Nunca descreva variação de PIB como crescimento econômico real.
4. PIB per capita é o valor publicado pelo IBGE, sem recálculo. Nunca o trate como renda.
5. Ausência é `NULL`, nunca zero. Não interpole nem projete valores.
6. Municípios instalados depois de 2010 têm ausência esperada nos anos anteriores; isso não é erro.
7. RAW é imutável: cada coleta grava arquivo novo com timestamp, URL e parâmetros. Nunca sobrescreva nem apague RAW.
8. Toda linha da tabela fato guarda fonte, tabela/variável SIDRA, unidade e data de coleta.
9. Sinais especiais do SIDRA: `-` e `0` carregam como 0; `...`, `..`, `X` e letras de faixa carregam como `NULL`. O sinal original fica na coluna `sinal_origem` (texto, `NULL` quando o valor veio numérico). Legenda em `docs/fontes/sidra_convencoes.md`.

## Como trabalhar comigo

- Mudanças pequenas e incrementais. Explique o que vai fazer antes de editar vários arquivos.
- Eu estou aprendendo: ao introduzir um conceito ou biblioteca nova, explique em poucas linhas o porquê.
- Rode `pytest` depois de qualquer mudança em `src/` ou `tests/` e mostre o resultado.
- Código novo em `src/` vem com teste em `tests/`.
- Não faça `git commit` nem `git push` sem eu pedir. Sugira mensagens de commit em inglês no padrão Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`), no imperativo e em minúsculas. Não cite o cartão do dia na mensagem.
- Nunca leia, imprima ou versione o conteúdo de `.env`. Nunca coloque credenciais em código, notebook ou log.
- Não adicione dependências sem perguntar; quando aprovadas, atualize `requirements.txt`.
- Não introduza Docker, Airflow, Spark ou serviços de nuvem: estão fora do escopo do MVP.
- Agentes têm acesso somente leitura ao banco; nenhuma alteração de dados sem eu pedir.
- Decisões de modelagem ou de escopo vão para `docs/decisoes.md` (data, decisão, motivo).

## Estilo de código

- Python com type hints e docstrings curtas em português.
- Funções pequenas e testáveis; I/O (HTTP, arquivos, banco) separado da lógica de transformação.
- Logs com `logging`, não `print`, no código do pipeline.
- SQL em arquivos `.sql` em `sql/`, nomes de tabelas e colunas em `snake_case` sem acentos.
