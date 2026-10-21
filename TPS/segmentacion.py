# segmentacion_pep.py
# Segmenta el EEG ya filtrado (el .fdt cargado y filtrado en
# preprocesamiento_pep.py) en épocas alrededor de cada estímulo, usando los
# tiempos (onset) del archivo de eventos .tsv.
#
# Uso desde main.py:
#     from segmentacion_pep import cargar_eventos, segmentar_epocas
#     eventos = cargar_eventos("EEG-Paciente1/sub-001_task-tibial_run-02_events.tsv")
#     epocas, tiempos = segmentar_epocas(eeg_filtrado, eventos)
#     # epocas: (n_epocas, n_canales, n_muestras) | tiempos: en segundos (0 = estímulo)

import numpy as np
import pandas as pd

# Ruta del archivo de eventos
RUTA_EVENTOS = "EEG-Paciente1/sub-001_task-tibial_run-02_events.tsv"

# Ventana alrededor del estímulo (segundos). Modificar según los componentes
# a estudiar (en PESS tibial: P37/P40, N45/N50, P60).
TMIN = -0.020
TMAX = 0.120


# Lee el archivo .tsv de eventos y deja solo los estímulos, ordenados por tiempo.
# El archivo tiene las columnas: onset, duration, trial_type, response_time,
# sample y value. Se usa trial_type == "stimulus" para quedarse con los estímulos.
def cargar_eventos(ruta_tsv=RUTA_EVENTOS):
    eventos = pd.read_csv(ruta_tsv, sep="\t", na_values=["n/a"])
    eventos = eventos[eventos["trial_type"] == "stimulus"]
    eventos = eventos.sort_values("onset").reset_index(drop=True)
    print(f"Eventos de estimulación leídos: {len(eventos)}")
    return eventos


# Segmenta el EEG filtrado en épocas alineadas al estímulo (tiempo 0 = estímulo).
# eeg_filtrado puede ser un objeto mne Raw o un array (n_canales, n_muestras);
# si es un array hay que pasar sfreq. Si baseline=True, a cada época se le resta
# la media del intervalo previo al estímulo (de tmin a 0).
# Devuelve las épocas (n_epocas, n_canales, n_muestras) y el vector de tiempos.
def segmentar_epocas(eeg_filtrado, eventos, sfreq=None, tmin=TMIN, tmax=TMAX,
                     baseline=True):
    # Obtener datos y frecuencia de muestreo real del EEG filtrado
    if hasattr(eeg_filtrado, "get_data"):
        datos = eeg_filtrado.get_data()
        sfreq = eeg_filtrado.info["sfreq"]
    else:
        datos = np.asarray(eeg_filtrado)
        if sfreq is None:
            raise ValueError("Si el EEG es un array hay que indicar sfreq.")

    # Convertir los onsets (segundos) a muestras
    muestras_estimulo = np.round(eventos["onset"].to_numpy() * sfreq).astype(int)

    # Posiciones relativas al estímulo dentro de la ventana
    desplazamientos = np.arange(int(round(tmin * sfreq)), int(round(tmax * sfreq)) + 1)
    tiempos = desplazamientos / sfreq

    # Descartar estímulos cuya ventana se sale del registro
    inicio = muestras_estimulo + desplazamientos[0]
    fin = muestras_estimulo + desplazamientos[-1]
    validos = (inicio >= 0) & (fin < datos.shape[1])
    if not validos.all():
        print(f"Aviso: {(~validos).sum()} estímulos descartados por salirse del registro.")
    muestras_estimulo = muestras_estimulo[validos]

    # Recortar todas las épocas: (n_canales, n_epocas, n_muestras) -> (n_epocas, n_canales, n_muestras)
    indices = muestras_estimulo[:, None] + desplazamientos[None, :]
    epocas = datos[:, indices].transpose(1, 0, 2)

    # Corrección de línea de base con el intervalo previo al estímulo
    if baseline:
        previo = tiempos < 0
        epocas = epocas - epocas[:, :, previo].mean(axis=2, keepdims=True)

    print(f"Épocas: {epocas.shape[0]} | canales: {epocas.shape[1]} | "
          f"muestras por época: {epocas.shape[2]} | sfreq: {sfreq:g} Hz")
    return epocas, tiempos


# Ejecución directa: solo lee y muestra los eventos (útil para revisar el archivo)
if __name__ == "__main__":
    eventos = cargar_eventos()
    print(eventos.head())