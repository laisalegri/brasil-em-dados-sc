"""App Streamlit (D36): implementação de docs/dashboards.md.

- textos: avisos das regras, formatadores pt-BR e títulos que afirmam o achado (sem Streamlit);
- calculos: recortes por região, participação regional e posições (sem Streamlit, sem I/O);
- figuras: gráficos plotly com a paleta e o rodapé dos notebooks (sem Streamlit);
- dados: leitura cacheada das funções de brasil_em_dados.analise (views gold, bed_readonly);
- filtros e componentes: filtros globais e blocos de tela reaproveitados pelas páginas.

Regra 11: nenhum valor é convertido; os formatadores só mudam o texto dos rótulos.
"""
