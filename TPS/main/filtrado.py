# filtrado.py
# Etapas 1 y 2 del pipeline: carga del registro, re-referencia, interpolación del
# artefacto de estímulo y filtrado de fase cero del EEG continuo.
#
# REFERENCIA
# El EEG del dataset está referido a la mastoides derecha (RM), que no figura como
# canal: cada canal es V_canal - V_RM. Re-referenciar es restar otra señal a cada
# canal. Opciones (parámetro `referencia`):
#   "RM" o None            -> la de adquisición, sin cambios.
#   "Fz" o [lista]         -> se resta un canal o el promedio de varios.
#                             Montaje IFCN del mediano: Pc-Fz (CP4-Fz), el elegido.
#   "mastoides_enlazadas"  -> (LM + RM)/2, simétrica. Como RM vale 0 en los datos,
#                             equivale a restar LM/2. Se usa para la lateralidad.
#   "promedio"             -> promedio de los 64 canales de EEG de cuero cabelludo
#                             (la referencia del paper del dataset). Se calcula por
#                             tramos de tiempo para no cargar los 64 canales juntos
#                             (~2 GB a 10 kHz).
# Para re-referenciar hay que cargar también los canales de referencia, por eso se
# hace en cargar_y_referenciar ANTES de quedarse solo con los canales de análisis.
# Es una operación lineal: su orden respecto de la interpolación y el filtrado no
# cambia el resultado.
#
# ARTEFACTO DE ESTIMULACIÓN
# El pulso eléctrico (0,2 ms) llega al cuero cabelludo por conducción de volumen y
# aparece en t = 0 en todas las épocas (~50 µV, ~1,5 ms). Como está sincronizado con
# el estímulo, el promediado no lo atenúa. Se reemplaza por una recta entre -1 y
# +3 ms de cada estímulo (interpolar_artefacto) ANTES de filtrar: si se filtrara
# primero, el filtro de fase cero lo dispersaría hacia la línea de base y el PEP.
#
# FILTRADO: Butterworth pasabanda 30-400 Hz (orden 4) + notch de 50 Hz, ambos con
# sosfiltfilt (fase cero), igual que el paper del dataset (Nierula et al. 2024).
#   - Fase cero: la señal se filtra hacia adelante y hacia atrás, así que no hay
#     desfasaje y las latencias de los picos no se corren (requisito del trabajo).
#     Como contrapartida, la atenuación en los cortes es el doble (-6 dB) y el
#     filtro es no causal (puede oscilar antes de un transitorio brusco: por eso se
#     interpola el artefacto antes).
#   - El complejo N20-P25 es rápido (~5 ms entre picos) y su energía está por encima
#     de ~30 Hz; la mayor parte del EEG de fondo (alfa, deriva) está por debajo.
#   - Los extremos del registro conservan un transitorio aunque se use extensión
#     impar (padlen); los estímulos están lejos de los bordes.
from dataclasses import dataclass
from pathlib import Path
import logging
import warnings

import mne
import numpy as np
from scipy.signal import butter, iirnotch, sosfiltfilt, tf2sos

log = logging.getLogger(__name__)

MASTOIDES_ENLAZADAS = "mastoides_enlazadas"
PROMEDIO = "promedio"

# 64 canales de EEG de cuero cabelludo (Nierula et al. 2024, Métodos), sin los
# electrodos espinales (S.., SC.., L1, L4, AC, AL), Iz ni ECG/EMG. LM incluida.
CANALES_EEG_CUERO = [
    "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "F7", "F8", "T7", "T8",
    "P7", "P8", "AFz", "Fz", "Cz", "Pz", "FC1", "FC2", "CP1", "CP2", "FC5", "FC6", "CP5",
    "CP6", "FT9", "FT10", "LM", "FCz", "F1", "F2", "C1", "C2", "P1", "P2", "AF3", "AF4",
    "FC3", "FC4", "CP3", "CP4", "PO3", "PO4", "F5", "F6", "C5", "C6", "P5", "P6", "AF7",
    "AF8", "FT7", "FT8", "TP7", "TP8", "PO7", "PO8", "FPz", "CPz", "F9", "F10"]


@dataclass
class ResultadoPreprocesamiento:
    raw: mne.io.BaseRaw   # EEG filtrado, solo los canales de análisis
    sfreq: float          # frecuencia de muestreo (Hz)
    canales: list         # nombres de los canales conservados
    parametros: dict      # parámetros usados (filtro, artefacto, referencia)


# --------------------------------------------------------------------------
# Carga y selección de canales
# --------------------------------------------------------------------------
def cargar_eeg(ruta_set):
    """Abre un registro EEGLAB (.set + .fdt) SIN cargar los datos en memoria: la
    señal se lee recién cuando se piden canales concretos."""
    ruta_set = Path(ruta_set)
    if not ruta_set.is_file():
        raise FileNotFoundError(f"No existe {ruta_set}.")
    if not ruta_set.with_suffix(".fdt").is_file():
        log.warning("No se encontró %s: el .fdt tiene que estar al lado del .set.",
                    ruta_set.with_suffix(".fdt").name)
    return mne.io.read_raw_eeglab(ruta_set, preload=False, verbose="ERROR")


def seleccionar_canales(raw, canales):
    """Copia del registro con solo los canales pedidos (sin distinguir mayúsculas)."""
    disponibles = {c.lower(): c for c in raw.ch_names}
    encontrados = [disponibles[c.lower()] for c in canales if c.lower() in disponibles]
    faltan = [c for c in canales if c.lower() not in disponibles]
    if faltan:
        msg = f"Canales no encontrados: {faltan}. Disponibles: {raw.ch_names}"
        if not encontrados:
            raise ValueError(msg)
        warnings.warn(msg)
    return raw.copy().pick(encontrados)


# --------------------------------------------------------------------------
# Re-referencia
# --------------------------------------------------------------------------
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
    datos: (n_canales_cargados, n_muestras) referidos a RM; nombres: sus nombres;
    canales: canales de análisis. Devuelve (len(canales), n_muestras)."""
    idx = {n.lower(): i for i, n in enumerate(nombres)}
    faltan = [c for c in list(canales) + canales_de_referencia(referencia) if c.lower() not in idx]
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
    """Etiqueta corta de la referencia, para títulos y nombres de archivo."""
    if referencia in (None, "RM"):
        return "RM"
    if referencia == MASTOIDES_ENLAZADAS:
        return "LMRM"
    if referencia == PROMEDIO:
        return "PROM"
    return "-".join(canales_de_referencia(referencia))


def senal_referencia_promedio(raw, canales=CANALES_EEG_CUERO, bloque_s=10.0):
    """Promedio de `canales` en cada instante, calculado por tramos de `bloque_s`
    segundos para no cargar todos los canales juntos. Devuelve (n_muestras,) en V."""
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
    """Lee solo los canales de análisis y los de referencia, re-referencia y devuelve
    un Raw en memoria con los canales de análisis.
    registro: ruta al .set o un mne.io.Raw ya abierto."""
    raw = registro if isinstance(registro, mne.io.BaseRaw) else cargar_eeg(registro)
    disponibles = {c.lower(): c for c in raw.ch_names}
    analisis = [disponibles[c.lower()] for c in canales if c.lower() in disponibles]
    if len(analisis) < len(canales):
        seleccionar_canales(raw, canales)          # avisa o falla con un mensaje claro
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
    nuevo = mne.io.RawArray(datos, sel.copy().pick(analisis).info, verbose="ERROR")
    nuevo.set_annotations(sel.annotations)
    log.info("Referencia: %s", nombre_referencia(referencia))
    return nuevo


# --------------------------------------------------------------------------
# Artefacto de estimulación
# --------------------------------------------------------------------------
def interpolar_artefacto(datos, muestras_estimulo, fs, t_ini=-0.001, t_fin=0.003):
    """Para cada estímulo, reemplaza las muestras entre t_ini y t_fin (s, relativos al
    estímulo) por la recta que une la muestra en t_ini con la muestra en t_fin.
    datos: (n_canales, n_muestras); muestras_estimulo: índices de muestra.
    Devuelve una copia."""
    if not t_ini < t_fin:
        raise ValueError(f"Se requiere t_ini < t_fin ({t_ini}, {t_fin}).")
    datos = np.array(datos, dtype=float, copy=True)
    i_ini, i_fin = int(round(t_ini * fs)), int(round(t_fin * fs))
    frac = np.linspace(0.0, 1.0, i_fin - i_ini + 1)          # 0 en el inicio, 1 en el fin
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


# --------------------------------------------------------------------------
# Filtrado
# --------------------------------------------------------------------------
def disenar_filtros(fs, f_bajo, f_alto, orden, f_notch, q_notch):
    """Butterworth pasabanda y notch en secciones de segundo orden (SOS, numéricamente
    estables a 10 kHz). f_notch=None omite el notch. Devuelve una lista de SOS."""
    nyq = fs / 2
    if not 0 < f_bajo < f_alto < nyq:
        raise ValueError(f"Cortes inválidos: se requiere 0 < {f_bajo} < {f_alto} < {nyq} Hz.")
    filtros = [butter(orden, [f_bajo, f_alto], btype="bandpass", fs=fs, output="sos")]
    if f_notch is not None:
        if not 0 < f_notch < nyq:
            raise ValueError(f"Notch inválido: {f_notch} Hz.")
        filtros.append(tf2sos(*iirnotch(f_notch, q_notch, fs=fs)))
    return filtros


def filtrar(datos, filtros, padlen):
    """Aplica cada filtro con sosfiltfilt (fase cero) sobre el último eje."""
    for sos in filtros:
        datos = sosfiltfilt(sos, datos, axis=-1, padlen=padlen)
    return datos


def padlen_de(fs, f_bajo, n_muestras):
    """Extensión de los bordes: ~3 períodos del corte inferior."""
    return min(int(3 * fs / f_bajo), n_muestras - 1)


# --------------------------------------------------------------------------
# Función principal de la etapa
# --------------------------------------------------------------------------
def preprocesar_eeg(registro, canales, f_bajo, f_alto, orden, f_notch, q_notch,
                    muestras_estimulo=None, t_artefacto=(-0.001, 0.003), referencia=None):
    """Carga + re-referencia + interpolación del artefacto + filtrado.
    registro: ruta al .set o Raw abierto | canales: canales de análisis
    muestras_estimulo: índices de los estímulos (None: no se interpola)
    Devuelve un ResultadoPreprocesamiento con el Raw filtrado."""
    raw = registro if isinstance(registro, mne.io.BaseRaw) else cargar_eeg(registro)
    log.info("Registro: fs = %.0f Hz | %d canales | %.1f s", raw.info["sfreq"],
             len(raw.ch_names), raw.times[-1])

    # 1. Solo ahora se leen datos, y solo de los canales de análisis y de referencia
    sel = cargar_y_referenciar(raw, canales, referencia)
    fs = sel.info["sfreq"]

    # 2. Interpolación del artefacto, sobre la señal sin filtrar
    if muestras_estimulo is not None:
        sel.apply_function(lambda x: interpolar_artefacto(x, muestras_estimulo, fs, *t_artefacto),
                           channel_wise=False, verbose="ERROR")
        log.info("Artefacto interpolado en %d estímulos (%.0f a %.0f ms).",
                 len(muestras_estimulo), t_artefacto[0] * 1e3, t_artefacto[1] * 1e3)

    # 3. Filtrado de fase cero
    filtros = disenar_filtros(fs, f_bajo, f_alto, orden, f_notch, q_notch)
    padlen = padlen_de(fs, f_bajo, sel.n_times)
    sel.apply_function(lambda x: filtrar(x, filtros, padlen), channel_wise=False, verbose="ERROR")

    parametros = dict(f_bajo=f_bajo, f_alto=f_alto, orden=orden, f_notch=f_notch,
                      q_notch=q_notch, padlen=padlen,
                      t_artefacto=None if muestras_estimulo is None else t_artefacto,
                      referencia=nombre_referencia(referencia))
    return ResultadoPreprocesamiento(sel, fs, sel.ch_names, parametros)
