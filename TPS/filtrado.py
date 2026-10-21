# preprocesamiento_pep.py
# Carga, selección de canales y filtrado (fase cero) del EEG continuo para PESS del nervio tibial.
#
# Limitaciones del filtrado de fase cero (sosfiltfilt):
# - Es no causal: el artefacto de estimulación y las ondas rápidas generan oscilaciones
#   previas al estímulo (pre-ringing), que pueden contaminar una línea de base posterior.
# - Se filtra hacia adelante y atrás: la atenuación en las frecuencias de corte es el doble
#   (-6 dB en lugar de -3 dB) y el orden efectivo se duplica.
# - Los extremos del registro conservan un transitorio residual aunque se use extensión impar
#   (padlen); conviene no analizar épocas pegadas al inicio/fin del registro.
# - Si el registro tiene discontinuidades (eventos 'boundary' de EEGLAB), el filtro las atraviesa.
#
# Sobre el corte inferior de 5 Hz: en el PESS tibial el componente cortical principal (P37)
# dura ~10-20 ms, por lo que su energía se concentra por encima de ~15-20 Hz y un pasaaltos de
# 5 Hz lo preserva. Pero puede recortar componentes lentos posteriores (N45 y ondas tardías);
# si son de interés, comparar con 1-3 Hz.
from __future__ import annotations

import argparse
import logging
import warnings
from dataclasses import dataclass
from pathlib import Path

import mne
import numpy as np
from scipy.signal import butter, iirnotch, sosfiltfilt, tf2sos

log = logging.getLogger(__name__)

CANALES_POR_DEFECTO = ["Cz", "CPz"]  # añadir "Fz" o "Fpz" solo si el análisis lo requiere
ARCHIVO_POR_DEFECTO = "sub-001_task-tibial_run-02_eeg.set"  # el .fdt debe estar al lado


@dataclass
class ResultadoPreprocesamiento:
    raw: mne.io.BaseRaw   # EEG filtrado, solo canales seleccionados, con anotaciones
    sfreq: float          # frecuencia de muestreo (Hz)
    canales: list         # nombres de los canales conservados
    eventos: np.ndarray   # (n, 3): muestra, 0, id (de las anotaciones; vacío si no hay)
    event_id: dict        # descripción del evento -> id
    parametros: dict      # parámetros de filtrado usados


def cargar_eeg(ruta="EEG-Paciente1", archivo=ARCHIVO_POR_DEFECTO):
    # Abre un registro EEGLAB (.set + .fdt) sin cargar los datos en memoria.
    # `ruta` puede ser la carpeta que contiene `archivo` o la ruta directa al .set.
    ruta = Path(ruta)
    if ruta.is_dir():
        ruta = ruta / archivo
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe {ruta}. Si está en una subcarpeta, incluila en la ruta.")
    fdt = ruta.with_suffix(".fdt")
    if ruta.suffix.lower() == ".set" and not fdt.is_file():
        log.warning("No se encontró %s; si los datos no están dentro del .set, la carga fallará.", fdt.name)
    return mne.io.read_raw_eeglab(ruta, preload=False, verbose="ERROR")


def _informar(raw):
    log.info("fs=%.1f Hz | %d canales | %.1f s | ref. personalizada aplicada (código MNE): %s",
             raw.info["sfreq"], len(raw.ch_names), raw.times[-1], raw.info["custom_ref_applied"])
    log.info("Canales: %s", raw.ch_names)
    log.info("Eventos (%d anotaciones), tipos: %s", len(raw.annotations),
             sorted(set(raw.annotations.description)))


def seleccionar_canales(raw, canales):
    # Devuelve una copia con solo los canales pedidos (sin restar ni combinar).
    disponibles = {c.lower(): c for c in raw.ch_names}
    encontrados = [disponibles[c.lower()] for c in canales if c.lower() in disponibles]
    faltan = [c for c in canales if c.lower() not in disponibles]
    if faltan:
        msg = f"Canales no encontrados: {faltan}. Disponibles: {raw.ch_names}"
        if not encontrados:
            raise ValueError(msg)
        warnings.warn(msg)
    return raw.copy().pick(encontrados)


def _disenar_filtros(fs, f_bajo, f_alto, orden, f_notch, q_notch):
    nyq = fs / 2
    if not 0 < f_bajo < f_alto < nyq:
        raise ValueError(f"Cortes inválidos: se requiere 0 < {f_bajo} < {f_alto} < Nyquist ({nyq} Hz).")
    if f_notch is not None and not 0 < f_notch < nyq:
        raise ValueError(f"Notch inválido: {f_notch} Hz debe estar entre 0 y Nyquist ({nyq} Hz).")
    filtros = [butter(orden, [f_bajo, f_alto], btype="bandpass", fs=fs, output="sos")]
    if f_notch is not None:
        filtros.append(tf2sos(*iirnotch(f_notch, q_notch, fs=fs)))
    return filtros


def _filtrar(datos, filtros, padlen):
    for sos in filtros:
        datos = sosfiltfilt(sos, datos, axis=-1, padlen=padlen)  # extensión impar en los bordes
    return datos


def graficar_comparacion(crudo, filtrado, inicio_s=0.0, duracion_s=5.0):
    # Solo para verificar el filtrado: crudo vs. filtrado en un intervalo.
    import matplotlib.pyplot as plt

    fs = crudo.info["sfreq"]
    i0 = int(inicio_s * fs)
    i1 = min(int((inicio_s + duracion_s) * fs), crudo.n_times)
    t = np.arange(i0, i1) / fs
    n = len(filtrado.ch_names)
    fig, axs = plt.subplots(n, 1, sharex=True, squeeze=False, figsize=(10, 2.5 * n))
    for ax, ch in zip(axs[:, 0], filtrado.ch_names):
        ax.plot(t, crudo.get_data(picks=ch, start=i0, stop=i1)[0] * 1e6, lw=0.8, label="Crudo")
        ax.plot(t, filtrado.get_data(picks=ch, start=i0, stop=i1)[0] * 1e6, lw=0.8, label="Filtrado")
        ax.set_ylabel(f"{ch} (µV)")
    axs[0, 0].legend(loc="upper right")
    axs[-1, 0].set_xlabel("Tiempo (s)")
    fig.tight_layout()
    plt.show()


def preprocesar_eeg(registro="EEG-Paciente1", canales=None, f_bajo=5.0, f_alto=100.0, orden=4,
                    f_notch=50.0, q_notch=30.0, graficar=False, ventana_grafico=(0.0, 5.0)):
    # Selecciona canales y filtra el EEG continuo (bandpass Butterworth + notch, fase cero).
    # registro: carpeta (se usa ARCHIVO_POR_DEFECTO), ruta a un .set, o un mne.io.Raw ya cargado.
    # f_notch=None desactiva el notch.
    raw = registro if isinstance(registro, mne.io.BaseRaw) else cargar_eeg(registro)
    _informar(raw)
    if any("boundary" in d.lower() for d in raw.annotations.description):
        warnings.warn("El registro tiene discontinuidades ('boundary'); el filtrado las atraviesa.")

    seleccion = seleccionar_canales(raw, canales or CANALES_POR_DEFECTO)
    seleccion.load_data()  # solo ahora se leen los datos, y solo de los canales elegidos
    fs = seleccion.info["sfreq"]
    amp = np.median(np.abs(seleccion.get_data()), axis=1) * 1e6
    log.info("Amplitud mediana |x| (µV; MNE trabaja internamente en V): %s",
             dict(zip(seleccion.ch_names, np.round(amp, 1))))

    filtros = _disenar_filtros(fs, f_bajo, f_alto, orden, f_notch, q_notch)
    padlen = min(int(3 * fs / f_bajo), seleccion.n_times - 1)

    filtrado = seleccion.copy()
    filtrado.apply_function(lambda x: _filtrar(x, filtros, padlen), channel_wise=False, verbose="ERROR")

    if graficar:
        graficar_comparacion(seleccion, filtrado, *ventana_grafico)

    if len(filtrado.annotations):
        eventos, event_id = mne.events_from_annotations(filtrado, verbose="ERROR")
    else:
        eventos, event_id = np.empty((0, 3), dtype=int), {}

    parametros = dict(f_bajo=f_bajo, f_alto=f_alto, orden=orden, f_notch=f_notch,
                      q_notch=q_notch, padlen=padlen)
    return ResultadoPreprocesamiento(filtrado, fs, filtrado.ch_names, eventos, event_id, parametros)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="Preprocesamiento de EEG para PESS tibial.")
    p.add_argument("ruta", nargs="?", default="EEG-Paciente1",
                   help=f"Carpeta que contiene {ARCHIVO_POR_DEFECTO} o ruta directa a un .set")
    p.add_argument("--canales", nargs="+", default=CANALES_POR_DEFECTO)
    p.add_argument("--f-bajo", type=float, default=5.0)
    p.add_argument("--f-alto", type=float, default=100.0)
    p.add_argument("--orden", type=int, default=4)
    p.add_argument("--notch", type=float, default=50.0)
    p.add_argument("--graficar", action="store_true", help="Comparación crudo vs. filtrado")
    a = p.parse_args()
    res = preprocesar_eeg(a.ruta, a.canales, a.f_bajo, a.f_alto, a.orden, a.notch, graficar=a.graficar)
    log.info("Listo: %s | %d eventos | ids: %s", res.canales, len(res.eventos), res.event_id)