# Registro de decisões

Decisões de projeto, da mais recente para a mais antiga. Cada entrada registra o que foi decidido, por quê e o que fica de fora.

## 2026-11-12 — D06: hierarquia territorial na `dim_municipio`

- **Decisão:** a `dim_municipio` guarda as duas divisões regionais do IBGE, com códigos em texto e nomes de coluna explícitos por divisão:
  - divisão nova: `cod_regiao_imediata`, `nome_regiao_imediata`, `cod_regiao_intermediaria`, `nome_regiao_intermediaria`;
  - divisão antiga: `cod_microrregiao`, `nome_microrregiao`, `cod_mesorregiao`, `nome_mesorregiao`.

  Os dashboards usam a divisão nova, com a região intermediária como filtro principal. As duas divisões nunca se relacionam pelo id.
- **Por quê:** a API de Localidades entrega as duas hierarquias completas, e a divisão nova substitui a antiga. Manter a antiga permite comparar com análises e publicações anteriores. Os ids de mesorregião e de região intermediária usam a mesma faixa (4201–4207) para entidades diferentes; por exemplo, a mesorregião 4201 é o Oeste Catarinense e a intermediária 4201 é Florianópolis. Nomes de coluna genéricos (como `cod_regiao`) permitiriam junções erradas.
- **Consequência:** a carga converte todos os ids para texto. Detalhes da fonte estão em `docs/fontes/ibge_localidades.md`.

## 2026-11-12 — D07: sinais especiais do SIDRA e coluna `sinal_origem`

- **Decisão:** a tabela fato terá a coluna `sinal_origem` (texto), com o sinal SIDRA original. Ela fica `NULL` quando o valor veio numérico. Os sinais `-` (zero absoluto) e `0` (zero por arredondamento) carregam como 0. Os demais (`...`, `..`, `X` e letras de faixa) carregam como `NULL`.
- **Por quê:** a regra "ausência é `NULL`, nunca zero" não deve apagar a informação de *por que* o valor falta. Guardar o sinal mantém a rastreabilidade até a fonte e distingue zero verdadeiro de ausência. Exemplo: Pescaria Brava e Balneário Rincão vêm com `...` em 2011 na tabela 6579.
- **Consequência:** o significado de cada sinal está em `docs/fontes/sidra_convencoes.md`. Os testes de carga devem verificar que nenhum sinal vira zero indevidamente.

## 2026-11-11 — D02: dados brutos fora do Git

- **Decisão:** `data/raw/`, `data/processed/` e `reports/` não são versionados. O pipeline recria esses arquivos.
- **Por quê:** manter o repositório leve e garantir que os dados venham sempre da fonte oficial, de forma reproduzível.
- **Consequência:** amostras pequenas usadas em testes ou na documentação ficam em `tests/` ou `docs/`.

## 2026-11-11 — D01: escopo do MVP

| Decisão | Motivo |
| --- | --- |
| Indicadores do MVP: população (censo e estimativa), PIB nominal e PIB per capita | São as fontes com tabelas identificadas; a estrutura setorial ainda depende de validação (D10) |
| Estrutura setorial fica como extensão | Tabela candidata 5964 e códigos setoriais não confirmados |
| Período 2010–2023 e cadastro atual de 295 municípios | Mantém o Censo 2010; municípios instalados depois de 2010 têm ausência esperada e documentada |
| PIB per capita: valor publicado pelo IBGE, sem recálculo | Usa a referência oficial; a população usada como denominador será documentada |
| Variação populacional oficial: Censo 2010 × Censo 2022 | Estimativas aparecem só como série complementar |
| MVP roda localmente; publicar o Streamlit (sem agente) é a primeira extensão | Evita custo e infraestrutura no MVP |
| Agentes de IA servem ao desenvolvimento; agente de perguntas de negócio é extensão | Prioriza entregar mais rápido e com qualidade |
