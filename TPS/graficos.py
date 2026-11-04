# graficos.py
# Figuras finales del informe, con estilo uniforme. Tres partes:
#   1. Estilo común: colores fijos por método y por referencia, tipografía para A4,
#      coma decimal en los ejes, guardado en PNG (300 dpi) y PDF en informe/figuras/.
#   2. Una función por figura (fig_*): reciben datos YA calculados (arrays, tablas)
#      y devuelven la figura. No leen archivos ni calculan nada del pipeline.
#   3. Orquestador (generar_todas): procesa los dos nervios con las funciones del
#      pipeline (filtrado, segmentacion, promedio, snr, teoria) y llama a las fig_*.
#
# Figuras (objetivos de la cátedra):
#   Obj. 1 (filtrado):     01 PSD crudo vs. filtrado | 02 artefacto e interpolación |
#                          03 comparación de pasaaltos
#   Obj. 2 (promediado):   04 PEP final con componentes | 05 comparación de referencias |
#                          06 lateralidad del mediano
#   Obj. 3 (SNR):          07 curvas SNR vs. N | 08 diferencias entre métodos (forest) |
#                          09 pesos del inhomogéneo, tibial RM vs. Fz
#   Control de calidad:    10 reproducibilidad (primera vs. segunda mitad)
#
# Ejecutar desde la raíz del repo:   python TPS/graficos.py
# (carga los dos nervios: tarda varios minutos)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from scipy.signal import welch

import config as cfg

# --------------------------------------------------------------------------
# 1. Estilo
# --------------------------------------------------------------------------
COLOR_METODO = {"homogeneo": "#1f77b4", "n": "#ff7f0e", "s": "#2ca02c", "sn": "#d62728"}
NOMBRE_METODO = {"homogeneo": "Homogéneo", "n": "Inhomogéneo (n)", "s": "Inhomogéneo (s)",
                 "sn": "Inhomogéneo (sn)"}
COLOR_REF = {"RM": "#1f77b4", "Fz": "#ff7f0e", "FPz": "#2ca02c", "LMRM": "#d62728",
             "PROM": "#9467bd"}
NOMBRE_REF = {"RM": "Mastoides der. (RM)", "Fz": "Fz", "FPz": "FPz",
              "LMRM": "Mastoides enlazadas", "PROM": "Promedio"}
NOMBRE_NERVIO = {"tibial": "Nervio tibial", "mediano": "Nervio mediano"}
ANCHO_A4 = 6.3   # pulgadas, ancho útil de una página A4 con márgenes de 2,5 cm


def estilo():
    plt.rcParams.update({
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 7.5,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.grid": True, "grid.alpha": 0.3,
        "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.2,
        "figure.dpi": 110, "savefig.bbox": "tight"})


def coma(x, _=None):
    """Formato con coma decimal y sin ceros sobrantes."""
    s = f"{x:.6g}"
    return s.replace(".", ",")


def _ejes_coma(ax, x=True, y=True):
    if x:
        ax.xaxis.set_major_formatter(FuncFormatter(coma))
    if y:
        ax.yaxis.set_major_formatter(FuncFormatter(coma))


def _marcar_estimulo(ax, ventana=None):
    ax.axvline(0, color="k", lw=0.6)
    if ventana is not None:
        ax.axvspan(*(np.asarray(ventana) * 1e3), color="0.92", zorder=0, lw=0)


def guardar(fig, nombre, carpeta=None):
    carpeta = carpeta or cfg.DIR_FIGURAS
    carpeta.mkdir(parents=True, exist_ok=True)
    for ext, dpi in (("png", 300), ("pdf", None)):
        fig.savefig(carpeta / f"{nombre}.{ext}", dpi=dpi)
    print(f"  guardada {nombre}.png / .pdf")


def fmt(x, d=1):
    """Número con d decimales y coma decimal (sin '-0')."""
    x = 0.0 if abs(round(float(x), d)) == 0 else float(x)
    return f"{x:.{d}f}".replace(".", ",")


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


# --------------------------------------------------------------------------
# 2. Figuras. Cada argumento "por_nervio" es {nervio: dict(...)}.
# --------------------------------------------------------------------------
def fig_psd(por_nervio, f_bajo, f_alto, f_notch):
    """01. PSD (Welch) del EEG crudo y filtrado. por_nervio[n] = dict(f, psd_crudo,
    psd_filtrado, canal); psd en V²/Hz."""
    fig, axs = plt.subplots(1, len(por_nervio), figsize=(ANCHO_A4, 2.7), squeeze=False)
    for ax, (nervio, d) in zip(axs[0], por_nervio.items()):
        m = (d["f"] >= 1) & (d["f"] <= 250)
        ax.semilogy(d["f"], d["psd_crudo"] * 1e12, color="0.55", lw=0.8, label="Crudo (interpolado)")
        ax.semilogy(d["f"], d["psd_filtrado"] * 1e12, color="#1f77b4", lw=1, label="Filtrado")
        ax.axvspan(f_bajo, f_alto, color="#1f77b4", alpha=0.07, lw=0,
                   label=f"Banda de paso {fmt(f_bajo, 0)}–{fmt(f_alto, 0)} Hz")
        if f_notch:
            ax.axvline(f_notch, color="#d62728", lw=0.7, ls=":", label=f"{f_notch:g} Hz (red)")
        p = d["psd_crudo"][m] * 1e12
        ax.set(xlim=(0, 250), ylim=(p.min() / 1e3, p.max() * 3), xlabel="Frecuencia (Hz)",
               ylabel="PSD (µV²/Hz)", title=f"{NOMBRE_NERVIO[nervio]} — {d['canal']}")
        _ejes_coma(ax, y=False)
    _leyenda_figura(fig, axs, ncol=4, alto=0.1)
    return fig


def fig_artefacto(por_nervio, t_artefacto):
    """02. Artefacto de estímulo. por_nervio[n] = dict(t, epocas_zoom (k, N), prom_crudo,
    prom_filtrado, prom_interpolado, canal, ventana), en V."""
    fig, axs = plt.subplots(len(por_nervio), 2, figsize=(ANCHO_A4, 2.3 * len(por_nervio) + 0.5),
                            squeeze=False)
    for fila, (nervio, d) in enumerate(por_nervio.items()):
        t_ms = d["t"] * 1e3
        z = (t_ms >= -5) & (t_ms <= 15)
        a1, a2 = axs[fila]
        a1.plot(t_ms[z], d["epocas_zoom"][:, z].T * 1e6, color="0.82", lw=0.4)
        a1.plot([], [], color="0.82", lw=0.8, label="Épocas individuales (sin filtrar)")
        a1.plot(t_ms[z], d["prom_crudo"][z] * 1e6, "k", lw=1.2, label="Promedio sin filtrar")
        a1.axvspan(*(np.asarray(t_artefacto) * 1e3), color="#ff7f0e", alpha=0.2, lw=0,
                   label=f"Ventana interpolada ({fmt(t_artefacto[0] * 1e3, 0)} a "
                         f"{fmt(t_artefacto[1] * 1e3, 0)} ms)")
        a1.axvline(0, color="k", lw=0.6)
        a1.set(xlabel="Tiempo (ms)", ylabel="µV",
               title=f"{NOMBRE_NERVIO[nervio]} — {d['canal']}: sin filtrar")
        a2.plot(t_ms, d["prom_crudo"] * 1e6, color="0.6", lw=0.8)
        a2.plot(t_ms, d["prom_filtrado"] * 1e6, color="#1f77b4", label="Filtrado sin interpolar")
        a2.plot(t_ms, d["prom_interpolado"] * 1e6, color="#ff7f0e", ls="--",
                label="Filtrado con interpolación")
        _marcar_estimulo(a2, d["ventana"])
        lim = 1.4 * np.abs(d["prom_interpolado"]).max() * 1e6
        a2.set(ylim=(-lim, lim), xlabel="Tiempo (ms)", ylabel="µV",
               title="Filtro e interpolación")
        for a in (a1, a2):
            _ejes_coma(a)
    _leyenda_figura(fig, axs, ncol=3, alto=0.08)
    return fig


def fig_pasaaltos(por_nervio, f_alto):
    """03. PEP con distintos cortes del pasaaltos. por_nervio[n] = dict(t, pes {corte: pe},
    canal, ventana)."""
    fig, axs = plt.subplots(1, len(por_nervio), figsize=(ANCHO_A4, 2.8), squeeze=False)
    for ax, (nervio, d) in zip(axs[0], por_nervio.items()):
        colores = plt.cm.viridis(np.linspace(0, 0.85, len(d["pes"])))
        for (corte, pe), c in zip(d["pes"].items(), colores):
            ax.plot(d["t"] * 1e3, pe * 1e6, color=c, label=f"Pasaaltos {coma(corte)} Hz")
        _marcar_estimulo(ax, d["ventana"])
        ax.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
               title=f"{NOMBRE_NERVIO[nervio]} — {d['canal']}")
        _ejes_coma(ax)
    _leyenda_figura(fig, axs, ncol=len(next(iter(por_nervio.values()))["pes"]), alto=0.09)
    fig.suptitle(f"Pasabajos fijo en {f_alto:g} Hz", fontsize=8, y=0.995, color="0.3")
    return fig


def fig_pep_final(por_nervio):
    """04. PEP final (promedio homogéneo) con componentes rotulados y banda ±2·RMS del
    ruido residual. por_nervio[n] = dict(t, pe, rms_ruido (V), componentes (DataFrame de
    teoria.comparar_con_teoria para el canal), canal, ref, ventana)."""
    fig, axs = plt.subplots(1, len(por_nervio), figsize=(ANCHO_A4, 3.0), squeeze=False)
    for ax, (nervio, d) in zip(axs[0], por_nervio.items()):
        t_ms, pe = d["t"] * 1e3, d["pe"] * 1e6
        banda = 2 * d["rms_ruido"] * 1e6
        ax.fill_between(t_ms, pe - banda, pe + banda, color="#1f77b4", alpha=0.2, lw=0,
                        label="±2·RMS del ruido residual")
        ax.plot(t_ms, pe, color="#1f77b4", label="Promedio homogéneo")
        _marcar_estimulo(ax, d["ventana"])
        comp = d["componentes"]
        comp = comp[~comp["componente"].str.contains("pico a pico") & comp["valido"].astype(bool)]
        for _, c in comp.iterrows():
            arriba = c["amp_uV"] > 0
            ax.plot(c["lat_ms"], c["amp_uV"], "o", color="k", ms=3)
            ax.annotate(f"{c['componente']}\n{fmt(c['lat_ms'])} ms", (c["lat_ms"], c["amp_uV"]),
                        xytext=(0, 6 if arriba else -6), textcoords="offset points",
                        ha="center", va="bottom" if arriba else "top", fontsize=6.5)
        rango = np.ptp(pe)
        ax.set(ylim=(pe.min() - 0.4 * rango, pe.max() + 0.4 * rango), xlabel="Tiempo (ms)",
               ylabel="Amplitud (µV)", title=f"{NOMBRE_NERVIO[nervio]} — {d['canal']}–{d['ref']}")
        _ejes_coma(ax)
    _leyenda_figura(fig, axs, ncol=2, alto=0.08)
    return fig


def fig_referencias(por_nervio):
    """05. PEP y ruido residual con distintas referencias (misma escala por columna).
    por_nervio[n] = dict(t, pes {ref: pe}, ruidos {ref: ruido}, rms {ref: V}, snr {ref: dB},
    canal, ventana)."""
    fig, axs = plt.subplots(2, len(por_nervio), figsize=(ANCHO_A4, 5.2), squeeze=False,
                            sharex="col")
    for col, (nervio, d) in enumerate(por_nervio.items()):
        ax_pe, ax_r = axs[0, col], axs[1, col]
        t_ms = d["t"] * 1e3
        for ref in d["pes"]:
            c = COLOR_REF.get(ref, "0.3")
            ax_pe.plot(t_ms, d["pes"][ref] * 1e6, color=c, lw=1, label=NOMBRE_REF.get(ref, ref))
            ax_r.plot(t_ms, d["ruidos"][ref] * 1e6, color=c, lw=0.8,
                      label=f"SNR {fmt(d['snr'][ref])} dB · RMS {fmt(d['rms'][ref] * 1e6, 2)} µV")
        for a in (ax_pe, ax_r):
            _marcar_estimulo(a, d["ventana"])
            _ejes_coma(a)
        ax_r.set_ylim(ax_pe.get_ylim())
        ax_pe.set(ylabel="Amplitud (µV)", title=f"{NOMBRE_NERVIO[nervio]} — {d['canal']}: PEP")
        ax_r.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
                 title="Ruido residual (par/impar)")
        ax_r.legend(fontsize=6, loc="upper right", framealpha=0.85)
    handles, labels = axs[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return fig


def fig_lateralidad(t, pes, ref, ventana, lat_n20=None):
    """06. Mediano: PEP en CP3 (ipsilateral) y CP4 (contralateral) con una referencia
    simétrica. pes = {canal: pe}; lat_n20 = latencia (ms) del N20 contralateral."""
    fig, ax = plt.subplots(figsize=(ANCHO_A4 * 0.62, 2.7))
    estilos = {"CP4": dict(color="#d62728", label="CP4 (contralateral)"),
               "CP3": dict(color="#1f77b4", ls="--", label="CP3 (ipsilateral)")}
    for canal, pe in pes.items():
        ax.plot(t * 1e3, pe * 1e6, **estilos.get(canal, dict(label=canal)))
    _marcar_estimulo(ax, ventana)
    if lat_n20 is not None:
        ax.axvline(lat_n20, color="0.4", lw=0.7, ls=":")
        ax.text(lat_n20 + 1, ax.get_ylim()[1], f"N20 {fmt(lat_n20)} ms", fontsize=7, va="top")
    ax.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
           title=f"Lateralidad — mediano izquierdo\n(ref. {NOMBRE_REF.get(ref, ref).lower()})")
    _ejes_coma(ax)
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    return fig


def fig_curvas(por_nervio, metodos=("homogeneo", "n")):
    """07. SNR vs. N con barras de error. por_nervio[n] = dict(curvas {ref: {metodo: dict(n,
    snr_db, se_db)}} para el canal principal (arrays 1D), pendientes {ref: {metodo: (b, sb)}},
    recta (N, snr) ajustada del homogéneo con la ref. principal, ref_principal, canal)."""
    fig, axs = plt.subplots(1, len(por_nervio), figsize=(ANCHO_A4, 3.2), squeeze=False)
    for ax, (nervio, d) in zip(axs[0], por_nervio.items()):
        lineas = []
        refs = sorted(d["curvas"], key=lambda r: r != d["ref_principal"])
        for r_i, ref in enumerate(refs):
            principal = ref == d["ref_principal"]
            for m_i, met in enumerate(metodos):
                c = d["curvas"][ref][met]
                b, sb = d["pendientes"][ref][met]
                x = c["n"] * (1 + 0.03 * (2 * r_i + m_i - 1.5))
                ax.errorbar(x, c["snr_db"], yerr=c["se_db"], fmt="o-" if principal else "s--",
                            ms=3, capsize=2, lw=1 if principal else 0.8, color=COLOR_METODO[met],
                            alpha=1 if principal else 0.45,
                            label=f"{NOMBRE_METODO[met]}, ref. {ref}")
                lineas.append(f"{NOMBRE_METODO[met].split(' ')[0][:5]}. {met if met != 'homogeneo' else ''}"
                              f" {ref}: {fmt(b)} ± {fmt(sb)}".replace("  ", " "))
        ax.plot(*d["recta"], "k:", lw=1, label="+10·log₁₀(N) ajustada (teórica)")
        ax.text(0.03, 0.97, "Pendiente (dB/década):\n" + "\n".join(lineas), transform=ax.transAxes,
                va="top", fontsize=6, bbox=dict(boxstyle="round", fc="white", ec="0.8", alpha=0.9))
        ax.set_xscale("log")
        ticks = []                                   # evita rótulos encimados (100 y 125)
        for n in d["curvas"][d["ref_principal"]][metodos[0]]["n"]:
            if not ticks or n / ticks[-1] >= 1.4:
                ticks.append(n)
        ax.set_xticks(ticks)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
        ax.xaxis.set_minor_formatter(FuncFormatter(lambda x, _: ""))
        ax.set(xlabel="N épocas promediadas", ylabel="SNR (dB)",
               title=f"{NOMBRE_NERVIO[nervio]} — {d['canal']}")
        _ejes_coma(ax, x=False)
    _leyenda_figura(fig, axs, ncol=3, alto=0.13)
    return fig


def fig_forest(tabla):
    """08. Diferencia de SNR respecto del homogéneo con IC 95 %. tabla: DataFrame con
    columnas nervio, ref, metodo, dif_db, ic95_inf, ic95_sup (canal principal)."""
    filas = tabla.reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(ANCHO_A4 * 0.8, 0.3 * len(filas) + 1.3))
    y = np.arange(len(filas))[::-1].astype(float)
    grupo_prev = None
    for yi, (_, f) in zip(y, filas.iterrows()):
        c = COLOR_REF.get(f["ref"], "0.3")
        ax.errorbar(f["dif_db"], yi, xerr=[[f["dif_db"] - f["ic95_inf"]], [f["ic95_sup"] - f["dif_db"]]],
                    fmt="o", color=c, ms=4, capsize=3)
        sig = "*" if (f["ic95_inf"] > 0 or f["ic95_sup"] < 0) else ""
        ax.text(f["ic95_sup"] + 0.12, yi, f"{fmt(f['dif_db'], 2)} dB{sig}", va="center",
                fontsize=6.5, color=c)
        grupo = (f["nervio"], f["ref"])
        if grupo_prev is not None and grupo != grupo_prev:
            ax.axhline(yi + 0.5, color="0.85", lw=0.6)
        grupo_prev = grupo
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{f['nervio'].capitalize()} · {f['ref']} · {f['metodo']}"
                        for _, f in filas.iterrows()], fontsize=7)
    ax.set_xlim(right=ax.get_xlim()[1] + 0.6)
    ax.set(xlabel="Diferencia de SNR respecto del homogéneo (dB), IC 95 %",
           title="Ganancia del promedio inhomogéneo (jackknife pareado)")
    _ejes_coma(ax, y=False)
    ax.grid(axis="y", alpha=0)
    for ref, c in COLOR_REF.items():
        if ref in set(filas["ref"]):
            ax.plot([], [], "o", color=c, label=f"Referencia {NOMBRE_REF[ref]}")
    ax.plot([], [], " ", label="* IC 95 % que excluye el 0")
    _leyenda_figura(fig, ax, ncol=3, alto=0.07)
    return fig


def fig_pesos(por_ref, canales):
    """09. Varianza del ruido y peso relativo de cada época (modo "n") con dos
    referencias, lado a lado y con la misma escala. por_ref[ref] = dict(sigma2 (M, C) en V²,
    w_rel (M, C), ganancia_db opcional)."""
    refs = list(por_ref)
    fig, axs = plt.subplots(2, len(refs), figsize=(ANCHO_A4, 4.4), sharex=True, sharey="row",
                            squeeze=False)
    colores = ["#1f77b4", "#ff7f0e"]
    for col, ref in enumerate(refs):
        d = por_ref[ref]
        M = d["sigma2"].shape[0]
        for i, canal in enumerate(canales):
            axs[0, col].plot(np.arange(M), d["sigma2"][:, i] * 1e12, lw=0.6, color=colores[i % 2],
                             label=canal)
            axs[1, col].plot(np.arange(M), d["w_rel"][:, i], lw=0.6, color=colores[i % 2])
        axs[1, col].axhline(1, color="k", lw=0.7, ls="--", label="Peso del homogéneo (1/M)")
        titulo = f"Tibial — ref. {NOMBRE_REF.get(ref, ref)}"
        if "ganancia_db" in d:
            titulo += f"\nganancia de n en {canales[-1]}: {fmt(d['ganancia_db'], 2)} dB"
        axs[0, col].set_title(titulo)
        axs[1, col].set_xlabel("Número de época (orden temporal)")
        for a in axs[:, col]:
            _ejes_coma(a)
    axs[0, 0].set_ylabel("σ² del ruido (µV²)")
    axs[1, 0].set_ylabel("Peso relativo (w·M)")
    _leyenda_figura(fig, axs, ncol=3, alto=0.06)
    return fig


def fig_reproducibilidad(por_nervio):
    """10. Subpromedios de la primera y la segunda mitad del registro. por_nervio[n] =
    dict(t, pe1, pe2, canal, ref, fila (Series de teoria.reproducibilidad), ventana)."""
    fig, axs = plt.subplots(1, len(por_nervio), figsize=(ANCHO_A4, 2.9), squeeze=False)
    for ax, (nervio, d) in zip(axs[0], por_nervio.items()):
        t_ms = d["t"] * 1e3
        ax.plot(t_ms, d["pe1"] * 1e6, color="#1f77b4", label="Primera mitad del registro")
        ax.plot(t_ms, d["pe2"] * 1e6, color="#d62728", ls="--", label="Segunda mitad del registro")
        _marcar_estimulo(ax, d["ventana"])
        f = d["fila"]
        ok = "cumple" if (f["cumple_lat"] and f["cumple_amp"]) else "no cumple"
        ax.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)")
        ax.set_title(f"{NOMBRE_NERVIO[nervio]} — {d['canal']}–{d['ref']}\n"
                     f"{f['componente']}: Δlat {fmt(f['dif_lat_ms'], 1)} ms, "
                     f"Δamp {fmt(100 * f['dif_amp_rel'], 1)} % ({ok} IFCN)", fontsize=8.5)
        _ejes_coma(ax)
    _leyenda_figura(fig, axs, ncol=2, alto=0.08)
    return fig


# --------------------------------------------------------------------------
# 3. Orquestador: calcula lo necesario con el pipeline y genera las figuras
# --------------------------------------------------------------------------
def _procesar_nervio(nervio, incluir_promedio=True):
    """Carga un nervio una sola vez y calcula todo lo que necesitan las figuras."""
    from chequeo_artefacto import epocar, restar_base, T_BASE, N_EPOCAS_GRAFICO
    from comparar_pasaaltos import CORTES
    from comparar_referencias import REFERENCIAS
    from filtrado import (MASTOIDES_ENLAZADAS, PROMEDIO, _disenar_filtros, _filtrar,
                          canales_de_referencia, cargar_eeg, interpolar_artefacto,
                          nombre_referencia, referenciar, senal_referencia_promedio,
                          seleccionar_canales)
    from promedio import promedio_homogeneo, varianza_ruido
    from segmentacion import cargar_eventos, segmentar_epocas
    from snr import (METODOS, ajustar_pendiente, calcular_snr, curva_snr, diferencia_metodos,
                     jackknife_snr, pesos_homogeneos, ruido_residual, snr_teorica_ajustada,
                     snr_todos_los_metodos)
    from teoria import comparar_con_teoria, reproducibilidad

    P = cfg.parametros(nervio)
    print(f"\n== {NOMBRE_NERVIO[nervio]}: cargando {P['archivo_eeg'].name}")
    canales, principal, ventana = P["canales"], P["canal_principal"], P["ventana_senal"]
    i_p = canales.index(principal)
    refs = [r for r in REFERENCIAS if incluir_promedio or r != PROMEDIO]

    crudo = cargar_eeg(P["archivo_eeg"])
    ref_prom = senal_referencia_promedio(crudo) if PROMEDIO in refs else None
    necesarios = list(dict.fromkeys(canales + [c for r in refs if r != PROMEDIO
                                                for c in canales_de_referencia(r)]))
    raw = seleccionar_canales(crudo, necesarios)
    raw.load_data()
    fs, nombres, datos_rm = raw.info["sfreq"], raw.ch_names, raw.get_data()
    eventos = cargar_eventos(P["archivo_eventos"])
    muestras = eventos["sample"].to_numpy().astype(int)

    def referenciados(ref):
        if ref == PROMEDIO:
            return referenciar(datos_rm, nombres, canales, "RM") - ref_prom
        return referenciar(datos_rm, nombres, canales, ref)

    def preparar(ref, f_bajo=cfg.F_BAJO, interpolar=cfg.INTERPOLAR_ARTEFACTO, filtrar=True):
        x = referenciados(ref)
        if interpolar:
            x = interpolar_artefacto(x, muestras, fs, *cfg.T_ARTEFACTO)
        if filtrar:
            filtros = _disenar_filtros(fs, f_bajo, cfg.F_ALTO, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH)
            x = _filtrar(x, filtros, min(int(3 * fs / f_bajo), x.shape[1] - 1))
        return x

    def epocas_de(x):
        return segmentar_epocas(x, eventos, sfreq=fs, tmin=cfg.TMIN, tmax=P["tmax"])

    out = dict(P=P, fs=fs)
    ref_p = P["referencia"]
    etq_p = nombre_referencia(ref_p)

    # 01 PSD (referencia principal, canal principal)
    x_int = preparar(ref_p, filtrar=False)
    x_fil = preparar(ref_p)
    f, psd_c = welch(x_int[i_p], fs=fs, nperseg=int(2 * fs))
    _, psd_f = welch(x_fil[i_p], fs=fs, nperseg=int(2 * fs))
    out["psd"] = dict(f=f, psd_crudo=psd_c, psd_filtrado=psd_f, canal=principal)

    # 02 Artefacto
    x_sin = preparar(ref_p, interpolar=False, filtrar=False)
    ep_c, t = epocar(x_sin, muestras, fs, cfg.TMIN, P["tmax"])
    ep_f, _ = epocar(preparar(ref_p, interpolar=False), muestras, fs, cfg.TMIN, P["tmax"])
    ep_i, _ = epocar(x_fil, muestras, fs, cfg.TMIN, P["tmax"])
    ep_c = restar_base(ep_c, t, T_BASE)
    sel = np.linspace(0, ep_c.shape[0] - 1, N_EPOCAS_GRAFICO).astype(int)
    out["artefacto"] = dict(t=t, epocas_zoom=ep_c[sel, i_p], prom_crudo=ep_c.mean(0)[i_p],
                            prom_filtrado=restar_base(ep_f, t, (cfg.TMIN, 0)).mean(0)[i_p],
                            prom_interpolado=restar_base(ep_i, t, (cfg.TMIN, 0)).mean(0)[i_p],
                            canal=principal, ventana=ventana)
    del x_sin, ep_c, ep_f, ep_i

    # 03 Pasaaltos (referencia principal)
    pes_hp = {}
    for corte in CORTES:
        ep, t = epocas_de(preparar(ref_p, f_bajo=corte))
        pes_hp[corte] = promedio_homogeneo(ep)[i_p]
    out["pasaaltos"] = dict(t=t, pes=pes_hp, canal=principal, ventana=ventana)

    # 05 Referencias
    pes_r, ruidos_r, rms_r, snr_r = {}, {}, {}, {}
    for ref in refs:
        etq = nombre_referencia(ref)
        ep, t = epocas_de(preparar(ref))
        pe, w = promedio_homogeneo(ep), pesos_homogeneos(ep)
        r = calcular_snr(ep, pe, w, t, ventana)
        pes_r[etq], ruidos_r[etq] = pe[i_p], ruido_residual(ep, w, n_perm=1)[0][i_p]
        rms_r[etq], snr_r[etq] = r["rms_ruido"][i_p], r["snr_db"][i_p]
    out["referencias"] = dict(t=t, pes=pes_r, ruidos=ruidos_r, rms=rms_r, snr=snr_r,
                              canal=principal, ventana=ventana)

    # Análisis completo con la referencia principal y con RM (comparación de métodos)
    analisis = {}
    for ref in dict.fromkeys([ref_p, "RM"]):
        etq = nombre_referencia(ref)
        print(f"   análisis completo con referencia {etq}")
        ep, t = epocas_de(preparar(ref))
        r = snr_todos_los_metodos(ep, t, ventana, cfg.TAM_BLOQUE)
        jk = jackknife_snr(ep, t, METODOS, cfg.N_BLOQUES_JK, ventana, cfg.TAM_BLOQUE)
        difs = {m: diferencia_metodos(jk, m, "homogeneo") for m in METODOS[1:]}
        n_valores = sorted({n for n in cfg.N_VALORES if n < ep.shape[0]} | {ep.shape[0]})
        curvas, pend = {}, {}
        for met in ("homogeneo", "n"):
            c = curva_snr(ep, t, n_valores, met, ventana, cfg.TAM_BLOQUE,
                          n_bloques_jk=cfg.N_BLOQUES_JK)
            curvas[met] = dict(n=c["n"], snr_db=c["snr_db"][:, i_p], se_db=c["se_db"][:, i_p])
            pend[met] = ajustar_pendiente(c["n"], c["snr_db"][:, i_p], c["se_db"][:, i_p])[1:]
        analisis[etq] = dict(epocas=ep, t=t, r=r, difs=difs, curvas=curvas, pendientes=pend,
                             sigma2=varianza_ruido(ep, np.ones(ep.shape[:2])),
                             w_rel=r["n"]["pesos"] * ep.shape[0])
    out["analisis"], out["ref_principal"] = analisis, etq_p

    # 04 y 10: PEP final y reproducibilidad con la referencia principal
    a = analisis[etq_p]
    comp = comparar_con_teoria(a["t"], a["r"]["homogeneo"]["pe"], canales, nervio)
    out["pep"] = dict(t=a["t"], pe=a["r"]["homogeneo"]["pe"][i_p],
                      rms_ruido=a["r"]["homogeneo"]["rms_ruido"][i_p],
                      componentes=comp[comp["canal"] == principal], canal=principal, ref=etq_p,
                      ventana=ventana)
    M = a["epocas"].shape[0]
    rep = reproducibilidad(a["t"], a["epocas"], canales, nervio)
    out["reproducibilidad"] = dict(t=a["t"], pe1=a["epocas"][:M // 2].mean(0)[i_p],
                                   pe2=a["epocas"][M // 2:].mean(0)[i_p], canal=principal,
                                   ref=etq_p, fila=rep[rep["canal"] == principal].iloc[0],
                                   ventana=ventana)

    # 06 Lateralidad (solo mediano): referencia simétrica
    if nervio == "mediano":
        ep, t = epocas_de(preparar(MASTOIDES_ENLAZADAS))
        pe = promedio_homogeneo(ep)
        comp_l = comparar_con_teoria(t, pe, canales, nervio)
        fila_n20 = comp_l[(comp_l["canal"] == principal) & (comp_l["componente"] == "N20")].iloc[0]
        out["lateralidad"] = dict(t=t, pes={c: pe[k] for k, c in enumerate(canales)},
                                  ref=nombre_referencia(MASTOIDES_ENLAZADAS), ventana=ventana,
                                  lat_n20=fila_n20["lat_ms"] if fila_n20["valido"] else None)
    for a in analisis.values():
        a.pop("epocas")          # libera memoria
    return out


def generar_todas(nervios=("tibial", "mediano"), incluir_promedio=True, mostrar=True):
    estilo()
    R = {n: _procesar_nervio(n, incluir_promedio) for n in nervios}
    print("\nGenerando figuras en", cfg.DIR_FIGURAS)
    figs = {
        "01_psd": fig_psd({n: R[n]["psd"] for n in nervios}, cfg.F_BAJO, cfg.F_ALTO, cfg.F_NOTCH),
        "02_artefacto": fig_artefacto({n: R[n]["artefacto"] for n in nervios}, cfg.T_ARTEFACTO),
        "03_pasaaltos": fig_pasaaltos({n: R[n]["pasaaltos"] for n in nervios}, cfg.F_ALTO),
        "04_pep_final": fig_pep_final({n: R[n]["pep"] for n in nervios}),
        "05_referencias": fig_referencias({n: R[n]["referencias"] for n in nervios}),
    }
    if "mediano" in R:
        L = R["mediano"]["lateralidad"]
        figs["06_lateralidad_mediano"] = fig_lateralidad(L["t"], L["pes"], L["ref"], L["ventana"],
                                                         L["lat_n20"])
    figs["07_curvas_snr"] = fig_curvas({
        n: dict(curvas={e: a["curvas"] for e, a in R[n]["analisis"].items()},
                pendientes={e: a["pendientes"] for e, a in R[n]["analisis"].items()},
                recta=(R[n]["analisis"][R[n]["ref_principal"]]["curvas"]["homogeneo"]["n"],
                       snr_teorica_ajustada_principal(R[n])),
                ref_principal=R[n]["ref_principal"], canal=R[n]["P"]["canal_principal"])
        for n in nervios})
    filas = []
    for n in nervios:
        i_p = R[n]["P"]["canales"].index(R[n]["P"]["canal_principal"])
        for etq, a in R[n]["analisis"].items():
            for met, d in a["difs"].items():
                filas.append(dict(nervio=n, ref=etq, metodo=met, dif_db=d["dif_db"][i_p],
                                  ic95_inf=d["ic_inf"][i_p], ic95_sup=d["ic_sup"][i_p]))
    tabla_f = pd.DataFrame(filas)
    figs["08_diferencias_metodos"] = fig_forest(tabla_f)
    if "tibial" in R:
        A = R["tibial"]["analisis"]
        i_p = R["tibial"]["P"]["canales"].index(R["tibial"]["P"]["canal_principal"])
        por_ref = {e: dict(sigma2=A[e]["sigma2"], w_rel=A[e]["w_rel"],
                           ganancia_db=A[e]["difs"]["n"]["dif_db"][i_p])
                   for e in ("RM", R["tibial"]["ref_principal"]) if e in A}
        figs["09_pesos_tibial"] = fig_pesos(por_ref, R["tibial"]["P"]["canales"])
    figs["10_reproducibilidad"] = fig_reproducibilidad({n: R[n]["reproducibilidad"] for n in nervios})
    for nombre, fig in figs.items():
        guardar(fig, nombre)
    tabla_f.to_csv(cfg.DIR_FIGURAS / "08_diferencias_metodos.csv", index=False)
    if mostrar:
        plt.show()
    return figs


def snr_teorica_ajustada_principal(Rn):
    from snr import snr_teorica_ajustada
    c = Rn["analisis"][Rn["ref_principal"]]["curvas"]["homogeneo"]
    return snr_teorica_ajustada(c["n"], c["snr_db"], c["se_db"])


if __name__ == "__main__":
    generar_todas()