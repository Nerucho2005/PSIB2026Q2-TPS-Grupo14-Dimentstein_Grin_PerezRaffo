# segmentacion.py
# Etapa 3 del pipeline: lectura de los estímulos y segmentación del EEG filtrado en
# épocas alineadas al estímulo (t = 0).
#
# Los tiempos de cada estímulo salen del archivo de eventos BIDS (_events.tsv), que
# tiene las columnas onset (s), duration, trial_type, response_time, sample y value.
# Cada época va de tmin a tmax respecto del estímulo y se le resta la media del
# pre-estímulo (corrección de línea de base). Las épocas se devuelven EN ORDEN
# TEMPORAL, que necesitan el promedio alternado (snr.py) y los bloques de amplitud
# (promedio.py).
import numpy as np
import pandas as pd


def cargar_eventos(ruta_tsv):
    """Lee el _events.tsv y deja solo los estímulos (trial_type == "stimulus"),
    ordenados por tiempo. Devuelve un DataFrame (con las columnas onset y sample)."""
    eventos = pd.read_csv(ruta_tsv, sep="\t", na_values=["n/a"])
    eventos = eventos[eventos["trial_type"] == "stimulus"]
    eventos = eventos.sort_values("onset").reset_index(drop=True)
    print(f"Eventos de estimulación leídos: {len(eventos)}")
    return eventos


def segmentar_epocas(eeg_filtrado, eventos, tmin, tmax, sfreq=None, baseline=True):
    """Recorta una época por estímulo, de tmin a tmax (s).
    eeg_filtrado: Raw de MNE o array (n_canales, n_muestras); si es un array hay que
    pasar sfreq. Si baseline=True, a cada época se le resta la media de tmin a 0.
    Se descartan los estímulos cuya ventana se sale del registro.
    Devuelve (epocas, tiempos): epocas (n_epocas, n_canales, n_muestras) en V y
    tiempos (n_muestras,) en s, con 0 = estímulo."""
    # Datos y frecuencia de muestreo
    if hasattr(eeg_filtrado, "get_data"):
        datos = eeg_filtrado.get_data()
        sfreq = eeg_filtrado.info["sfreq"]
    else:
        datos = np.asarray(eeg_filtrado)
        if sfreq is None:
            raise ValueError("Si el EEG es un array hay que indicar sfreq.")

    # Onsets (s) -> índices de muestra, y desplazamientos de la ventana
    muestras_estimulo = np.round(eventos["onset"].to_numpy() * sfreq).astype(int)
    desplazamientos = np.arange(int(round(tmin * sfreq)), int(round(tmax * sfreq)) + 1)
    tiempos = desplazamientos / sfreq

    # Estímulos cuya ventana entra completa en el registro
    validos = ((muestras_estimulo + desplazamientos[0] >= 0)
               & (muestras_estimulo + desplazamientos[-1] < datos.shape[1]))
    if not validos.all():
        print(f"Aviso: {(~validos).sum()} estímulos descartados por salirse del registro.")
    muestras_estimulo = muestras_estimulo[validos]

    # Recorte vectorizado: (n_canales, n_epocas, n_muestras) -> (n_epocas, n_canales, n_muestras)
    indices = muestras_estimulo[:, None] + desplazamientos[None, :]
    epocas = datos[:, indices].transpose(1, 0, 2)

    # Corrección de línea de base con el pre-estímulo
    if baseline:
        epocas = epocas - epocas[:, :, tiempos < 0].mean(axis=2, keepdims=True)

    print(f"Épocas: {epocas.shape[0]} | canales: {epocas.shape[1]} | "
          f"muestras por época: {epocas.shape[2]} | fs: {sfreq:g} Hz")
    return epocas, tiempos
