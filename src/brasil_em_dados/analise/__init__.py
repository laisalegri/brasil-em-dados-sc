"""Análise exploratória (D31–D33): consultas às views da GOLD, cálculos e gráficos.

- consultas: lê só views do schema gold, como bed_readonly, em transação READ ONLY;
- calculos: funções puras sobre DataFrames (rankings, variações, resumos);
- graficos: gráficos matplotlib com título que afirma o achado, unidade nos eixos, fonte e
  paleta fixa. Nenhuma conversão de unidade (regra 11): os valores ficam como vêm da GOLD
  (R$, habitantes, %); só os rótulos dos eixos são formatados.
"""
