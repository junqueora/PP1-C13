"""Métricas da resposta ao degrau: tempo de subida, acomodação e overshoot."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.config import BANDA_ACOMODACAO


@dataclass(frozen=True)
class Metricas:
    tr: float            # tempo de subida, de 10 % a 90 % da variação
    t10: float           # instante do cruzamento de 10 %
    t90: float           # instante do cruzamento de 90 %
    ts: float            # tempo de acomodação (critério dos 2 %)
    mp: float            # overshoot, em % da variação
    pico: float          # maior valor atingido pela saída
    t_pico: float
    valor_final: float
    erro_regime: float   # referência - valor final


def calcular(t, y, y_inicial: float, referencia: float, valor_final: float | None = None,
             banda: float = BANDA_ACOMODACAO) -> Metricas:
    """Calcula as métricas de uma resposta ao degrau.

    `valor_final` é o valor de regime; se não for dado, usa a última amostra.
    Tudo é medido sobre a variação (valor_final - y_inicial), então a função
    serve para degraus de subida ou de descida.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if valor_final is None:
        valor_final = float(y[-1])
    variacao = valor_final - y_inicial
    nan = float("nan")
    if variacao == 0:
        return Metricas(nan, nan, nan, nan, nan, float(y.max()), nan, valor_final,
                        referencia - valor_final)

    z = (y - y_inicial) / variacao   # resposta normalizada: 0 no início, 1 no regime

    # Tempo de subida. O 10 % é o último cruzamento antes do 90 %, para ignorar a
    # oscilação inicial que a aproximação de Padé cria durante o tempo morto.
    acima90 = np.nonzero(z >= 0.9)[0]
    if acima90.size:
        i90 = int(acima90[0])
        abaixo10 = np.nonzero(z[:i90] < 0.1)[0]
        i10 = int(abaixo10[-1]) + 1 if abaixo10.size else 0
        t10, t90 = float(t[i10]), float(t[i90])
        tr = t90 - t10
    else:
        t10 = t90 = tr = nan

    # Tempo de acomodação: último instante fora da banda de ±2 %.
    fora = np.nonzero(np.abs(z - 1.0) > banda)[0]
    if fora.size == 0:
        ts = float(t[0])
    elif fora[-1] == len(t) - 1:
        ts = nan   # não acomodou dentro da janela simulada
    else:
        ts = float(t[fora[-1] + 1])

    i_pico = int(np.argmax(z))
    mp = max(0.0, (float(z[i_pico]) - 1.0) * 100.0)
    return Metricas(tr, t10, t90, ts, mp, float(y[i_pico]), float(t[i_pico]),
                    valor_final, referencia - valor_final)
