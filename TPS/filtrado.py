# filtrado.py
# Carga, selección de canales, re-referencia, interpolación del artefacto de
# estímulo y filtrado (fase cero) del EEG continuo para PES (tibial y mediano).
#
# Referencia: el EEG del dataset está referido a la mastoides derecha (RM), que no
# figura como canal. Cada canal es V_canal - V_RM, así que la actividad que capte
# RM se resta de todos los canales. Opciones (parámetro `referencia`):
#   "RM" o None            -> la de adquisición, sin cambios.
#   "Fz", "FPz" o [lista]  -> se resta un canal o el promedio de varios.
#                             Montajes IFCN: tibial CPz-FPz, mediano CP3/CP4-Fz.
#   "mastoides_enlazadas"  -> (LM + RM)/2, simétrica. Como RM vale 0 en los datos,
#                             equivale a restar LM/2 a cada canal.
# La re-referencia necesita cargar también el/los canales de referencia, por eso
# se hace en cargar_y_referenciar, ANTES de quedarse solo con los canales de
# análisis. Como es una operación lineal, el orden respecto de la interpolación
# y el filtrado no cambia el resultado.
#   "promedio"             -> promedio de los 64 canales de EEG de cuero cabelludo
#                             (CANALES_EEG_CUERO; la que usa el paper del dataset).
#                             Excluye los no EEG (S.., SC.., Iz, L1, L4, AC, AL, ECG,
#                             EMG...). Cargar los 64 juntos ocuparía ~2 GB a 10 kHz,
#                             así que el promedio se calcula por tramos de tiempo
#                             (senal_referencia_promedio). RM no se suma (vale 0 y
#                             no es un canal): el factor 64/65 es despreciable.
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
# Artefacto de estimulación: el pulso del estimulador (0,2 ms) llega al cuero
# cabelludo por conducción de volumen. En este registro dura ~1,5 ms y mide
# ~70-85 µV en el promedio. Se reemplaza por una recta entre -1 y +3 ms de cada
# estímulo (interpolar_artefacto) ANTES de filtrar, para que el filtro de fase
# cero no lo disperse hacia la línea de base ni hacia la ventana del PEP.
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


MASTOIDES_ENLAZADAS = "mastoides_enlazadas"
PROMEDIO = "promedio"

# 64 canales de EEG de cuero cabelludo (Nierula et al. 2024, Métodos). LM incluida.
CANALES_EEG_CUERO = [
    "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "F7", "F8", "T7", "T8",
    "P7", "P8", "AFz", "Fz", "Cz", "Pz", "FC1", "FC2", "CP1", "CP2", "FC5", "FC6", "CP5",
    "CP6", "FT9", "FT10", "LM", "FCz", "F1", "F2", "C1", "C2", "P1", "P2", "AF3", "AF4",
    "FC3", "FC4", "CP3", "CP4", "PO3", "PO4", "F5", "F6", "C5", "C6", "P5", "P6", "AF7",
    "AF8", "FT7", "FT8", "TP7", "TP8", "PO7", "PO8", "FPz", "CPz", "F9", "F10"]


def canales_de_referencia(referencia):
    """Canales que hay que cargar para aplicar la referencia pedida."""
    if referencia in (None, "RM"):
        return []
    if referencia == MASTOIDES_ENLAZADAS:
        return ["LM"]
    if referencia == PROMEDIO:
        return list(CANALES_EEG_CUERO)
    return [referencia] if isinstance(referencia, str) else list(referencia)


def referenciar(datos, nombres, canales, referencia):
    """Re-referencia y devuelve SOLO los canales de análisis.
    datos: (n_canales_cargados, n_muestras) referidos a RM | nombres: sus nombres
    canales: canales de análisis | referencia: ver encabezado del módulo.
    Devuelve (len(canales), n_muestras)."""
    idx = {n.lower(): i for i, n in enumerate(nombres)}
    faltan = [c for c in list(canales) + canales_de_referencia(referencia)
              if c.lower() not in idx]
    if faltan:
        raise ValueError(f"Faltan canales para referenciar: {faltan}. Cargados: {list(nombres)}")
    sel = datos[[idx[c.lower()] for c in canales]]
    if referencia in (None, "RM"):
        return sel.copy()
    if referencia == MASTOIDES_ENLAZADAS:
        return sel - 0.5 * datos[idx["lm"]]
    ref = datos[[idx[r.lower()] for r in canales_de_referencia(referencia)]].mean(axis=0)
    return sel - ref


def nombre_referencia(referencia):
    """Etiqueta corta para títulos y nombres de archivo."""
    if referencia in (None, "RM"):
        return "RM"
    if referencia == MASTOIDES_ENLAZADAS:
        return "LMRM"
    if referencia == PROMEDIO:
        return "PROM"
    return "-".join(canales_de_referencia(referencia))


def senal_referencia_promedio(raw, canales=CANALES_EEG_CUERO, bloque_s=10.0):
    """Promedio de `canales` en cada instante, calculado por tramos de `bloque_s`
    segundos para no cargar todos los canales juntos en memoria.
    raw: Raw sin precargar (o precargado). Devuelve (n_muestras,) en V."""
    disponibles = {c.lower(): c for c in raw.ch_names}
    faltan = [c for c in canales if c.lower() not in disponibles]
    if faltan:
        raise ValueError(f"Faltan canales para la referencia promedio: {faltan}")
    picks = [disponibles[c.lower()] for c in canales]
    paso = int(bloque_s * raw.info["sfreq"])
    ref = np.empty(raw.n_times)
    for ini in range(0, raw.n_times, paso):
        fin = min(ini + paso, raw.n_times)
        ref[ini:fin] = raw.get_data(picks=picks, start=ini, stop=fin).mean(axis=0)
    return ref


def cargar_y_referenciar(registro, canales, referencia=None):
    """Carga solo los canales de análisis y los de referencia, re-referencia y
    devuelve un Raw (en memoria) con los canales de análisis y las anotaciones.
    registro: ruta a un .set, carpeta, o un mne.io.Raw ya abierto."""
    raw = registro if isinstance(registro, mne.io.BaseRaw) else cargar_eeg(registro)
    disponibles = {c.lower(): c for c in raw.ch_names}
    analisis = [disponibles[c.lower()] for c in canales if c.lower() in disponibles]
    if len(analisis) < len(canales):
        seleccionar_canales(raw, canales)          # avisa o falla con el mensaje de siempre
    if referencia == PROMEDIO:
        ref = senal_referencia_promedio(raw)
        sel = seleccionar_canales(raw, analisis)
        sel.load_data()
        datos = sel.get_data() - ref
    else:
        necesarios = list(dict.fromkeys(analisis + canales_de_referencia(referencia)))
        sel = seleccionar_canales(raw, necesarios)
        sel.load_data()
        datos = referenciar(sel.get_data(), sel.ch_names, analisis, referencia)
    info = sel.copy().pick(analisis).info
    nuevo = mne.io.RawArray(datos, info, verbose="ERROR")
    nuevo.set_annotations(sel.annotations)
    if referencia not in (None, "RM"):
        cr = canales_de_referencia(referencia)
        log.info("Referencia: %s (%s)", nombre_referencia(referencia),
                 f"{len(cr)} canales de cuero cabelludo" if referencia == PROMEDIO else cr)
    return nuevo


def interpolar_artefacto(datos, muestras_estimulo, fs, t_ini=-0.001, t_fin=0.003):
    """Reemplaza el artefacto de estimulación por una recta.
    Para cada estímulo, une con una recta la muestra en t_ini y la muestra en
    t_fin (relativos al estímulo, en s); las muestras intermedias se descartan.
    datos: (n_canales, n_muestras) | muestras_estimulo: índices de muestra.
    Devuelve una copia; se omiten estímulos cuya ventana se sale del registro."""
    if not t_ini < t_fin:
        raise ValueError(f"Se requiere t_ini < t_fin ({t_ini}, {t_fin}).")
    datos = np.array(datos, dtype=float, copy=True)
    i_ini, i_fin = int(round(t_ini * fs)), int(round(t_fin * fs))
    frac = np.linspace(0.0, 1.0, i_fin - i_ini + 1)          # 0 en n_a, 1 en n_b
    n_omitidos = 0
    for m in np.asarray(muestras_estimulo, dtype=int):
        a, b = m + i_ini, m + i_fin
        if a < 0 or b >= datos.shape[1]:
            n_omitidos += 1
            continue
        datos[:, a:b + 1] = datos[:, [a]] + (datos[:, [b]] - datos[:, [a]]) * frac
    if n_omitidos:
        warnings.warn(f"{n_omitidos} estímulos sin interpolar: su ventana se sale del registro.")
    return datos


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
                    f_notch=50.0, q_notch=30.0, graficar=False, ventana_grafico=(0.0, 5.0),
                    muestras_estimulo=None, t_artefacto=(-0.001, 0.003), referencia=None):
    # Selecciona canales, interpola el artefacto de estímulo y filtra el EEG continuo
    # (bandpass Butterworth + notch, fase cero).
    # registro: carpeta (se usa ARCHIVO_POR_DEFECTO), ruta a un .set, o un mne.io.Raw ya cargado.
    # f_notch=None desactiva el notch.
    # muestras_estimulo: índices de muestra de los estímulos; None no interpola.
    # t_artefacto: (t_ini, t_fin) en s respecto de cada estímulo.
    # referencia: "RM"/None (adquisición), "Fz", "FPz", lista de canales,
    # "mastoides_enlazadas" o "promedio".
    raw = registro if isinstance(registro, mne.io.BaseRaw) else cargar_eeg(registro)
    _informar(raw)
    if any("boundary" in d.lower() for d in raw.annotations.description):
        warnings.warn("El registro tiene discontinuidades ('boundary'); el filtrado las atraviesa.")

    # solo ahora se leen los datos, y solo de los canales de análisis y de referencia
    seleccion = cargar_y_referenciar(raw, canales or CANALES_POR_DEFECTO, referencia)
    fs = seleccion.info["sfreq"]
    if muestras_estimulo is not None:
        seleccion.apply_function(
            lambda x: interpolar_artefacto(x, muestras_estimulo, fs, *t_artefacto),
            channel_wise=False, verbose="ERROR")
        log.info("Artefacto interpolado en %d estímulos, de %.1f a %.1f ms.",
                 len(muestras_estimulo), t_artefacto[0] * 1e3, t_artefacto[1] * 1e3)
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
                      q_notch=q_notch, padlen=padlen,
                      t_artefacto=None if muestras_estimulo is None else t_artefacto,
                      referencia=nombre_referencia(referencia))
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