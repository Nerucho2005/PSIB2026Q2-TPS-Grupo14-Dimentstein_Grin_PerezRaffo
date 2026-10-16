#"""
#PASO 1 - Cargar y filtrar la señal, y compararla antes/después
#Requiere:  pip install mne pandas numpy matplotlib
#"""


from pathlib import Path

import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd

# =====================================================================
# PARÁMETROS DE FILTRADO
# =====================================================================
BASE = "sub-001_task-tibial_run-02"

ARTEFACTO = (-0.002, 0.006)    # ventana alrededor del estímulo que se interpola (s)
NOTCH = [50, 100, 150]         # red eléctrica (Argentina: 50 Hz) y armónicos
PASA_ALTO = 1.0                # Hz  (corta deriva lenta)
PASA_BAJO = 200.0              # Hz  (corta ruido de alta frecuencia)

# Qué canales mirar en los gráficos (ajustalo a los tuyos)
CANALES_VER = ["Cz", "Fz", "L1", "Knee1"]
DURACION_VENTANA = 10          # segundos que se ven por pantalla en la señal continua

# =====================================================================
# 1. CARGAR
# =====================================================================
try:
    aqui = Path(__file__).resolve().parent
except NameError:
    aqui = Path.cwd()

candidatas = [aqui / "EEG-Paciente1", aqui.parent / "EEG-Paciente1", Path.cwd() / "EEG-Paciente1"]
carpeta = next((c for c in candidatas if (c / f"{BASE}_eeg.set").exists()), None)
if carpeta is None:
    raise FileNotFoundError("No encontré el .set. Busqué en: " + ", ".join(map(str, candidatas)))

raw = mne.io.read_raw_eeglab(carpeta / f"{BASE}_eeg.set", preload=True)
print(raw.info)
print(f"Muestreo: {raw.info['sfreq']} Hz | Duración: {raw.times[-1]:.1f} s | Canales: {len(raw.ch_names)}")

# Verificar que los canales a mostrar existan
canales_ver = [c for c in CANALES_VER if c in raw.ch_names]
faltan = set(CANALES_VER) - set(canales_ver)
if faltan:
    print(f"Aviso: no existen estos canales: {sorted(faltan)}")
if not canales_ver:
    canales_ver = raw.ch_names[:4]
    print("Se muestran los primeros canales:", canales_ver)

# =====================================================================
# 2. EVENTOS (necesarios para localizar el artefacto del estímulo)
# =====================================================================
if len(raw.annotations) > 0:
    events, event_id = mne.events_from_annotations(raw)
else:
    df = pd.read_csv(carpeta / f"{BASE}_events.tsv", sep="\t")
    muestras = df["sample"].astype(int).to_numpy()
    events = np.column_stack([muestras, np.zeros_like(muestras), np.ones_like(muestras)])
    event_id = {"tibial": 1}
print(f"Estímulos: {len(events)}")

# Guardamos una copia sin filtrar para comparar
raw_cruda = raw.copy()

# =====================================================================
# 3. FILTRADO (en este orden)
# =====================================================================
# 3a. Artefacto del estímulo: se interpola ANTES de filtrar, para que el
#     filtro no lo "desparrame" por la señal.
raw = mne.preprocessing.fix_stim_artifact(
    raw, events=events, event_id=event_id,
    tmin=ARTEFACTO[0], tmax=ARTEFACTO[1], mode="linear",
)

# 3b. Notch: elimina la interferencia de la red eléctrica
raw.notch_filter(freqs=NOTCH)

# 3c. Pasa-banda: se queda solo con la banda de interés
raw.filter(l_freq=PASA_ALTO, h_freq=PASA_BAJO)

# =====================================================================
# 4. VISUALIZACIÓN
# =====================================================================
# 4a. Señal continua, filtrada (ventanas navegables con las flechas)
raw.copy().pick(canales_ver).plot(
    duration=DURACION_VENTANA, scalings="auto",
    title="Señal FILTRADA", show=False,
)
raw_cruda.copy().pick(canales_ver).plot(
    duration=DURACION_VENTANA, scalings="auto",
    title="Señal CRUDA (sin filtrar)", show=False,
)

# 4b. Zoom alrededor de un estímulo: cruda vs filtrada
sf = raw.info["sfreq"]
muestra_estimulo = events[len(events) // 2, 0]           # un estímulo del medio
ini = int(muestra_estimulo - 0.05 * sf)
fin = int(muestra_estimulo + 0.20 * sf)
tiempo_ms = (np.arange(ini, fin) - muestra_estimulo) / sf * 1000

fig, axes = plt.subplots(len(canales_ver), 1, figsize=(9, 2.4 * len(canales_ver)), sharex=True)
axes = np.atleast_1d(axes)
for ax, ch in zip(axes, canales_ver):
    ax.plot(tiempo_ms, raw_cruda.get_data(picks=ch, start=ini, stop=fin)[0] * 1e6,
            color="gray", lw=0.8, label="cruda")
    ax.plot(tiempo_ms, raw.get_data(picks=ch, start=ini, stop=fin)[0] * 1e6,
            color="C0", lw=1, label="filtrada")
    ax.axvspan(ARTEFACTO[0] * 1000, ARTEFACTO[1] * 1000, color="red", alpha=0.15)
    ax.axvline(0, color="r", ls="--", lw=0.8)
    ax.set_ylabel(f"{ch} (µV)")
    ax.grid(alpha=0.3)
axes[0].legend(loc="upper right")
axes[0].set_title("Un estímulo: cruda vs filtrada (zona roja = artefacto interpolado)")
axes[-1].set_xlabel("Tiempo respecto al estímulo (ms)")
fig.tight_layout()

# 4c. Espectro de potencia antes y después (¿desapareció el pico de 50 Hz?)
fig2, ax2 = plt.subplots(figsize=(9, 4))
for obj, color, nombre in [(raw_cruda, "gray", "cruda"), (raw, "C0", "filtrada")]:
    psd = obj.compute_psd(fmax=300, picks=canales_ver, verbose=False)
    pot, freqs = psd.get_data(return_freqs=True)
    ax2.semilogy(freqs, pot.mean(axis=0), color=color, label=nombre)
for f in NOTCH:
    ax2.axvline(f, color="r", ls=":", lw=0.8)
ax2.axvline(PASA_ALTO, color="g", ls=":", lw=0.8)
ax2.axvline(PASA_BAJO, color="g", ls=":", lw=0.8)
ax2.set_xlabel("Frecuencia (Hz)")
ax2.set_ylabel("Potencia (V²/Hz)")
ax2.set_title("Espectro promedio de los canales mostrados")
ax2.legend()
ax2.grid(alpha=0.3)
fig2.tight_layout()

plt.show()