# comparar_pasaaltos.py
# Compara distintas frecuencias de corte del pasaaltos para justificar la elección.
#
# El filtrado es de fase cero (sosfiltfilt), así que cambiar el corte NO desfasa la
# señal: solo cambia qué frecuencias pasan. Un corte menor conserva componentes
# lentos del PEP (forma y amplitud más fieles) pero deja pasar más EEG de fondo de
# baja frecuencia (más ruido). Para cada corte se reportan:
#   - el PEP (promedio homogéneo) superpuesto, por canal,
#   - latencias y amplitudes de los componentes (teoria.py),
#   - la SNR del promedio homogéneo y del inhomogéneo "n".
#
# El registro se carga e interpola una sola vez; solo se repite el filtrado.
# Ejecutar desde la raíz del repo:   python TPS/comparar_pasaaltos.py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
from filtrado import (_disenar_filtros, _filtrar, cargar_eeg, interpolar_artefacto,
                      seleccionar_canales)
from segmentacion import cargar_eventos, segmentar_epocas
from snr import calcular_snr, pesos_homogeneos
from promedio import promedio_homogeneo, promedio_inhomogeneo
from teoria import comparar_con_teoria, componentes_de

CORTES = [0.5, 1.0, 2.0, 5.0]   # Hz; el actual es cfg.F_BAJO


def main():
    raw = seleccionar_canales(cargar_eeg(cfg.ARCHIVO_EEG), cfg.CANALES)
    raw.load_data()
    fs, canales = raw.info["sfreq"], raw.ch_names
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int)
    datos = raw.get_data()
    if cfg.INTERPOLAR_ARTEFACTO:
        datos = interpolar_artefacto(datos, muestras, fs, *cfg.T_ARTEFACTO)

    pes, filas = {}, []
    for f_bajo in CORTES:
        filtros = _disenar_filtros(fs, f_bajo, cfg.F_ALTO, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH)
        padlen = min(int(3 * fs / f_bajo), datos.shape[1] - 1)
        epocas, t = segmentar_epocas(_filtrar(datos, filtros, padlen), eventos, sfreq=fs,
                                     tmin=cfg.TMIN, tmax=cfg.TMAX)

        pe = promedio_homogeneo(epocas)
        snr_h = calcular_snr(epocas, pe, pesos_homogeneos(epocas), t, cfg.VENTANA_SENAL)
        pe_n, w_n = promedio_inhomogeneo(epocas, "n", t, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
        snr_n = calcular_snr(epocas, pe_n, w_n, t, cfg.VENTANA_SENAL)
        pes[f_bajo] = pe

        comp = comparar_con_teoria(t, pe, canales, cfg.NERVIO).set_index(["canal", "componente"])
        for i, canal in enumerate(canales):
            fila = {"corte_Hz": f_bajo, "canal": canal,
                    "SNR_homog_dB": snr_h["snr_db"][i], "SNR_n_dB": snr_n["snr_db"][i],
                    "ruido_rms_uV": snr_h["rms_ruido"][i] * 1e6}
            for nombre in list(componentes_de(cfg.NERVIO))[:2]:
                fila[f"{nombre}_lat_ms"] = comp.loc[(canal, nombre), "lat_ms"]
                fila[f"{nombre}_amp_uV"] = comp.loc[(canal, nombre), "amp_uV"]
            pp = [c for c in comp.loc[canal].index if "pico a pico" in c][0]
            fila["pico_a_pico_uV"] = comp.loc[(canal, pp), "amp_uV"]
            filas.append(fila)

    tabla = pd.DataFrame(filas).sort_values(["canal", "corte_Hz"])
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(f"\nComparación de pasaaltos (pasabajos fijo en {cfg.F_ALTO:g} Hz)")
        print(tabla.round(2).to_string(index=False))
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)
    tabla.to_csv(cfg.DIR_RESULTADOS / f"comparacion_pasaaltos_{cfg.NERVIO}.csv", index=False)

    t_ms = t * 1e3
    colores = plt.cm.viridis(np.linspace(0, 0.85, len(CORTES)))
    fig, axs = plt.subplots(1, len(canales), figsize=(6.5 * len(canales), 4), squeeze=False)
    for i, (ax, canal) in enumerate(zip(axs[0], canales)):
        for f_bajo, color in zip(CORTES, colores):
            ax.plot(t_ms, pes[f_bajo][i] * 1e6, color=color, lw=1.2,
                    label=f"{f_bajo:g}–{cfg.F_ALTO:g} Hz")
        ax.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.93", zorder=0)
        ax.axvline(0, color="k", lw=0.5)
        ax.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
               title=f"PEP {cfg.NERVIO} — {canal}: efecto del pasaaltos")
        ax.legend(title="Banda")
    fig.tight_layout()
    fig.savefig(cfg.DIR_RESULTADOS / f"comparacion_pasaaltos_{cfg.NERVIO}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()
