"""Funções de desenho compartilhadas pelos scripts e pela interface.

Usam a classe Figure do matplotlib diretamente (sem pyplot), então funcionam
tanto para salvar arquivos quanto dentro da janela PyQt.
"""
from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from src.config import MV_MAX, MV_MIN

# Paleta categórica em ordem fixa: a mesma série recebe sempre a mesma cor.
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
COR_DADOS = "#9a9a95"
COR_REFERENCIA = "#3a3a38"
COR_GRADE = "#e3e2dc"
COR_TEXTO = "#52514e"
# Cada método de identificação tem sempre a mesma cor, em qualquer gráfico.
COR_POR_METODO = {"Smith": CORES[0], "Sundaresan": CORES[1], "Ajuste fino": CORES[2]}


def estilizar(ax, xlabel: str = "", ylabel: str = "", titulo: str = ""):
    """Grade e eixos discretos, para os dados ficarem em primeiro plano."""
    ax.grid(True, color=COR_GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(COR_GRADE)
    ax.tick_params(colors=COR_TEXTO, labelsize=9)
    ax.set_xlabel(xlabel, color=COR_TEXTO, fontsize=10)
    ax.set_ylabel(ylabel, color=COR_TEXTO, fontsize=10)
    if titulo:
        ax.set_title(titulo, fontsize=11, loc="left", color="#0b0b0b")


def legenda(ax, **opcoes):
    opcoes.setdefault("fontsize", 9)
    opcoes.setdefault("frameon", False)
    return ax.legend(**opcoes)


def rotulo_saida(unidade: str, grandeza: str = "Saída") -> str:
    return f"{grandeza} ({unidade})" if unidade else grandeza


# --------------------------------------------------------------------------- #
# Identificação
# --------------------------------------------------------------------------- #
def desenhar_identificacao(ax, ds, resultados, titulo: str = "", grandeza: str = "Saída"):
    """Dados do ensaio e a resposta de um ou mais modelos identificados."""
    ax.plot(ds.t, ds.y, ".", markersize=3, color=COR_DADOS, label="Dados do ensaio")
    for reserva, r in zip(CORES[3:], resultados):
        cor = COR_POR_METODO.get(r.metodo, reserva)
        ax.plot(ds.t, r.y_modelo, color=cor, linewidth=2,
                label=f"{r.metodo} (EQM = {r.eqm:.4f})")
    ax.axvline(ds.t0, color=COR_REFERENCIA, linewidth=1, linestyle=":")
    ax.annotate("degrau", (ds.t0, ds.yf), xytext=(4, 0), textcoords="offset points",
                fontsize=8, color=COR_TEXTO, va="top")
    estilizar(ax, "Tempo (s)", rotulo_saida(ds.unidade, grandeza), titulo)
    legenda(ax, loc="lower right")


def figura_identificacao(ds, resultados, titulo: str, grandeza: str = "Saída") -> Figure:
    fig = Figure(figsize=(9, 5), layout="constrained")
    desenhar_identificacao(fig.add_subplot(), ds, resultados, titulo, grandeza)
    return fig


# --------------------------------------------------------------------------- #
# Malha aberta x malha fechada (sem controlador)
# --------------------------------------------------------------------------- #
def figura_malhas(curvas: dict, titulo: str) -> Figure:
    """`curvas` = {nome: (t, y)} para um degrau unitário na referência."""
    fig = Figure(figsize=(9, 5), layout="constrained")
    ax = fig.add_subplot()
    estilos = ["-", "--"]
    for i, (nome, (t, y)) in enumerate(curvas.items()):
        ax.plot(t, y, color=CORES[i], linewidth=2, linestyle=estilos[i % 2], label=nome)
    estilizar(ax, "Tempo (s)", "Saída para degrau unitário na referência", titulo)
    legenda(ax, loc="lower right")
    return fig


# --------------------------------------------------------------------------- #
# Malha fechada com PID
# --------------------------------------------------------------------------- #
def desenhar_controle(ax_pv, ax_mv, resposta, titulo: str = "", unidade: str = "",
                      marcar=(), cor: str = CORES[0], grandeza: str = "Saída"):
    """Resposta do controle: PV em cima, MV embaixo. `marcar` aceita 'tr', 'ts' e 'mp'."""
    q = resposta.metricas
    ax_pv.plot(resposta.t, resposta.pv, color=cor, linewidth=2, label="PV")
    ax_pv.axhline(resposta.sp, color=COR_REFERENCIA, linewidth=1, linestyle="--", label="SetPoint")
    estilizar(ax_pv, "" if ax_mv is not None else "Tempo (s)", rotulo_saida(unidade, grandeza), titulo)
    legenda(ax_pv, loc="lower right")

    sufixo = f" {unidade}" if unidade else ""
    caixa = dict(boxstyle="round,pad=0.3", facecolor="#fff8d6", edgecolor=COR_GRADE)
    seta = dict(arrowstyle="-", color=COR_TEXTO, linewidth=0.8)

    def ponto(x, y):
        ax_pv.plot([x], [y], "o", markersize=7, color="#e34948", markeredgecolor="white", zorder=5)

    def anotar(x, y, texto, altura):
        """Marca o ponto e escreve o rótulo na área livre do gráfico, ligado por uma linha."""
        ponto(x, y)
        ax_pv.annotate(texto, (x, y), xytext=(0.42, altura), textcoords="axes fraction",
                       fontsize=8, bbox=caixa, arrowprops=seta, va="center", zorder=6)

    if "mp" in marcar and np.isfinite(q.mp):
        anotar(q.t_pico, q.pico, f"Pico: {q.pico:.4g}{sufixo}  |  Overshoot: {q.mp:.2f} %", 0.72)
    if "tr" in marcar and np.isfinite(q.tr):
        ponto(q.t10, float(np.interp(q.t10, resposta.t, resposta.pv)))
        anotar(q.t90, float(np.interp(q.t90, resposta.t, resposta.pv)),
               f"Subida (10–90 %): {q.tr:.2f} s", 0.40)
    if "ts" in marcar and np.isfinite(q.ts):
        anotar(q.ts, float(np.interp(q.ts, resposta.t, resposta.pv)),
               f"Acomodação (2 %): {q.ts:.2f} s", 0.56)

    if ax_mv is not None:
        ax_mv.plot(resposta.t, resposta.mv, color=cor, linewidth=1.5, label="MV")
        for limite in (MV_MIN, MV_MAX):
            ax_mv.axhline(limite, color=COR_REFERENCIA, linewidth=1, linestyle=":")
        # O pico inicial da derivada pode ser enorme; o eixo fica limitado à
        # vizinhança da faixa do atuador para a curva continuar legível.
        folga = 0.25 * (MV_MAX - MV_MIN)
        ax_mv.set_ylim(MV_MIN - folga, MV_MAX + folga)
        estilizar(ax_mv, "Tempo (s)", "MV – motor (%)")
        ax_mv.annotate("limites do atuador", (resposta.t[-1], MV_MAX), xytext=(0, 3),
                       textcoords="offset points", ha="right", fontsize=8, color=COR_TEXTO)


def figura_controle(resposta, titulo: str, unidade: str = "", marcar=("tr", "ts", "mp"),
                    grandeza: str = "Saída") -> Figure:
    fig = Figure(figsize=(9, 6.5), layout="constrained")
    ax_pv, ax_mv = fig.subplots(2, 1, sharex=True, height_ratios=[3, 1.2])
    desenhar_controle(ax_pv, ax_mv, resposta, titulo, unidade, marcar, grandeza=grandeza)
    return fig


def figura_comparacao(respostas: dict, titulo: str, unidade: str = "", t_max: float | None = None,
                      grandeza: str = "Saída") -> Figure:
    """Várias sintonias no mesmo gráfico. `respostas` = {nome: RespostaControle}."""
    fig = Figure(figsize=(9, 5), layout="constrained")
    ax = fig.add_subplot()
    primeira = next(iter(respostas.values()))
    for cor, (nome, r) in zip(CORES, respostas.items()):
        ax.plot(r.t, r.pv, color=cor, linewidth=2,
                label=f"{nome} (Mp = {r.metricas.mp:.1f} %, ts = {r.metricas.ts:.1f} s)")
    ax.axhline(primeira.sp, color=COR_REFERENCIA, linewidth=1, linestyle="--", label="SetPoint")
    if t_max is not None:
        ax.set_xlim(0, t_max)
    estilizar(ax, "Tempo (s)", rotulo_saida(unidade, grandeza), titulo)
    legenda(ax, loc="lower right")
    return fig


def figura_validacao_pade(linhas) -> Figure:
    """Compara Padé e atraso exato. `linhas` vem de scripts/validar_pade.py."""
    fig = Figure(figsize=(4.4 * len(linhas), 4.5), layout="constrained")
    eixos = fig.subplots(1, len(linhas), sharey=True, squeeze=False)[0]
    for ax, (nome, pade, exato, t, y) in zip(eixos, linhas):
        ax.plot(pade.t, pade.pv, color=CORES[0], linewidth=2,
                label=f"Padé (Mp = {pade.metricas.mp:.2f} %)")
        ax.plot(t, y, color=CORES[1], linewidth=2, linestyle="--",
                label=f"Atraso exato (Mp = {exato.mp:.2f} %)")
        ax.axhline(1.0, color=COR_REFERENCIA, linewidth=1, linestyle=":")
        ax.set_xlim(0, 30)
        estilizar(ax, "Tempo (s)", "PV normalizada" if ax is eixos[0] else "", nome)
        legenda(ax, loc="lower right")
    return fig
