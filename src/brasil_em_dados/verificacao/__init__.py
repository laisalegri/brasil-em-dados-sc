"""Agente de verificação do pipeline (D29).

Um executor determinístico roda os passos (pytest e, só com flags explícitas, coleta, carga e
GOLD) e guarda as saídas; o agente do Claude Agent SDK recebe só ferramentas próprias de leitura
e escreve a análise que vai para reports/verificacao_<carimbo>.md.

Uso: python -m brasil_em_dados.verificacao [--coleta] [--carga] [--gold]
"""
