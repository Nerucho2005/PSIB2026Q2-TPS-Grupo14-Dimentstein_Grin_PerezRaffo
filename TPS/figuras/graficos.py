# graficos.py
# Figuras finales del informe (nervio mediano, CP4-Fz, 30-400 Hz), con estilo uniforme.
# Tres partes:
#   1. Estilo común: colores fijos por método y por referencia, tipografía para A4,
#      coma decimal en los ejes, guardado en PNG (300 dpi) y PDF en informe/figuras/.
#   2. Una función por figura (fig_*): reciben datos YA calculados y devuelven la
#      figura. No leen archivos ni calculan nada del pipeline.
#   3. Orquestador (generar_todas): carga el registro con las funciones del pipeline
#      (TPS/main) y de los scripts de verificación (TPS/pruebas), calcula todo una sola
#      vez y llama a las fig_*. Usa el sujeto de config.py (sub-001 en el informe).
#
# Figuras, ordenadas según el informe:
#   Decisiones de diseño:  01 PSD crudo vs. filtrado | 02 artefacto e interpolación |
#                          03 comparación de bandas de filtrado | 04 comparación de
#                          referencias | 05 lateralidad (elección de CP4)
#   Resultados (objetivo): 06 PEP según el método de promediado | 07 SNR vs. N (SNR
#                          principal y SNR del paper) | 08 diferencias entre métodos
#                          (IC 95 %) | 09 varianza del ruido y pesos por época
#   Control de calidad:    10 reproducibilidad (primera vs. segunda mitad)
#
# Ejecutar desde la raíz del repo:   python TPS/figuras/graficos.py
# (tarda varios minutos; con --sin-promedio se omite la referencia promedio, la más lenta)
import sys
from pathlib import Path

_TPS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_TPS / "main"), str(_TPS / "pruebas")]   # pipeline y scripts de pruebas

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from scipy.signal import welch

import config as cfg

# --------------------------------------------------------------------------
# 1. Estilo
# --------------------------------------------------------------------------
METODOS = ("homogeneo", "n", "s", "sn")
COLOR_METODO = {"homogeneo": "#1f77b4", "n": "#ff7f0e", "s": "#2ca02c", "sn": "#d62728"}
NOMBRE_METODO = {"homogeneo": "Homogéneo", "n": "Inhomogéneo (n)", "s": "Inhomogéneo (s)",
                 "sn": "Inhomogéneo (sn)"}
COLOR_REF = {"RM": "#1f77b4", "Fz": "#ff7f0e", "LMRM": "#d62728", "PROM": "#9467bd"}
NOMBRE_REF = {"RM": "Mastoides der. (RM)", "Fz": "Fz", "LMRM": "Mastoides enlazadas",
              "PROM": "Promedio"}
COLOR_BANDA = {"IFCN": "0.55", "Anterior": "#1f77b4", "Paper": "#d62728"}
ANCHO_A4 = 6.3   # pulgadas, ancho útil de una página A4 con márgenes de 2,5 cm


def estilo():
    plt.rcParams.update({
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 7.5,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.grid": True, "grid.alpha": 0.3,
        "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.2,
        "figure.dpi": 110, "savefig.bbox": "tight"})


def coma(x, _=None):
    """Formato con coma decimal y sin ceros sobrantes."""
    return f"{x:.6g}".replace(".", ",")


def fmt(x, d=1):
    """Número con d decimales y coma decimal (sin '-0')."""
    if not np.isfinite(x):
        return "—"
    x = 0.0 if abs(round(float(x), d)) == 0 else float(x)
    return f"{x:.{d}f}".replace(".", ",")


def _ejes_coma(ax, x=True, y=True):
    if x:
        ax.xaxis.set_major_formatter(FuncFormatter(coma))
    if y:
        ax.yaxis.set_major_formatter(FuncFormatter(coma))


def _marcar_estimulo(ax, ventana=None):
    ax.axvline(0, color="k", lw=0.6)
    if ventana is not None:
        ax.axvspan(*(np.asarray(ventana) * 1e3), color="0.92", zorder=0, lw=0)


def _leyenda_figura(fig, axs, ncol=3, alto=0.1):
    """Una sola leyenda debajo de la figura, con las entradas (sin repetir) de axs."""
    handles, labels = [], []
    for ax in np.ravel(axs):
        for h, l in zip(*ax.get_legend_handles_labels()):
            if l not in labels and not l.startswith("_"):
                handles.append(h)
                labels.append(l)
    fig.legend(handles, labels, loc="lower center", ncol=ncol, frameon=False,
               fontsize=7.5, bbox_to_anchor=(0.5, 0))
    fig.tight_layout(rect=(0, alto, 1, 1))


def _ticks_n(ax, n_valores):
    """Eje x logarítmico con los N usados como rótulos (sin encimarse)."""
    ax.set_xscale("log")
    ticks = []
    for n in n_valores:
        if not ticks or n / ticks[-1] >= 1.4:
            ticks.append(n)
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda x, _: ""))


def guardar(fig, nombre, carpeta=None):
    carpeta = carpeta or cfg.DIR_FIGURAS
    carpeta.mkdir(parents=True, exist_ok=True)
    for ext, dpi in (("png", 300), ("pdf", None)):
        fig.savefig(carpeta / f"{nombre}.{ext}", dpi=dpi)
    print(f"  guardada {nombre}.png / .pdf")


# --------------------------------------------------------------------------
# 2. Figuras
# --------------------------------------------------------------------------
def fig_psd(d):
    """01. PSD (Welch) del EEG crudo (interpolado) y filtrado. d = dict(f, psd_crudo,
    psd_filtrado) en V²/Hz."""
    fig, ax = plt.subplots(figsize=(ANCHO_A4, 2.9))
    m = (d["f"] >= 1) & (d["f"] <= 1000)
    ax.semilogy(d["f"], d["psd_crudo"] * 1e12, color="0.55", lw=0.7, label="Crudo (interpolado)")
    ax.semilogy(d["f"], d["psd_filtrado"] * 1e12, color="#1f77b4", lw=0.9, label="Filtrado")
    ax.axvspan(cfg.F_BAJO, cfg.F_ALTO, color="#1f77b4", alpha=0.07, lw=0,
               label=f"Banda de paso {fmt(cfg.F_BAJO, 0)}–{fmt(cfg.F_ALTO, 0)} Hz")
    if cfg.F_NOTCH:
        ax.axvline(cfg.F_NOTCH, color="#d62728", lw=0.7, ls=":",
                   label=f"Notch {cfg.F_NOTCH:g} Hz (red)")
    p = d["psd_crudo"][m] * 1e12
    ax.set(xlim=(0, 1000), ylim=(p.min() / 1e3, p.max() * 3), xlabel="Frecuencia (Hz)",
           ylabel="PSD (µV²/Hz)", title=f"Espectro de {cfg.CANAL}–{cfg.REFERENCIA}")
    _ejes_coma(ax, y=False)
    _leyenda_figura(fig, ax, ncol=4, alto=0.1)
    return fig


def fig_artefacto(d):
    """02. Artefacto de estímulo. d = dict(t, epocas_zoom (k, N), prom_crudo,
    prom_filtrado, prom_interpolado) en V."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(ANCHO_A4, 2.8))
    t_ms = d["t"] * 1e3
    z = (t_ms >= -5) & (t_ms <= 15)
    a1.plot(t_ms[z], d["epocas_zoom"][:, z].T * 1e6, color="0.82", lw=0.4)
    a1.plot([], [], color="0.82", lw=0.8, label="Épocas individuales (sin filtrar)")
    a1.plot(t_ms[z], d["prom_crudo"][z] * 1e6, "k", lw=1.2, label="Promedio sin filtrar")
    a1.axvspan(*(np.asarray(cfg.T_ARTEFACTO) * 1e3), color="#ff7f0e", alpha=0.2, lw=0,
               label=f"Ventana interpolada ({fmt(cfg.T_ARTEFACTO[0] * 1e3, 0)} a "
                     f"{fmt(cfg.T_ARTEFACTO[1] * 1e3, 0)} ms)")
    a1.axvline(0, color="k", lw=0.6)
    a1.set(xlabel="Tiempo (ms)", ylabel="µV", title=f"{cfg.CANAL}: sin filtrar")
    a2.plot(t_ms, d["prom_crudo"] * 1e6, color="0.6", lw=0.8)
    a2.plot(t_ms, d["prom_filtrado"] * 1e6, color="#1f77b4", label="Filtrado sin interpolar")
    a2.plot(t_ms, d["prom_interpolado"] * 1e6, color="#ff7f0e", ls="--",
            label="Filtrado con interpolación")
    _marcar_estimulo(a2, cfg.VENTANA_SENAL)
    lim = 1.4 * np.abs(d["prom_interpolado"]).max() * 1e6
    a2.set(ylim=(-lim, lim), xlabel="Tiempo (ms)", ylabel="µV", title="Filtro e interpolación")
    for a in (a1, a2):
        _ejes_coma(a)
    _leyenda_figura(fig, (a1, a2), ncol=2, alto=0.16)
    return fig


def fig_filtros(t, pes, tabla):
    """03. PEP con distintas bandas y su SNR. pes = {banda: pe}; tabla: DataFrame de
    comparar_filtros (columnas banda, banda_Hz, SNR_homog_dB, SNR_n_dB, N20_lat_ms)."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(ANCHO_A4, 2.9),
                                 gridspec_kw=dict(width_ratios=(1.6, 1)))
    for nombre, pe in pes.items():
        f = tabla.set_index("banda").loc[nombre]
        a1.plot(t * 1e3, pe * 1e6, color=COLOR_BANDA.get(nombre, "0.3"),
                label=f"{nombre} ({f['banda_Hz'].replace('-', '–')} Hz)")
    _marcar_estimulo(a1, cfg.VENTANA_SENAL)
    a1.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)", title=f"PEP en {cfg.CANAL}–{cfg.REFERENCIA}")
    _ejes_coma(a1)
    x = np.arange(len(tabla))
    for k, (col, etq, c) in enumerate((("SNR_homog_dB", "Homogéneo", COLOR_METODO["homogeneo"]),
                                       ("SNR_n_dB", "Inhomogéneo (n)", COLOR_METODO["n"]))):
        barras = a2.bar(x + (k - 0.5) * 0.38, tabla[col], 0.38, color=c, label=f"SNR {etq}")
        for b, v in zip(barras, tabla[col]):
            a2.text(b.get_x() + b.get_width() / 2, v, fmt(v), ha="center", va="bottom", fontsize=6)
    a2.set_xticks(x)
    a2.set_xticklabels(tabla["banda"])
    a2.set(ylabel="SNR (dB)", title="SNR con M épocas")
    a2.grid(axis="x", alpha=0)
    _ejes_coma(a2, x=False)
    _leyenda_figura(fig, (a1, a2), ncol=3, alto=0.17)
    return fig


def fig_referencias(t, pes, ruidos, rms, snr):
    """04. PEP y ruido residual con distintas referencias (misma escala). Diccionarios
    {etiqueta_ref: ...}; rms en V y snr en dB del promedio homogéneo."""
    fig, (ax_pe, ax_r) = plt.subplots(2, 1, figsize=(ANCHO_A4, 4.6), sharex=True)
    t_ms = t * 1e3
    for ref in pes:
        c = COLOR_REF.get(ref, "0.3")
        ax_pe.plot(t_ms, pes[ref] * 1e6, color=c, lw=1, label=f"{cfg.CANAL}–{NOMBRE_REF.get(ref, ref)}")
        ax_r.plot(t_ms, ruidos[ref] * 1e6, color=c, lw=0.8,
                  label=f"SNR {fmt(snr[ref])} dB · RMS {fmt(rms[ref] * 1e6, 2)} µV")
    for a in (ax_pe, ax_r):
        _marcar_estimulo(a, cfg.VENTANA_SENAL)
        _ejes_coma(a)
    ax_r.set_ylim(ax_pe.get_ylim())
    ax_pe.set(ylabel="Amplitud (µV)", title="PEP (promedio homogéneo)")
    ax_r.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)", title="Ruido residual (par/impar)")
    ax_r.legend(fontsize=6.5, loc="upper right", framealpha=0.85)
    handles, labels = ax_pe.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return fig


def fig_lateralidad(t, pes, ref, lat_n20=None):
    """05. PEP en CP3 (ipsilateral) y CP4 (contralateral) con una referencia simétrica.
    pes = {canal: pe}; lat_n20 = latencia (ms) del N20 contralateral."""
    fig, ax = plt.subplots(figsize=(ANCHO_A4 * 0.62, 2.7))
    estilos = {"CP4": dict(color="#d62728", label="CP4 (contralateral)"),
               "CP3": dict(color="#1f77b4", ls="--", label="CP3 (ipsilateral)")}
    for canal, pe in pes.items():
        ax.plot(t * 1e3, pe * 1e6, **estilos.get(canal, dict(label=canal)))
    _marcar_estimulo(ax, cfg.VENTANA_SENAL)
    if lat_n20 is not None:
        ax.axvline(lat_n20, color="0.4", lw=0.7, ls=":")
        ax.text(lat_n20 + 1, ax.get_ylim()[1], f"N20 {fmt(lat_n20)} ms", fontsize=7, va="top")
    ax.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
           title=f"Lateralidad — mediano izquierdo\n(ref. {NOMBRE_REF.get(ref, ref).lower()})")
    _ejes_coma(ax)
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    return fig


def fig_pep_metodos(t, pes, rms_ruido, componentes):
    """06. PEP con los cuatro métodos de promediado, banda ±2·RMS del ruido residual del
    homogéneo y componentes válidos del homogéneo rotulados. pes = {metodo: pe} (V)."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(ANCHO_A4, 3.0),
                                 gridspec_kw=dict(width_ratios=(1.5, 1)))
    t_ms = t * 1e3
    for a, zoom in ((a1, False), (a2, True)):
        h = pes["homogeneo"] * 1e6
        a.fill_between(t_ms, h - 2 * rms_ruido * 1e6, h + 2 * rms_ruido * 1e6, color="#1f77b4",
                       alpha=0.15, lw=0, label="±2·RMS del ruido residual (homogéneo)")
        for met in METODOS:
            a.plot(t_ms, pes[met] * 1e6, color=COLOR_METODO[met], lw=1 if met != "homogeneo" else 1.4,
                   ls="-" if met in ("homogeneo", "n") else "--", label=NOMBRE_METODO[met])
        _marcar_estimulo(a, cfg.VENTANA_SENAL)
        _ejes_coma(a)
        a.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)")
    comp = componentes[~componentes["componente"].str.contains("pico a pico")
                       & componentes["valido"].astype(bool)]
    for _, c in comp.iterrows():
        arriba = c["amp_uV"] > 0
        a1.plot(c["lat_ms"], c["amp_uV"], "o", color="k", ms=3)
        a1.annotate(f"{c['componente']}\n{fmt(c['lat_ms'])} ms", (c["lat_ms"], c["amp_uV"]),
                    xytext=(0, 6 if arriba else -6), textcoords="offset points",
                    ha="center", va="bottom" if arriba else "top", fontsize=6.5)
    rango = np.ptp(pes["homogeneo"]) * 1e6
    a1.set(ylim=(pes["homogeneo"].min() * 1e6 - 0.4 * rango, pes["homogeneo"].max() * 1e6 + 0.4 * rango),
           title=f"{cfg.CANAL}–{cfg.REFERENCIA}")
    a2.set(xlim=np.asarray(cfg.VENTANA_SENAL) * 1e3 + (-3, 3), title="Detalle de la ventana del PEP")
    _leyenda_figura(fig, (a1, a2), ncol=3, alto=0.15)
    return fig


def fig_curvas(curvas, pendientes, recta, curva_paper, pendiente_paper, recta_paper):
    """07. (a) SNR principal vs. N para los cuatro métodos; (b) SNR del paper vs. N
    (homogéneo). curvas = {metodo: dict(n, snr_db, se_db)} (arrays 1D);
    pendientes = {metodo: (b, sb)}; recta = (N, snr) +10·log10(N) ajustada al homogéneo."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(ANCHO_A4, 3.2))
    lineas = []
    for k, met in enumerate(METODOS):
        c = curvas[met]
        b, sb = pendientes[met]
        a1.errorbar(c["n"] * (1 + 0.03 * (k - 1.5)), c["snr_db"], yerr=c["se_db"], fmt="o-",
                    ms=3, capsize=2, lw=1, color=COLOR_METODO[met], label=NOMBRE_METODO[met])
        lineas.append(f"{NOMBRE_METODO[met]}: {fmt(b)} ± {fmt(sb)}")
    a1.plot(*recta, "k:", lw=1, label="+10·log₁₀(N) ajustada (teórica)")
    a1.text(0.03, 0.97, "Pendiente (dB/década):\n" + "\n".join(lineas), transform=a1.transAxes,
            va="top", fontsize=6, bbox=dict(boxstyle="round", fc="white", ec="0.8", alpha=0.9))
    a1.set(xlabel="N épocas promediadas", ylabel="SNR (dB)",
           title="SNR principal (par/impar, ventana del PEP)")
    c = curva_paper
    a2.errorbar(c["n"], c["snr_db"], yerr=c["se_db"], fmt="s-", ms=3, capsize=2, lw=1,
                color=COLOR_METODO["homogeneo"])
    a2.plot(*recta_paper, "k:", lw=1)
    a2.text(0.03, 0.97, f"Pendiente: {fmt(pendiente_paper[0])} ± {fmt(pendiente_paper[1])} dB/década",
            transform=a2.transAxes, va="top", fontsize=6,
            bbox=dict(boxstyle="round", fc="white", ec="0.8", alpha=0.9))
    a2.set(xlabel="N épocas promediadas", ylabel="SNR (dB)",
           title="SNR del paper (N20 ±1 ms / pre-estímulo)\npromedio homogéneo")
    for a in (a1, a2):
        _ticks_n(a, curvas["homogeneo"]["n"])
        _ejes_coma(a, x=False)
    _leyenda_figura(fig, (a1, a2), ncol=3, alto=0.15)
    return fig


def fig_forest(tabla):
    """08. Diferencia de SNR de cada inhomogéneo respecto del homogéneo con IC 95 %.
    tabla: DataFrame con columnas metodo, dif_db, ic95_inf, ic95_sup."""
    fig, ax = plt.subplots(figsize=(ANCHO_A4 * 0.8, 0.35 * len(tabla) + 1.3))
    y = np.arange(len(tabla))[::-1].astype(float)
    for yi, (_, f) in zip(y, tabla.iterrows()):
        c = COLOR_METODO[f["metodo"]]
        ax.errorbar(f["dif_db"], yi, xerr=[[f["dif_db"] - f["ic95_inf"]], [f["ic95_sup"] - f["dif_db"]]],
                    fmt="o", color=c, ms=4, capsize=3)
        sig = "*" if (f["ic95_inf"] > 0 or f["ic95_sup"] < 0) else ""
        ax.text(f["ic95_sup"] + 0.12, yi, f"{fmt(f['dif_db'], 2)} dB{sig}", va="center",
                fontsize=7, color=c)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([NOMBRE_METODO[m] for m in tabla["metodo"]], fontsize=7.5)
    ax.set_xlim(right=ax.get_xlim()[1] + 0.8)
    ax.set(xlabel="Diferencia de SNR respecto del homogéneo (dB), IC 95 %",
           title="Ganancia del promedio inhomogéneo (jackknife pareado)")
    _ejes_coma(ax, y=False)
    ax.grid(axis="y", alpha=0)
    ax.plot([], [], " ", label="* IC 95 % que excluye el 0")
    _leyenda_figura(fig, ax, ncol=1, alto=0.1)
    return fig


def fig_pesos(sigma2, pesos):
    """09. Varianza del ruido de cada época y peso relativo (w·M) que le asigna cada
    método inhomogéneo. sigma2 (M,) en V²; pesos = {metodo: (M,)}."""
    M = len(sigma2)
    fig, axs = plt.subplots(2, 1, figsize=(ANCHO_A4, 4.2), sharex=True)
    axs[0].plot(np.arange(M), sigma2 * 1e12, lw=0.6, color="0.3")
    axs[0].set(ylabel="σ² del ruido (µV²)", title=f"Varianza del ruido por época — {cfg.CANAL}–{cfg.REFERENCIA}")
    for met in METODOS[1:]:
        axs[1].plot(np.arange(M), pesos[met] * M, lw=0.6, color=COLOR_METODO[met],
                    label=NOMBRE_METODO[met], alpha=0.9 if met == "n" else 0.7)
    axs[1].axhline(1, color="k", lw=0.7, ls="--", label="Homogéneo (1/M)")
    axs[1].set(xlabel="Número de época (orden temporal)", ylabel="Peso relativo (w·M)",
               title="Peso de cada época en el promedio")
    for a in axs:
        _ejes_coma(a)
    _leyenda_figura(fig, axs, ncol=4, alto=0.07)
    return fig


def fig_reproducibilidad(t, pe1, pe2, fila):
    """10. Subpromedios de la primera y la segunda mitad del registro. fila: Series de
    teoria.reproducibilidad."""
    fig, ax = plt.subplots(figsize=(ANCHO_A4 * 0.7, 2.9))
    t_ms = t * 1e3
    ax.plot(t_ms, pe1 * 1e6, color="#1f77b4", label="Primera mitad del registro")
    ax.plot(t_ms, pe2 * 1e6, color="#d62728", ls="--", label="Segunda mitad del registro")
    _marcar_estimulo(ax, cfg.VENTANA_SENAL)
    ok = "cumple" if (fila["cumple_lat"] and fila["cumple_amp"]) else "no cumple"
    ax.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)")
    ax.set_title(f"{cfg.CANAL}–{cfg.REFERENCIA} — {fila['componente']}: Δlat {fmt(fila['dif_lat_ms'], 2)} ms, "
                 f"Δamp {fmt(100 * fila['dif_amp_rel'], 1)} % ({ok} IFCN)", fontsize=8.5)
    _ejes_coma(ax)
    _leyenda_figura(fig, ax, ncol=2, alto=0.1)
    return fig


# --------------------------------------------------------------------------
# 3. Orquestador: calcula lo necesario con el pipeline y genera las figuras
# --------------------------------------------------------------------------
def calcular(incluir_promedio=True, avance=None):
    """Carga el registro y calcula todo lo que necesitan las figuras.
    avance(fraccion, texto): aviso de progreso por etapa (lo usa la interfaz; puede
    lanzar una excepción para cancelar entre etapas). Por defecto imprime la etapa."""
    avance = avance or (lambda frac, texto: print(texto))
    from chequeo_artefacto import N_EPOCAS_GRAFICO, T_BASE, epocar, restar_base
    from comparar_filtros import BANDAS, analizar_banda
    from comparar_referencias import REFERENCIAS, epocas_por_referencia, resumen_referencia
    from filtrado import (MASTOIDES_ENLAZADAS, PROMEDIO, disenar_filtros, filtrar,
                          cargar_y_referenciar, interpolar_artefacto, nombre_referencia)
    from promedio import varianza_ruido
    from segmentacion import cargar_eventos
    from snr import (ajustar_pendiente, curva_snr, curva_snr_paper, diferencia_metodos,
                     jackknife_snr, snr_teorica_ajustada, snr_todos_los_metodos)
    from teoria import comparar_con_teoria, reproducibilidad

    R = {}
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int)

    # Decisiones 1 y 2: espectro, artefacto y bandas (CP4-Fz sin filtrar, una carga)
    avance(0.00, f"Cargando {cfg.ARCHIVO_EEG.name} ({cfg.CANAL}–{cfg.REFERENCIA})")
    raw = cargar_y_referenciar(cfg.ARCHIVO_EEG, cfg.CANALES, cfg.REFERENCIA)
    fs, x_sin = raw.info["sfreq"], raw.get_data()
    x_int = interpolar_artefacto(x_sin, muestras, fs, *cfg.T_ARTEFACTO)
    filtros = disenar_filtros(fs, cfg.F_BAJO, cfg.F_ALTO, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH)
    padlen = min(int(3 * fs / cfg.F_BAJO), x_sin.shape[1] - 1)
    x_fil = filtrar(x_int, filtros, padlen)
    f, psd_c = welch(x_int[0], fs=fs, nperseg=int(fs))
    _, psd_f = welch(x_fil[0], fs=fs, nperseg=int(fs))
    R["psd"] = dict(f=f, psd_crudo=psd_c, psd_filtrado=psd_f)

    avance(0.15, "Artefacto de estímulo")
    ep_c, t = epocar(x_sin, muestras, fs, cfg.TMIN, cfg.TMAX)
    ep_f, _ = epocar(filtrar(x_sin, filtros, padlen), muestras, fs, cfg.TMIN, cfg.TMAX)
    ep_i, _ = epocar(x_fil, muestras, fs, cfg.TMIN, cfg.TMAX)
    ep_c = restar_base(ep_c, t, T_BASE)
    sel = np.linspace(0, ep_c.shape[0] - 1, N_EPOCAS_GRAFICO).astype(int)
    R["artefacto"] = dict(t=t, epocas_zoom=ep_c[sel, 0], prom_crudo=ep_c.mean(0)[0],
                          prom_filtrado=restar_base(ep_f, t, (cfg.TMIN, 0)).mean(0)[0],
                          prom_interpolado=restar_base(ep_i, t, (cfg.TMIN, 0)).mean(0)[0])
    del ep_c, ep_f, ep_i, x_fil

    avance(0.22, "Bandas de filtrado")
    pes_b, filas_b = {}, []
    for nombre, (fb, fa) in BANDAS.items():
        t_b, pes_b[nombre], fila = analizar_banda(x_int, fs, eventos, fb, fa)
        filas_b.append({"banda": nombre, **fila})
    R["filtros"] = dict(t=t_b, pes=pes_b, tabla=pd.DataFrame(filas_b))
    del x_sin, x_int

    # Decisiones 3 y 4: referencias y lateralidad (una carga con CP4, CP3 y referencias)
    avance(0.35, "Referencias y lateralidad")
    refs = [r for r in REFERENCIAS if incluir_promedio or r != PROMEDIO]
    canales = [cfg.CANAL] + [c for c in cfg.CANALES_LATERALIDAD if c != cfg.CANAL]
    ep_ref = epocas_por_referencia(refs, canales)
    pes_r, ruidos_r, rms_r, snr_r, filas_r = {}, {}, {}, {}, []
    for etq, (ep, t_r) in ep_ref.items():
        pes_r[etq], ruidos_r[etq], fila = resumen_referencia(ep[:, :1], t_r)
        rms_r[etq], snr_r[etq] = fila["ruido_rms_uV"] / 1e6, fila["SNR_homog_dB"]
        filas_r.append({"referencia": etq, **fila})
    R["referencias"] = dict(t=t_r, pes=pes_r, ruidos=ruidos_r, rms=rms_r, snr=snr_r,
                            tabla=pd.DataFrame(filas_r))
    etq_lat = nombre_referencia(cfg.REFERENCIA_LATERALIDAD)
    ep_l, t_l = ep_ref[etq_lat]
    pe_l = ep_l.mean(0)
    comp_l = comparar_con_teoria(t_l, pe_l[:1], cfg.CANALES)
    n20_l = comp_l[comp_l["componente"] == "N20"].iloc[0]
    R["lateralidad"] = dict(t=t_l, pes={c: pe_l[k] for k, c in enumerate(canales)}, ref=etq_lat,
                            lat_n20=n20_l["lat_ms"] if n20_l["valido"] else None)

    # Resultados: análisis completo con la referencia elegida (CP4-Fz)
    avance(0.55, "Promedios, SNR y curvas (referencia elegida)")
    ep, t = ep_ref[nombre_referencia(cfg.REFERENCIA)]
    ep = ep[:, :1]
    M = ep.shape[0]
    del ep_ref
    r = snr_todos_los_metodos(ep, t, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
    avance(0.62, "SNR con incertidumbre (jackknife)")
    jk = jackknife_snr(ep, t, METODOS, cfg.N_BLOQUES_JK, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
    difs = []
    for met in METODOS[1:]:
        d = diferencia_metodos(jk, met, "homogeneo")
        difs.append(dict(metodo=met, dif_db=d["dif_db"][0], se_db=d["se_db"][0],
                         ic95_inf=d["ic_inf"][0], ic95_sup=d["ic_sup"][0]))
    comp = comparar_con_teoria(t, r["homogeneo"]["pe"], cfg.CANALES)
    n20 = comp[comp["componente"] == "N20"].iloc[0]
    lat_n20 = n20["lat_ms"] / 1e3 if n20["valido"] else np.nan
    n_valores = sorted({n for n in cfg.N_VALORES if n < M} | {M})
    curvas, pend = {}, {}
    for k, met in enumerate(METODOS):
        avance(0.72 + 0.05 * k, f"Curva SNR vs. N ({NOMBRE_METODO[met]})")
        c = curva_snr(ep, t, n_valores, met, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE,
                      n_bloques_jk=cfg.N_BLOQUES_JK)
        curvas[met] = dict(n=c["n"], snr_db=c["snr_db"][:, 0], se_db=c["se_db"][:, 0])
        pend[met] = ajustar_pendiente(c["n"], c["snr_db"][:, 0], c["se_db"][:, 0])[1:]
    avance(0.93, "SNR del paper y reproducibilidad")
    cp = curva_snr_paper(ep, t, n_valores, lat_n20, cfg.SEMIANCHO_SNR_PAPER, cfg.N_BLOQUES_JK)
    cp = dict(n=cp["n"], snr_db=cp["snr_db"][:, 0], se_db=cp["se_db"][:, 0])
    h = curvas["homogeneo"]
    rep = reproducibilidad(t, ep, cfg.CANALES)
    R["resultados"] = dict(
        t=t, M=M, pes={m: r[m]["pe"][0] for m in METODOS}, rms_ruido=r["homogeneo"]["rms_ruido"][0],
        componentes=comp, snr={m: (jk[m]["snr_db"][0], jk[m]["se_db"][0]) for m in METODOS},
        difs=pd.DataFrame(difs), curvas=curvas, pendientes=pend,
        recta=(h["n"], snr_teorica_ajustada(h["n"], h["snr_db"], h["se_db"])),
        curva_paper=cp, pendiente_paper=ajustar_pendiente(cp["n"], cp["snr_db"], cp["se_db"])[1:],
        recta_paper=(cp["n"], snr_teorica_ajustada(cp["n"], cp["snr_db"], cp["se_db"])),
        sigma2=varianza_ruido(ep, np.ones(ep.shape[:2]))[:, 0],
        pesos={m: r[m]["pesos"][:, 0] for m in METODOS[1:]},
        pe1=ep[:M // 2].mean(0)[0], pe2=ep[M // 2:].mean(0)[0], reproducibilidad=rep.iloc[0],
        tabla_reproducibilidad=rep)
    avance(1.00, "Listo")
    return R


def construir_figuras(R):
    """Figuras a partir de los resultados de calcular(). Devuelve {nombre: Figure}."""
    F, Rf, Rr, L, X = R["psd"], R["filtros"], R["referencias"], R["lateralidad"], R["resultados"]
    return {
        "01_psd": fig_psd(F),
        "02_artefacto": fig_artefacto(R["artefacto"]),
        "03_filtros": fig_filtros(Rf["t"], Rf["pes"], Rf["tabla"]),
        "04_referencias": fig_referencias(Rr["t"], Rr["pes"], Rr["ruidos"], Rr["rms"], Rr["snr"]),
        "05_lateralidad": fig_lateralidad(L["t"], L["pes"], L["ref"], L["lat_n20"]),
        "06_pep_metodos": fig_pep_metodos(X["t"], X["pes"], X["rms_ruido"], X["componentes"]),
        "07_curvas_snr": fig_curvas(X["curvas"], X["pendientes"], X["recta"], X["curva_paper"],
                                    X["pendiente_paper"], X["recta_paper"]),
        "08_diferencias_metodos": fig_forest(X["difs"]),
        "09_pesos": fig_pesos(X["sigma2"], X["pesos"]),
        "10_reproducibilidad": fig_reproducibilidad(X["t"], X["pe1"], X["pe2"], X["reproducibilidad"]),
    }


def guardar_tablas(R, carpeta=None):
    """Tablas que acompañan a las figuras (CSV en la carpeta de figuras)."""
    carpeta = carpeta or cfg.DIR_FIGURAS
    carpeta.mkdir(parents=True, exist_ok=True)
    X = R["resultados"]
    R["filtros"]["tabla"].to_csv(carpeta / "03_filtros.csv", index=False)
    R["referencias"]["tabla"].to_csv(carpeta / "04_referencias.csv", index=False)
    snr = pd.DataFrame([dict(metodo=m, snr_db=v[0], se_db=v[1], pendiente_db_decada=X["pendientes"][m][0],
                             se_pendiente=X["pendientes"][m][1]) for m, v in X["snr"].items()])
    snr.to_csv(carpeta / "07_snr_metodos.csv", index=False)
    X["difs"].to_csv(carpeta / "08_diferencias_metodos.csv", index=False)
    X["componentes"].to_csv(carpeta / "06_componentes.csv", index=False)


def generar_todas(incluir_promedio=True, mostrar=True):
    estilo()
    R = calcular(incluir_promedio)
    print("\nGenerando figuras en", cfg.DIR_FIGURAS)
    figs = construir_figuras(R)
    for nombre, fig in figs.items():
        guardar(fig, nombre)
    guardar_tablas(R)
    if mostrar:
        plt.show()
    return figs


if __name__ == "__main__":
    generar_todas(incluir_promedio="--sin-promedio" not in sys.argv)
