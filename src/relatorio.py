"""Relatório em PDF: identificação, sintonia atual e comparação, em páginas A4.

Usa só o matplotlib (PdfPages) e as mesmas funções de desenho da interface, então
o PDF mostra exatamente os gráficos que aparecem na tela.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from src import graficos, simulacao, sintonia
from src.config import INTEGRANTES, METODOS_GRUPO, SUBTITULO, TITULO
from src.graficos import COR_GRADE, COR_TEXTO

A4 = (8.27, 11.69)             # retrato, em polegadas
MARGEM = 0.07                  # margem lateral, em fração da largura

# Seções que podem ser escolhidas, na ordem das páginas.
SECOES = {
    "identificacao": "Identificação do processo",
    "controle": "Sintonia atual",
    "comparacao": "Comparação dos métodos",
}


@dataclass
class DadosRelatorio:
    """Tudo o que o relatório precisa, tirado do estado atual da interface."""

    ds: object                  # Dataset
    resultados: dict            # {método: Identificacao}, inclui o ajuste fino
    metodo_modelo: str          # método cujo modelo foi usado na sintonia
    modelo: object              # ModeloFOPDT usado na sintonia
    sp: float
    lam: float | None = None    # λ do IMC no campo da interface
    resposta: object = None     # RespostaControle atual (None se não houver sintonia válida)
    pid: object = None
    titulo_controle: str = ""
    limitada: bool = False
    gerado_em: datetime | None = None


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #
def paginas(dados: DadosRelatorio, secoes=tuple(SECOES)) -> list[Figure]:
    """Monta as páginas das seções pedidas. A primeira sempre traz o cabeçalho."""
    construtores = {"identificacao": _pagina_identificacao, "controle": _pagina_controle,
                    "comparacao": _pagina_comparacao}
    escolhidas = [s for s in SECOES if s in secoes]
    if "controle" in escolhidas and dados.resposta is None:
        escolhidas.remove("controle")             # sem sintonia válida não há o que mostrar
    figuras = []
    for secao in escolhidas:
        fig = Figure(figsize=A4)
        topo = _cabecalho(fig, dados) if not figuras else 0.95
        construtores[secao](fig, dados, topo)
        figuras.append(fig)
    for numero, fig in enumerate(figuras, start=1):
        _rodape(fig, numero, len(figuras))
    return figuras


def salvar_pdf(caminho, figuras: list[Figure]):
    with PdfPages(caminho) as pdf:
        for fig in figuras:
            pdf.savefig(fig)
        info = pdf.infodict()
        info["Title"] = TITULO
        info["Subject"] = SUBTITULO


def _pagina_identificacao(fig, dados: DadosRelatorio, topo: float):
    ds = dados.ds
    y = _secao(fig, topo, "1. Planta e ensaio")
    linhas = [
        "Planta: cilindro pneumático (compressor + reservatório).",
        f"Variável controlada: pressão no reservatório ({ds.unidade or '—'}).  "
        "Variável manipulada: comando do motor (0 a 100 %).",
        f"Ensaio: {ds.nome}, {len(ds.t)} amostras, degrau de {ds.u0:g} para {ds.u1:g} % "
        f"em t = {ds.t0:g} s.",
        f"Saída de {ds.y0:.4g} para {ds.yf:.4g} {ds.unidade} (Δy = {ds.dy:.4g}).",
    ]
    y = _paragrafos(fig, y, linhas)

    y = _secao(fig, y - 0.015, "2. Identificação")
    cabecalho = ["Método", "k", "τ (s)", "θ (s)", "θ/τ", "EQM"]
    corpo = [[r.metodo, f"{r.modelo.k:.5g}", f"{r.modelo.tau:.4g}", f"{r.modelo.theta:.4g}",
              f"{r.modelo.incontrolabilidade:.3g}", f"{r.eqm:.4g}"]
             for r in dados.resultados.values()]
    ref = ds.referencia or {}
    if {"k", "tau", "theta"} <= ref.keys():
        corpo.append(["Referência do arquivo", f"{ref['k']:.5g}", f"{ref['tau']:.4g}",
                      f"{ref['theta']:.4g}", f"{ref['theta'] / ref['tau']:.3g}", "—"])
    destaque = [i for i, r in enumerate(dados.resultados.values())
                if r.metodo == dados.metodo_modelo]
    y = _tabela(fig, y, cabecalho, corpo, destaque, primeira_larga=True)
    y = _paragrafos(fig, y, [f"Modelo usado na sintonia ({dados.metodo_modelo}): {dados.modelo}"])

    ax = fig.add_axes(_area(y - 0.02, 0.08))
    graficos.desenhar_identificacao(ax, ds, list(dados.resultados.values()),
                                    "Curva de reação e modelos identificados", ds.grandeza)


def _pagina_controle(fig, dados: DadosRelatorio, topo: float):
    r, pid, q = dados.resposta, dados.pid, dados.resposta.metricas
    unidade = dados.ds.unidade
    y = _secao(fig, topo, "3. Sintonia atual")
    y = _paragrafos(fig, y, [dados.titulo_controle,
                             "Simulação com o motor limitado a 0–100 % (atraso exato e anti-windup)."
                             if r.limitada else
                             "Simulação linear, com o atraso aproximado por Padé."])
    y = _tabela(fig, y, ["Kp", "Ti (s)", "Td (s)", f"SP ({unidade})"],
                [[f"{pid.kp:.4g}", f"{pid.ti:.4g}", f"{pid.td:.4g}", f"{r.sp:.4g}"]])
    y = _tabela(fig, y - 0.01,
                ["tr (s)", "ts (s)", "Mp (%)", f"Pico ({unidade})", f"Erro ({unidade})", "MV máx (%)"],
                [[_num(q.tr, ".2f"), _num(q.ts, ".2f"), _num(q.mp, ".2f"), f"{q.pico:.4g}",
                  f"{round(q.erro_regime, 9) + 0.0:.3g}", f"{r.mv_max:.0f}"]])
    baixo, alto = 0.08, y - 0.02
    ax_pv = fig.add_axes([MARGEM + 0.04, baixo + 0.30 * (alto - baixo), 0.85, 0.70 * (alto - baixo)])
    ax_mv = fig.add_axes([MARGEM + 0.04, baixo, 0.85, 0.24 * (alto - baixo)], sharex=ax_pv)
    graficos.desenhar_controle(ax_pv, ax_mv, r, "Resposta da malha fechada", unidade,
                               ("tr", "ts", "mp"), grandeza=dados.ds.grandeza)
    ax_pv.tick_params(labelbottom=False)


def _pagina_comparacao(fig, dados: DadosRelatorio, topo: float):
    m, ds = dados.modelo, dados.ds
    y = _secao(fig, topo, "4. Comparação dos métodos de sintonia")
    lam = sintonia.lambda_ou_padrao(m, dados.lam)
    y = _paragrafos(fig, y, [
        f"Mesmo degrau de SetPoint ({ds.y0:.4g} → {dados.sp:.4g} {ds.unidade}), modelo "
        f"{dados.metodo_modelo}, λ = {lam:.3g} s no IMC. Métodos do Grupo 3 em destaque.",
        "Critério do grupo: menor índice de overshoot."])

    simular = simulacao.simular_controle_saturado if dados.limitada else simulacao.simular_controle
    corpo, destaque = [], []
    for nome in sintonia.TECNICAS:
        try:
            pid = sintonia.sintonizar(nome, m, lam)
            q = simular(m, pid, dados.sp, ds.y0, ds.u0).metricas
        except ValueError as erro:          # θ = 0 ou malha instável
            corpo.append([nome, "–", "–", "–", "–", "–", str(erro)[:28]])
            continue
        if nome in METODOS_GRUPO:
            destaque.append(len(corpo))
        corpo.append([nome, f"{pid.kp:.4g}", f"{pid.ti:.4g}", f"{pid.td:.4g}",
                      _num(q.tr, ".2f"), _num(q.ts, ".2f"), _num(q.mp, ".2f")])
    y = _tabela(fig, y, ["Método", "Kp", "Ti (s)", "Td (s)", "tr (s)", "ts (s)", "Mp (%)"],
                corpo, destaque, primeira_larga=True)

    try:
        respostas = simulacao.comparar_imc_itae(m, lam, dados.sp, ds.y0, ds.u0, dados.limitada)
    except ValueError as erro:
        _paragrafos(fig, y, [f"Não foi possível comparar IMC × ITAE: {erro}"])
        return
    ax = fig.add_axes(_area(y - 0.02, 0.08))
    titulo = "IMC × ITAE" + ("  ·  motor limitado" if dados.limitada else "")
    # Mostra até 1,5× a maior acomodação, para o transitório não ficar espremido.
    acomodacoes = [r.metricas.ts for r in respostas.values() if np.isfinite(r.metricas.ts)]
    t_max = 1.5 * max(acomodacoes) if acomodacoes else None
    graficos.desenhar_comparacao(ax, respostas, titulo, ds.unidade, t_max, ds.grandeza)


# --------------------------------------------------------------------------- #
# Elementos da página (posições em fração da altura, de cima para baixo)
# --------------------------------------------------------------------------- #
def _cabecalho(fig, dados: DadosRelatorio) -> float:
    gerado = dados.gerado_em or datetime.now()
    fig.text(MARGEM, 0.955, TITULO, fontsize=16, weight="bold", color="#1c2430")
    fig.text(MARGEM, 0.935, SUBTITULO, fontsize=11, color="#3d4c5c")
    fig.text(1 - MARGEM, 0.935, f"Gerado em {gerado:%d/%m/%Y %H:%M}", fontsize=8,
             color=COR_TEXTO, ha="right")
    fig.text(MARGEM, 0.915, "Grupo 3  ·  " + "  ·  ".join(INTEGRANTES), fontsize=8, color=COR_TEXTO)
    fig.add_artist(_linha(0.905))
    return 0.885


def _rodape(fig, numero: int, total: int):
    fig.add_artist(_linha(0.04))
    fig.text(MARGEM, 0.025, "PP1-C13  ·  Grupo 3", fontsize=7.5, color=COR_TEXTO)
    fig.text(1 - MARGEM, 0.025, f"Página {numero} de {total}", fontsize=7.5,
             color=COR_TEXTO, ha="right")


def _secao(fig, y: float, texto: str) -> float:
    fig.text(MARGEM, y, texto, fontsize=12, weight="bold", color="#1c2430", va="top")
    return y - 0.03


def _paragrafos(fig, y: float, linhas) -> float:
    for linha in linhas:
        fig.text(MARGEM, y, linha, fontsize=9, color="#1c2430", va="top", wrap=True)
        y -= 0.02
    return y - 0.005


def _tabela(fig, y: float, cabecalho, corpo, destaque=(), primeira_larga: bool = False) -> float:
    """Tabela com linhas de 0,022 de altura. Linhas em `destaque` ficam em negrito.

    Com `primeira_larga`, a primeira coluna (nomes de métodos) ocupa o dobro das outras.
    """
    altura = 0.022 * (len(corpo) + 1)
    ax = fig.add_axes([MARGEM, y - altura, 1 - 2 * MARGEM, altura])
    ax.axis("off")
    pesos = [2.0 if primeira_larga and i == 0 else 1.0 for i in range(len(cabecalho))]
    tabela = ax.table(cellText=corpo, colLabels=cabecalho, loc="upper center",
                      cellLoc="center", bbox=[0, 0, 1, 1],
                      colWidths=[p / sum(pesos) for p in pesos])
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(8.5)
    for (linha, _), celula in tabela.get_celld().items():
        celula.set_edgecolor(COR_GRADE)
        if linha == 0:
            celula.set_facecolor("#eef2f6")
            celula.set_text_props(weight="bold", color="#1c2430")
        elif linha - 1 in destaque:
            celula.set_facecolor("#e8f1ff")
            celula.set_text_props(weight="bold")
    return y - altura - 0.015


def _area(topo: float, base: float) -> list[float]:
    """Retângulo de um gráfico entre `topo` e `base`, com espaço para os rótulos dos eixos."""
    return [MARGEM + 0.04, base, 1 - 2 * MARGEM - 0.04, topo - base - 0.03]


def _linha(y: float):
    return Line2D([MARGEM, 1 - MARGEM], [y, y], color=COR_GRADE, linewidth=0.8)


def _num(valor: float, formato: str) -> str:
    return format(valor, formato) if np.isfinite(valor) else "–"
