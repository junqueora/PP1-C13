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
    """Resposta do controle: PV em cima, MV embaixo. `marcar` aceita 'tr', 'ts' e 'mp'.

    Devolve a lista de rótulos dos pontos marcados, como (anotação, [(x, y), ...]),
    para a interface poder mostrá-los só quando o mouse passa sobre o ponto.
    """
    q = resposta.metricas
    destaques = []
    ax_pv.plot(resposta.t, resposta.pv, color=cor, linewidth=2, label="PV")
    ax_pv.axhline(resposta.sp, color=COR_REFERENCIA, linewidth=1, linestyle="--", label="SetPoint")
    estilizar(ax_pv, "" if ax_mv is not None else "Tempo (s)", rotulo_saida(unidade, grandeza), titulo)
    # À direita, a meia altura: depois do transitório a curva fica colada no SetPoint
    # (em cima ou embaixo), então essa região fica livre nos dois sentidos de degrau.
    legenda(ax_pv, loc="center right")

    sufixo = f" {unidade}" if unidade else ""
    # Num degrau de subida a curva continua para cima depois de cada ponto, então
    # o lado de baixo fica livre; num degrau de descida é o contrário.
    sentido = 1.0 if resposta.sp >= resposta.y_inicial else -1.0
    t_meio = 0.5 * (resposta.t[0] + resposta.t[-1])

    def ponto(x, y):
        ax_pv.plot([x], [y], "o", markersize=6, color=cor, markeredgecolor="white",
                   markeredgewidth=1.2, zorder=5)

    def rotulo(x, y, texto, dy, pontos):
        """Rótulo ligado ao ponto, deslocado `dy` pontos (positivo = acima da curva).

        `pontos` são os pontos do gráfico que acionam o rótulo no hover.
        """
        direita = x <= t_meio                  # na metade direita o texto vai para a esquerda
        anotacao = ax_pv.annotate(texto, (x, y), xytext=(18 if direita else -18, sentido * dy),
                       textcoords="offset points", ha="left" if direita else "right",
                       va="center", fontsize=8, color=COR_TEXTO, zorder=6,
                       bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                                 edgecolor=COR_GRADE, alpha=0.96),
                       arrowprops=dict(arrowstyle="-", color=COR_TEXTO, linewidth=0.7,
                                       shrinkA=0, shrinkB=4))
        destaques.append((anotacao, pontos))

    # A ondulação durante o tempo morto vem da aproximação de Padé; a simulação com
    # o motor limitado usa o atraso exato e não tem esse efeito.
    if not resposta.limitada and np.isfinite(q.t10):
        ax_pv.annotate("ondulação inicial: efeito da aproximação de Padé,\nnão existe na planta real",
                       (q.t10, resposta.y_inicial), xytext=(12, 0), textcoords="offset points",
                       ha="left", va="bottom" if sentido > 0 else "top", fontsize=7.5,
                       fontstyle="italic", color=COR_TEXTO)

    if "tr" in marcar and np.isfinite(q.tr):
        y10 = float(np.interp(q.t10, resposta.t, resposta.pv))
        y90 = float(np.interp(q.t90, resposta.t, resposta.pv))
        ponto(q.t10, y10)
        ponto(q.t90, y90)
        rotulo(q.t90, y90, f"Subida: {q.tr:.2f} s", -30, [(q.t10, y10), (q.t90, y90)])
    if "ts" in marcar and np.isfinite(q.ts):
        y_ts = float(np.interp(q.ts, resposta.t, resposta.pv))
        ponto(q.ts, y_ts)
        rotulo(q.ts, y_ts, f"Acomodação: {q.ts:.2f} s", -62, [(q.ts, y_ts)])
    if "mp" in marcar and np.isfinite(q.mp):
        ponto(q.t_pico, q.pico)
        rotulo(q.t_pico, q.pico, f"Pico: {q.pico:.4g}{sufixo} / Overshoot: {q.mp:.2f} %", 22,
               [(q.t_pico, q.pico)])
        # Folga no lado do pico para o rótulo não sair do gráfico nem cobrir o título.
        baixo, alto = ax_pv.get_ylim()
        folga = 0.25 * abs(resposta.sp - resposta.y_inicial)
        if sentido > 0:
            ax_pv.set_ylim(baixo, max(alto, q.pico + folga))
        else:
            ax_pv.set_ylim(min(baixo, q.pico - folga), alto)

    if ax_mv is not None:
        ax_mv.plot(resposta.t, resposta.mv, color=cor, linewidth=1.5, label="MV")
        for limite in (MV_MIN, MV_MAX):
            ax_mv.axhline(limite, color=COR_REFERENCIA, linewidth=1, linestyle=":")
        # O pico inicial da derivada pode ser enorme; o eixo fica limitado à
        # vizinhança da faixa do atuador para a curva continuar legível.
        folga = 0.25 * (MV_MAX - MV_MIN)
        ax_mv.set_ylim(MV_MIN - folga, MV_MAX + folga)
        estilizar(ax_mv, "Tempo (s)", "MV (%)")
        ax_mv.annotate("limites do atuador", (resposta.t[-1], MV_MAX), xytext=(0, 3),
                       textcoords="offset points", ha="right", fontsize=8, color=COR_TEXTO)
    return destaques


def figura_controle(resposta, titulo: str, unidade: str = "", marcar=("tr", "ts", "mp"),
                    grandeza: str = "Saída") -> Figure:
    fig = Figure(figsize=(9, 6.5), layout="constrained")
    ax_pv, ax_mv = fig.subplots(2, 1, sharex=True, height_ratios=[3, 1.2])
    desenhar_controle(ax_pv, ax_mv, resposta, titulo, unidade, marcar, grandeza=grandeza)
    return fig


def desenhar_comparacao(ax, respostas: dict, titulo: str = "", unidade: str = "",
                        t_max: float | None = None, grandeza: str = "Saída", ax_mv=None):
    """Várias sintonias no mesmo eixo. `respostas` = {nome: RespostaControle}.

    Com `ax_mv`, desenha também o sinal de controle de cada sintonia.
    """
    primeira = next(iter(respostas.values()))
    for cor, (nome, r) in zip(CORES, respostas.items()):
        ax.plot(r.t, r.pv, color=cor, linewidth=2,
                label=f"{nome} (Mp = {r.metricas.mp:.1f} %, ts = {r.metricas.ts:.1f} s)")
        if ax_mv is not None:
            ax_mv.plot(r.t, r.mv, color=cor, linewidth=1.5)
    ax.axhline(primeira.sp, color=COR_REFERENCIA, linewidth=1, linestyle="--", label="SetPoint")
    if t_max is not None:
        ax.set_xlim(0, t_max)
    estilizar(ax, "Tempo (s)" if ax_mv is None else "", rotulo_saida(unidade, grandeza), titulo)
    legenda(ax, loc="lower right")
    if ax_mv is not None:
        for limite in (MV_MIN, MV_MAX):
            ax_mv.axhline(limite, color=COR_REFERENCIA, linewidth=1, linestyle=":")
        folga = 0.25 * (MV_MAX - MV_MIN)
        ax_mv.set_ylim(MV_MIN - folga, MV_MAX + folga)
        estilizar(ax_mv, "Tempo (s)", "MV (%)")


def figura_comparacao(respostas: dict, titulo: str, unidade: str = "", t_max: float | None = None,
                      grandeza: str = "Saída") -> Figure:
    """Várias sintonias no mesmo gráfico. `respostas` = {nome: RespostaControle}."""
    fig = Figure(figsize=(9, 5), layout="constrained")
    desenhar_comparacao(fig.add_subplot(), respostas, titulo, unidade, t_max, grandeza)
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
