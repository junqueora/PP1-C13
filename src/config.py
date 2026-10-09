"""Constantes e caminhos usados em todo o projeto."""
from __future__ import annotations

from pathlib import Path

# Caminhos sempre relativos à raiz do projeto, para funcionar de qualquer pasta.
RAIZ = Path(__file__).resolve().parents[1]
PASTA_DADOS = RAIZ / "data"
DATASET_PADRAO = PASTA_DADOS / "Pneumatico_G3.mat"
PASTA_FIGURAS = RAIZ / "resultados" / "figuras"

# Identificação
JANELA_SUAVIZACAO = 9      # amostras da média móvel usada para achar os cruzamentos
FRACAO_REGIME = 0.10       # fração final das amostras usada para estimar o valor final

# Simulação
ORDEM_PADE = 10            # ordem da aproximação de Padé do atraso (igual ao código base da disciplina)
N_FILTRO_DERIVADA = 10     # filtro da ação derivativa: Td*s / (Td/N*s + 1)
BANDA_ACOMODACAO = 0.02    # critério dos 2 %

# Sintonia IMC: valor inicial de lambda como múltiplo do atraso (lambda = 1,2*theta)
RAZAO_LAMBDA_PADRAO = 1.2

# Faixa física do atuador (motor do compressor), em %
MV_MIN, MV_MAX = 0.0, 100.0

# Métodos de sintonia definidos para o Grupo 3 (Tabela 7 do enunciado)
METODOS_GRUPO = ("IMC", "ITAE")
