# comparar_filtros.py
# Compara bandas de filtrado para justificar la elegida (config.F_BAJO-F_ALTO).
#
# Bandas comparadas (todas Butterworth de orden 4, fase cero, + notch de 50 Hz):
#   IFCN      1-2000 Hz  guía clínica (Mauguière et al. 1999): pasaaltos < 3 Hz y
#                        pasabajos > 2000 Hz registran "todos los componentes sin
#                        distorsión"; el filtrado digital posterior permite "seleccionar
#                        off-line las frecuencias de interés clínico".
#   Anterior  5-100 Hz   la que se usaba en este trabajo antes del cambio de objetivo.
#   Paper     30-400 Hz  la del EEG cortical de Nierula et al. (2024): elegida.
#
# El filtro es de fase cero (sosfiltfilt), así que cambiar la banda NO desfasa la señal:
# solo cambia qué frecuencias pasan. Una banda más ancha conserva la forma del PEP pero
# deja pasar más EEG de fondo (más ruido). Para cada banda se reportan:
#   - el PEP (promedio homogéneo) superpuesto,
#   - latencias del N20 y del P25 y amplitud pico a pico N20-P25 (teoria.py),
#   - la SNR principal (promedio alternado) del homogéneo y del inhomogéneo "n",
#   - la SNR estilo paper (RMS ±1 ms alrededor del N20 / RMS pre-estímulo).
#
# El registro se carga, re-referencia e interpola una sola vez; solo se repite el filtrado.
# Ejecutar desde la raíz del repo:   python TPS/comparar_filtros.py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
from filtrado import _disenar_filtros, _filtrar, cargar_y_referenciar, interpolar_artefacto
from promedio import promedio_homogeneo, promedio_inhomogeneo
from segmentacion import cargar_eventos, segmentar_epocas
from snr import calcular_snr, pesos_homogeneos, snr_paper
from teoria import comparar_con_teoria

BANDAS = {"IFCN": (1.0, 2000.0), "Anterior": (5.0, 100.0), "Paper": (30.0, 400.0)}


def cargar_interpolado():
    """Registro re-referenciado e interpolado (sin filtrar), una sola vez."""
    raw = cargar_y_referenciar(cfg.ARCHIVO_EEG, cfg.CANALES, cfg.REFERENCIA)
    fs = raw.info["sfreq"]
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int)
    datos = raw.get_data()
    if cfg.INTERPOLAR_ARTEFACTO:
        datos = interpolar_artefacto(datos, muestras, fs, *cfg.T_ARTEFACTO)
    return datos, fs, eventos


def analizar_banda(datos, fs, eventos, f_bajo, f_alto):
    """PEP y métricas con una banda. Devuelve (t, pe, fila de la tabla)."""
    filtros = _disenar_filtros(fs, f_bajo, f_alto, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH)
    padlen = min(int(3 * fs / f_bajo), datos.shape[1] - 1)
    epocas, t = segmentar_epocas(_filtrar(datos, filtros, padlen), eventos, sfreq=fs,
                                 tmin=cfg.TMIN, tmax=cfg.TMAX)
    pe = promedio_homogeneo(epocas)
    snr_h = calcular_snr(epocas, pe, pesos_homogeneos(epocas), t, cfg.VENTANA_SENAL)
    pe_n, w_n = promedio_inhomogeneo(epocas, "n", t, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
    snr_n = calcular_snr(epocas, pe_n, w_n, t, cfg.VENTANA_SENAL)
    comp = comparar_con_teoria(t, pe, cfg.CANALES).set_index("componente")
    n20 = comp.loc["N20"]
    lat = n20["lat_ms"] / 1e3 if n20["valido"] else np.nan
    sp = snr_paper(pe, t, lat, cfg.SEMIANCHO_SNR_PAPER)
    fila = {"banda_Hz": f"{f_bajo:g}-{f_alto:g}",
            "SNR_homog_dB": snr_h["snr_db"][0], "SNR_n_dB": snr_n["snr_db"][0],
            "ganancia_n_dB": snr_n["snr_db"][0] - snr_h["snr_db"][0],
            "SNR_paper_dB": sp["snr_db"][0], "ruido_rms_uV": snr_h["rms_ruido"][0] * 1e6,
            "N20_lat_ms": n20["lat_ms"], "N20_valido": bool(n20["valido"]),
            "P25_lat_ms": comp.loc["P25", "lat_ms"],
            "N20_P25_pp_uV": comp.loc["N20-P25 (pico a pico)", "amp_uV"]}
    return t, pe[0], fila


def main():
    datos, fs, eventos = cargar_interpolado()
    pes, filas = {}, []
    for nombre, (f_bajo, f_alto) in BANDAS.items():
        t, pe, fila = analizar_banda(datos, fs, eventos, f_bajo, f_alto)
        pes[nombre] = pe
        filas.append({"banda": nombre, **fila})

    tabla = pd.DataFrame(filas)
    with pd.option_context("display.width", 180, "display.max_columns", 20):
        print(f"\nComparación de bandas — {cfg.CANAL}–{cfg.REFERENCIA}, M = {len(eventos)}")
        print(tabla.round(2).to_string(index=False))
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)
    tabla.to_csv(cfg.DIR_RESULTADOS / "comparacion_filtros.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 4))
    for (nombre, pe), color in zip(pes.items(), ["0.55", "#1f77b4", "#d62728"]):
        f_bajo, f_alto = BANDAS[nombre]
        ax.plot(t * 1e3, pe * 1e6, color=color, lw=1.2, label=f"{nombre} ({f_bajo:g}–{f_alto:g} Hz)")
    ax.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.93", zorder=0)
    ax.axvline(0, color="k", lw=0.5)
    ax.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
           title=f"PEP del mediano — {cfg.CANAL}–{cfg.REFERENCIA}: efecto de la banda de filtrado")
    ax.legend()
    fig.tight_layout()
    fig.savefig(cfg.DIR_RESULTADOS / "comparacion_filtros.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()
