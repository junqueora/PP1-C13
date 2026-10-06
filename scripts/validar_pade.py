"""Valida a aproximação de Padé comparando com uma simulação de atraso exato.

A biblioteca control não representa o atraso de transporte, então o projeto usa
Padé. Este script simula a mesma malha no tempo, passo a passo, guardando o sinal
de controle em um buffer para aplicar o atraso exato, e compara as métricas.

Execute a partir da raiz do projeto:  python scripts/validar_pade.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from src import dataset, graficos, identificacao, metricas, simulacao, sintonia  # noqa: E402
from src.config import DATASET_PADRAO, N_FILTRO_DERIVADA, PASTA_FIGURAS  # noqa: E402
from src.modelo import ModeloFOPDT  # noqa: E402
from src.sintonia import PID  # noqa: E402


def simular_atraso_exato(m: ModeloFOPDT, pid: PID, t_final: float, dt: float = 1e-3,
                         n: float = N_FILTRO_DERIVADA):
    """Malha fechada com PID para degrau unitário de SetPoint, com atraso exato."""
    passos = int(round(t_final / dt))
    atraso = int(round(m.theta / dt))          # atraso em número de amostras
    decaimento = np.exp(-dt / m.tau)           # discretização exata da primeira ordem
    tf = pid.td / n if pid.td > 0 else 0.0     # constante do filtro da derivada
    y = np.zeros(passos)
    u = np.zeros(passos)
    saida = integral = erro_filtrado = 0.0
    for i in range(passos):
        y[i] = saida
        erro = 1.0 - saida
        integral += erro * dt / pid.ti
        derivada = 0.0
        if pid.td > 0:
            derivada = pid.td / tf * (erro - erro_filtrado)
            erro_filtrado += (erro - erro_filtrado) * dt / tf
        u[i] = pid.kp * (erro + integral + derivada)
        u_atrasado = u[i - atraso] if i >= atraso else 0.0
        saida = decaimento * saida + (1.0 - decaimento) * m.k * u_atrasado
    return np.arange(passos) * dt, y


def comparar(m: ModeloFOPDT, casos: dict[str, PID], t_final: float = 80.0):
    """Devolve, para cada caso, as métricas com Padé e com atraso exato."""
    linhas = []
    for nome, pid in casos.items():
        pade = simulacao.simular_controle(m, pid, 1.0, 0.0, t_final=t_final)
        t, y = simular_atraso_exato(m, pid, t_final)
        exato = metricas.calcular(t, y, 0.0, 1.0, 1.0)
        linhas.append((nome, pade, exato, t, y))
    return linhas


def main():
    ds = dataset.carregar(DATASET_PADRAO)
    m = identificacao.melhor(identificacao.identificar(ds)).modelo
    casos = {"ITAE": sintonia.itae(m)}
    for razao in (1.0, 1.2, 1.5):
        casos[f"IMC λ/θ={razao:g}"] = sintonia.imc(m, razao * m.theta)

    print(f"Modelo: {m}")
    print(f"{'Sintonia':<14}{'':>8}{'tr (s)':>9}{'ts (s)':>9}{'Mp (%)':>9}")
    linhas = comparar(m, casos)
    for nome, pade, exato, _, _ in linhas:
        p = pade.metricas
        print(f"{nome:<14}{'Padé':>8}{p.tr:9.2f}{p.ts:9.2f}{p.mp:9.2f}")
        print(f"{'':<14}{'Exato':>8}{exato.tr:9.2f}{exato.ts:9.2f}{exato.mp:9.2f}")

    fig = graficos.figura_validacao_pade(linhas[:3])
    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_FIGURAS / "08_validacao_pade.png"
    fig.savefig(destino, dpi=200)
    print(f"\nFigura salva: resultados/figuras/{destino.name}")


if __name__ == "__main__":
    main()
