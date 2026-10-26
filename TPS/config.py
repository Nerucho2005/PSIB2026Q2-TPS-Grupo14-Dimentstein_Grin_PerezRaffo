# config.py
# Parámetros compartidos del pipeline del PEP tibial.
# Es el único archivo común a todos: cambiarlo solo con un PR que vea el grupo.
from pathlib import Path

# ---- Rutas ----
RAIZ = Path(__file__).resolve().parent.parent      # raíz del repo (config.py está en TPS/)
DIR_DATOS = RAIZ / "EEG-Paciente1"                 # datos, fuera de git
DIR_RESULTADOS = RAIZ / "results"                  # figuras
NERVIO = "mediano"                                  # "tibial" o "mediano"
SUJETO = "001"
RUN = {"tibial": "02", "mediano": "03"}[NERVIO]    # run a analizar de cada nervio
TAREA = {"tibial": "tibial", "mediano": "median"}[NERVIO]
BASE = f"sub-{SUJETO}_task-{TAREA}_run-{RUN}"      # prefijo BIDS del run
ARCHIVO_EEG = DIR_DATOS / f"{BASE}_eeg.set"        # el .fdt debe estar al lado
ARCHIVO_EVENTOS = DIR_DATOS / f"{BASE}_events.tsv"

# ---- Canales (referencia de adquisición: mastoides derecha, RM) ----
# Mediano: CP3/CP4 ~ C3'/C4'. El N20 aparece solo en el CONTRALATERAL al brazo
# estimulado; se dejan los dos para identificar el lado.
CANALES = {"tibial": ["Cz", "CPz"], "mediano": ["CP3", "CP4"]}[NERVIO]

# ---- Artefacto de estimulación (se interpola ANTES de filtrar) ----
INTERPOLAR_ARTEFACTO = True
T_ARTEFACTO = (-0.001, 0.003)    # s respecto del estímulo; el artefacto dura ~1,5 ms

# ---- Filtrado (Butterworth pasabanda + notch, fase cero) ----
F_BAJO = 5.0      # Hz
F_ALTO = 100.0    # Hz
ORDEN = 4
F_NOTCH = 50.0    # Hz (None desactiva el notch)
Q_NOTCH = 30.0

# ---- Segmentación ----
TMIN = -0.020                                          # s, inicio de la época
TMAX = {"tibial": 0.120, "mediano": 0.080}[NERVIO]     # s, fin de la época

# ---- Promedios y SNR ----
VENTANA_SENAL = {"tibial": (0.015, 0.080),     # s, donde está el PEP: P40...N75
                 "mediano": (0.012, 0.060)}[NERVIO]   # N20...P45
TAM_BLOQUE = 50                  # épocas por bloque para estimar amplitudes
N_VALORES = [10, 25, 50, 100, 200, 400]   # N para la curva SNR vs. N (M se agrega solo)
N_REP = 20                       # repeticiones por N en la curva