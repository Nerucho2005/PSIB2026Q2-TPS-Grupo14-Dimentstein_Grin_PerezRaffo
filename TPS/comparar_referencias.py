# comparar_referencias.py
# Compara distintas referencias para justificar la elección del montaje.
#
# El EEG está referido a la mastoides derecha (RM). Cada canal es V_canal - V_ref,
# así que si la referencia capta el PEP, se resta y cambia la amplitud (e incluso
# la polaridad). Se comparan:
#   RM                   adquisición (sin cambios)
#   Fz / FPz             montajes IFCN (mediano CP3/CP4-Fz, tibial CPz-FPz)
#   mastoides_enlazadas  (LM + RM)/2, simétrica
#   promedio             64 canales de cuero cabelludo (la del paper del dataset);
#                        se calcula por tramos para no cargar los 64 canales juntos
# Al ser una resta, la re-referencia NO cambia las latencias reales: sí la forma,
# la amplitud y la SNR. Para cada referencia se reportan la SNR (homogéneo y "n"),
# el ruido residual, las latencias y amplitudes de los primeros componentes, y la
# amplitud pico a pico. El registro se carga una vez con todos los canales
# necesarios; solo se repite la re-referencia, la interpolación y el filtrado.
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
from teoria import comparar_con_teoria, componentes_de

REFERENCIAS = ["RM", "Fz", "FPz", MASTOIDES_ENLAZADAS, PROMEDIO]


def main():
    crudo = cargar_eeg(cfg.ARCHIVO_EEG)
    ref_promedio = senal_referencia_promedio(crudo) if PROMEDIO in REFERENCIAS else None
    necesarios = list(dict.fromkeys(
        cfg.CANALES + [c for r in REFERENCIAS if r != PROMEDIO for c in canales_de_referencia(r)]))
    raw = seleccionar_canales(crudo, necesarios)
    raw.load_data()
    fs, nombres, datos_rm = raw.info["sfreq"], raw.ch_names, raw.get_data()
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int)
    filtros = _disenar_filtros(fs, cfg.F_BAJO, cfg.F_ALTO, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH)
    padlen = min(int(3 * fs / cfg.F_BAJO), datos_rm.shape[1] - 1)
    primeros = list(componentes_de(cfg.NERVIO))[:2]

    pes, ruidos, filas = {}, {}, []
    for ref in REFERENCIAS:
        etiqueta = nombre_referencia(ref)
        if ref == PROMEDIO:
            datos = referenciar(datos_rm, nombres, cfg.CANALES, "RM") - ref_promedio
        else:
            datos = referenciar(datos_rm, nombres, cfg.CANALES, ref)
        if cfg.INTERPOLAR_ARTEFACTO:
            datos = interpolar_artefacto(datos, muestras, fs, *cfg.T_ARTEFACTO)
        epocas, t = segmentar_epocas(_filtrar(datos, filtros, padlen), eventos, sfreq=fs,
                                     tmin=cfg.TMIN, tmax=cfg.TMAX)

        pe = promedio_homogeneo(epocas)
        snr_h = calcular_snr(epocas, pe, pesos_homogeneos(epocas), t, cfg.VENTANA_SENAL)
        pe_n, w_n = promedio_inhomogeneo(epocas, "n", t, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
        snr_n = calcular_snr(epocas, pe_n, w_n, t, cfg.VENTANA_SENAL)
        pes[etiqueta] = pe
        # ruido residual del promedio homogéneo: promedio alternado par/impar (n_perm=1)
        ruidos[etiqueta] = ruido_residual(epocas, pesos_homogeneos(epocas), n_perm=1)[0]

        comp = comparar_con_teoria(t, pe, cfg.CANALES, cfg.NERVIO).set_index(["canal", "componente"])
        for i, canal in enumerate(cfg.CANALES):
            fila = {"referencia": etiqueta, "canal": canal,
                    "SNR_homog_dB": snr_h["snr_db"][i], "SNR_n_dB": snr_n["snr_db"][i],
                    "ruido_rms_uV": snr_h["rms_ruido"][i] * 1e6}
            for nombre in primeros:
                fila[f"{nombre}_lat_ms"] = comp.loc[(canal, nombre), "lat_ms"]
                fila[f"{nombre}_amp_uV"] = comp.loc[(canal, nombre), "amp_uV"]
                fila[f"{nombre}_borde"] = comp.loc[(canal, nombre), "borde"]
            pp = [c for c in comp.loc[canal].index if "pico a pico" in c][0]
            fila["pico_a_pico_uV"] = comp.loc[(canal, pp), "amp_uV"]
            filas.append(fila)

    tabla = pd.DataFrame(filas).sort_values(["canal", "referencia"], kind="stable")
    with pd.option_context("display.width", 180, "display.max_columns", 20):
        print(f"\nComparación de referencias — {cfg.NERVIO} "
              f"({cfg.F_BAJO:g}-{cfg.F_ALTO:g} Hz, M = {epocas.shape[0]})")
        print(tabla.round(2).to_string(index=False))
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)
    tabla.to_csv(cfg.DIR_RESULTADOS / f"comparacion_referencias_{cfg.NERVIO}.csv", index=False)

    t_ms = t * 1e3
    colores = plt.cm.tab10(np.arange(len(REFERENCIAS)))
    # Fila 1: PEP (promedio homogéneo). Fila 2: ruido residual con la MISMA escala,
    # para ver que una referencia puede achicar la señal pero achicar más el ruido.
    fig, axs = plt.subplots(2, len(cfg.CANALES), figsize=(6.5 * len(cfg.CANALES), 7.5),
                            squeeze=False, sharex=True)
    for i, canal in enumerate(cfg.CANALES):
        ax_pe, ax_r = axs[0, i], axs[1, i]
        for etiqueta, color in zip(pes, colores):
            rms = tabla.loc[(tabla.referencia == etiqueta) & (tabla.canal == canal),
                            "ruido_rms_uV"].iloc[0]
            ax_pe.plot(t_ms, pes[etiqueta][i] * 1e6, color=color, lw=1.2,
                       label=f"{canal}–{etiqueta}")
            ax_r.plot(t_ms, ruidos[etiqueta][i] * 1e6, color=color, lw=1,
                      label=f"{etiqueta} (RMS {rms:.2f} µV)")
        for ax in (ax_pe, ax_r):
            ax.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.93", zorder=0)
            ax.axvline(0, color="k", lw=0.5)
        ax_r.set_ylim(ax_pe.get_ylim())
        ax_pe.set(ylabel="Amplitud (µV)", title=f"PEP {cfg.NERVIO} — {canal}: efecto de la referencia")
        ax_r.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
                 title=f"{canal}: ruido residual (promedio alternado par/impar)")
        ax_pe.legend(title="Derivación", fontsize=8)
        ax_r.legend(title="RMS en la ventana del PEP", fontsize=8)
    fig.tight_layout()
    fig.savefig(cfg.DIR_RESULTADOS / f"comparacion_referencias_{cfg.NERVIO}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()