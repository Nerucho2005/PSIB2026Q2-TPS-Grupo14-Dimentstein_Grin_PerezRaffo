# comparar_referencias.py
# Compara distintas referencias para justificar la elección del montaje (CP4-Fz).
#
# El EEG está referido a la mastoides derecha (RM). Cada canal es V_canal - V_ref,
# así que si la referencia capta el PEP, se resta y cambia la amplitud (e incluso
# la polaridad). Se comparan:
#   RM                   adquisición (Nierula et al. 2024), sin cambios
#   Fz                   montaje cortical de la IFCN para el mediano (Pc-Fz): elegida
#   mastoides_enlazadas  (LM + RM)/2, simétrica (se usa para la lateralidad)
#   promedio             64 canales de cuero cabelludo, la del paper del dataset;
#                        se calcula por tramos para no cargar los 64 canales juntos
# Al ser una resta, la re-referencia NO cambia las latencias reales: sí la forma,
# la amplitud y la SNR. Para cada referencia se reportan la SNR (homogéneo y "n"),
# el ruido residual, la latencia y amplitud del N20 y del P25 y la amplitud pico a
# pico. El registro se carga una vez con todos los canales necesarios; solo se
# repite la re-referencia, la interpolación y el filtrado.
#
# Ejecutar desde la raíz del repo:   python TPS/comparar_referencias.py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
from filtrado import (MASTOIDES_ENLAZADAS, PROMEDIO, _disenar_filtros, _filtrar,
                      canales_de_referencia, cargar_eeg, interpolar_artefacto,
                      nombre_referencia, referenciar, senal_referencia_promedio,
                      seleccionar_canales)
from promedio import promedio_homogeneo, promedio_inhomogeneo
from segmentacion import cargar_eventos, segmentar_epocas
from snr import calcular_snr, pesos_homogeneos, ruido_residual
from teoria import comparar_con_teoria

REFERENCIAS = ["RM", "Fz", MASTOIDES_ENLAZADAS, PROMEDIO]


def epocas_por_referencia(referencias, canales, f_bajo=None):
    """Carga el registro una vez y devuelve {etiqueta: (epocas, t)} para cada referencia,
    con interpolación del artefacto y el filtrado de config.py."""
    f_bajo = f_bajo or cfg.F_BAJO
    crudo = cargar_eeg(cfg.ARCHIVO_EEG)
    ref_prom = senal_referencia_promedio(crudo) if PROMEDIO in referencias else None
    necesarios = list(dict.fromkeys(
        canales + [c for r in referencias if r != PROMEDIO for c in canales_de_referencia(r)]))
    raw = seleccionar_canales(crudo, necesarios)
    raw.load_data()
    fs, nombres, datos_rm = raw.info["sfreq"], raw.ch_names, raw.get_data()
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int)
    filtros = _disenar_filtros(fs, f_bajo, cfg.F_ALTO, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH)
    padlen = min(int(3 * fs / f_bajo), datos_rm.shape[1] - 1)
    salida = {}
    for ref in referencias:
        if ref == PROMEDIO:
            datos = referenciar(datos_rm, nombres, canales, "RM") - ref_prom
        else:
            datos = referenciar(datos_rm, nombres, canales, ref)
        if cfg.INTERPOLAR_ARTEFACTO:
            datos = interpolar_artefacto(datos, muestras, fs, *cfg.T_ARTEFACTO)
        salida[nombre_referencia(ref)] = segmentar_epocas(_filtrar(datos, filtros, padlen), eventos,
                                                          sfreq=fs, tmin=cfg.TMIN, tmax=cfg.TMAX)
    return salida


def resumen_referencia(epocas, t):
    """PEP, ruido residual (par/impar) y métricas de un canal (el primero)."""
    pe = promedio_homogeneo(epocas)
    w = pesos_homogeneos(epocas)
    snr_h = calcular_snr(epocas, pe, w, t, cfg.VENTANA_SENAL)
    pe_n, w_n = promedio_inhomogeneo(epocas, "n", t, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
    snr_n = calcular_snr(epocas, pe_n, w_n, t, cfg.VENTANA_SENAL)
    comp = comparar_con_teoria(t, pe[:1], cfg.CANALES).set_index("componente")
    fila = {"SNR_homog_dB": snr_h["snr_db"][0], "SNR_n_dB": snr_n["snr_db"][0],
            "ganancia_n_dB": snr_n["snr_db"][0] - snr_h["snr_db"][0],
            "ruido_rms_uV": snr_h["rms_ruido"][0] * 1e6}
    for nombre in ("N20", "P25"):
        fila[f"{nombre}_lat_ms"] = comp.loc[nombre, "lat_ms"]
        fila[f"{nombre}_amp_uV"] = comp.loc[nombre, "amp_uV"]
        fila[f"{nombre}_valido"] = bool(comp.loc[nombre, "valido"])
    fila["N20_P25_pp_uV"] = comp.loc["N20-P25 (pico a pico)", "amp_uV"]
    ruido = ruido_residual(epocas, w, n_perm=1)[0]
    return pe[0], ruido[0], fila


def main():
    ep_ref = epocas_por_referencia(REFERENCIAS, cfg.CANALES)
    pes, ruidos, filas = {}, {}, []
    for etiqueta, (epocas, t) in ep_ref.items():
        pes[etiqueta], ruidos[etiqueta], fila = resumen_referencia(epocas, t)
        filas.append({"referencia": etiqueta, **fila})

    tabla = pd.DataFrame(filas)
    with pd.option_context("display.width", 180, "display.max_columns", 20):
        print(f"\nComparación de referencias — {cfg.CANAL} "
              f"({cfg.F_BAJO:g}-{cfg.F_ALTO:g} Hz, M = {epocas.shape[0]})")
        print(tabla.round(2).to_string(index=False))
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)
    tabla.to_csv(cfg.DIR_RESULTADOS / "comparacion_referencias.csv", index=False)

    # Arriba: PEP. Abajo: ruido residual con la MISMA escala, para ver que una referencia
    # puede achicar la señal pero achicar más el ruido.
    t_ms = t * 1e3
    fig, (ax_pe, ax_r) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    for (etiqueta, pe), color in zip(pes.items(), plt.cm.tab10(np.arange(len(pes)))):
        rms = tabla.loc[tabla.referencia == etiqueta, "ruido_rms_uV"].iloc[0]
        ax_pe.plot(t_ms, pe * 1e6, color=color, lw=1.2, label=f"{cfg.CANAL}–{etiqueta}")
        ax_r.plot(t_ms, ruidos[etiqueta] * 1e6, color=color, lw=1,
                  label=f"{etiqueta} (RMS {rms:.2f} µV)")
    for ax in (ax_pe, ax_r):
        ax.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.93", zorder=0)
        ax.axvline(0, color="k", lw=0.5)
    ax_r.set_ylim(ax_pe.get_ylim())
    ax_pe.set(ylabel="Amplitud (µV)", title=f"PEP del mediano — {cfg.CANAL}: efecto de la referencia")
    ax_r.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
             title="Ruido residual (promedio alternado par/impar)")
    ax_pe.legend(title="Derivación", fontsize=8)
    ax_r.legend(title="RMS en la ventana del PEP", fontsize=8)
    fig.tight_layout()
    fig.savefig(cfg.DIR_RESULTADOS / "comparacion_referencias.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()
