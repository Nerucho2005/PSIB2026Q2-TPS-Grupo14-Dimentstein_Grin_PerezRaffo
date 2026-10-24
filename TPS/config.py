# config.py
# Parámetros compartidos del pipeline del PEP tibial.
# Es el único archivo común a todos: cambiarlo solo con un PR que vea el grupo.
from pathlib import Path

# ---- Rutas ----
RAIZ = Path(__file__).resolve().parent.parent      # raíz del repo (config.py está en TPS/)
DIR_DATOS = RAIZ / "EEG-Paciente1"                 # datos, fuera de git
DIR_RESULTADOS = RAIZ / "results"                  # figuras
BASE = "sub-001_task-tibial_run-02"                # prefijo BIDS del run
ARCHIVO_EEG = DIR_DATOS / f"{BASE}_eeg.set"        # el .fdt debe estar al lado
ARCHIVO_EVENTOS = DIR_DATOS / f"{BASE}_events.tsv"

# ---- Canales ----
CANALES = ["Cz", "CPz"]

# ---- Filtrado (Butterworth pasabanda + notch, fase cero) ----
F_BAJO = 5.0      # Hz
F_ALTO = 100.0    # Hz
ORDEN = 4
F_NOTCH = 50.0    # Hz (None desactiva el notch)
Q_NOTCH = 30.0

# ---- Segmentación ----
TMIN = -0.020     # s, inicio de la época respecto del estímulo
TMAX = 0.120      # s, fin de la época

# ---- Promedios y SNR ----
VENTANA_SENAL = (0.015, 0.080)   # s, donde está el PEP (P37/P40, N45)
TAM_BLOQUE = 50                  # épocas por bloque para estimar amplitudes
N_VALORES = [10, 25, 50, 100, 200, 400]   # N para la curva SNR vs. N (M se agrega solo)
N_REP = 20                       # repeticiones por N en la curva
