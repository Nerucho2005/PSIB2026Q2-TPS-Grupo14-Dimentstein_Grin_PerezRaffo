# PSIB2026Q2 · TPS Grupo 14 · Dimentstein, Grin, Pérez Raffo

**Potenciales evocados somatosensoriales (PES) del nervio mediano: mejora de la relación señal/ruido según el tipo de promediado y la cantidad de épocas.**

Este repositorio contiene el pipeline de análisis y una **interfaz gráfica** que permite analizar cualquiera de los 40 sujetos del dataset OpenNeuro ds004388 sin editar código. La primera parte de este README explica cómo instalar todo y cómo usar la interfaz; la segunda parte (*Documentación técnica*) describe el proyecto en detalle.

---

# Guía de instalación y uso

## A. Requisitos

| Requisito | Detalle |
|---|---|
| Sistema operativo | Windows 10/11 (probado), también Linux o macOS |
| Python | **3.10 o superior** (64 bits). Se descarga de [python.org](https://www.python.org/downloads/); en el instalador de Windows, tildar **"Add python.exe to PATH"** |
| Git | Para clonar el repositorio ([git-scm.com](https://git-scm.com/)). También se puede descargar el ZIP desde GitHub |
| curl | Lo usa la interfaz para descargar los datos. Viene instalado en Windows 10/11, Linux y macOS |
| Espacio en disco | ~1,8 GB por sujeto descargado, más ~1 GB de margen. Los resultados guardados ocupan unos MB por sujeto |
| Memoria RAM | 8 GB recomendados |
| Conexión a internet | Solo para descargar los registros la primera vez |

Para verificar que Python y curl están disponibles, abrir **CMD** (tecla Windows → escribir `cmd` → Enter) y correr:

```
python --version
curl --version
```

## B. Instalación

Todos los comandos se escriben en **CMD**, uno por línea.

1. **Clonar el repositorio** en la carpeta donde se quiera trabajar:
   ```
   git clone https://github.com/Nerucho2005/PSIB2026Q2-TPS-Grupo14-Dimentstein_Grin_PerezRaffo.git
   cd PSIB2026Q2-TPS-Grupo14-Dimentstein_Grin_PerezRaffo
   ```

2. **Crear un entorno virtual** (recomendado, para no mezclar estas librerías con otras instalaciones de Python):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
   Al activarlo, la línea de CMD empieza con `(.venv)`. En Linux/macOS el segundo comando es `source .venv/bin/activate`. Cada vez que se abra una CMD nueva para usar el proyecto hay que volver a correr `.venv\Scripts\activate` desde la raíz del repositorio.

3. **Instalar las dependencias** listadas en `requirements.txt` (MNE, NumPy, SciPy, pandas, Matplotlib y PySide6):
   ```
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
   La instalación tarda unos minutos.

4. **Verificar la instalación:**
   ```
   python -c "import mne, scipy, pandas, matplotlib, PySide6; print('OK')"
   ```
   Si imprime `OK`, está todo listo.

## C. Abrir la interfaz gráfica

Desde la **raíz del repositorio** (la carpeta que contiene `TPS/` y este README), con el entorno virtual activado:

```
python TPS/interfaz/main_window.py
```

Es importante ejecutarlo desde la raíz: el programa ubica los datos (`EEG-Paciente<n>/`) y los resultados (`results/`) a partir de esa carpeta.

No hace falta descargar ningún dato a mano: la interfaz descarga el registro del sujeto elegido la primera vez que se lo analiza.

## D. Cómo se usa la interfaz

La ventana tiene un **panel de controles** a la izquierda, numerado en el orden de uso (1 a 4), y a la derecha las **pestañas de figuras**, el **registro de eventos** y la **barra de progreso**.

### 1. Paciente

- **Paciente:** lista desplegable con los 40 sujetos del dataset (sub-001 a sub-040).
- **Run:** muestra qué bloque se va a analizar. Siempre es el *primer* bloque de 500 estímulos del mediano de ese sujeto (run-02 o run-03, según el orden contrabalanceado del experimento). Se completa solo.
- **Datos:** indica el estado del registro en la computadora:
  - *Descargado en EEG-Paciente<n>*: ya está completo, se analiza sin descargar.
  - *A descargar: ~1,8 GB (… GB libres)*: hay que descargarlo; se informa el espacio necesario y el disponible.
  - *Descarga incompleta: se retoma*: una descarga anterior se cortó; continúa desde donde quedó.
  - *Ya analizado (resultados guardados)*: hay resultados en caché y se pueden ver sin descargar ni recalcular.

### 2. Opciones

- **Incluir referencia promedio (lento):** agrega la referencia promedio a la comparación de referencias (pestaña 4). Es más lenta porque obliga a leer los 64 canales del registro.
- **Usar resultados guardados si existen:** si el sujeto ya se analizó con los mismos parámetros, se muestran los resultados guardados de inmediato, aunque los datos se hayan borrado.
- **Datos descargados:** qué hacer con el registro descargado (solo afecta a los que descargó la interfaz):
  - *Eliminar al terminar el análisis* (opción por defecto): libera el disco apenas termina el cálculo.
  - *Eliminar al cambiar de paciente*: los conserva mientras se trabaje con ese sujeto.
  - *Conservar*: no borra nada.

### 3. Análisis

- **Botón principal:** cambia de nombre según el estado del paciente:
  - *Descargar y analizar*: descarga los archivos que falten y corre el pipeline completo.
  - *Analizar*: los datos ya están; solo corre el pipeline.
  - *Ver resultados*: carga los resultados guardados.

  El pipeline hace, en orden: re-referencia CP4–Fz, interpolación del artefacto de estímulo, filtrado (30–400 Hz y notch de 50 Hz, fase cero), segmentación en épocas, los cuatro promedios (homogéneo, `n`, `s`, `sn`), la SNR con su incertidumbre, la curva SNR vs. N y los componentes del PES. La barra de progreso avanza por etapas y el registro de eventos muestra lo que se está haciendo. Un análisis completo tarda unos minutos, más el tiempo de descarga. Atajo: **Ctrl+R**.
- **Cancelar:** detiene el trabajo en curso. Una descarga se interrumpe enseguida (y se podrá retomar); un cálculo se detiene al terminar la etapa que está corriendo.
- **Eliminar datos descargados:** borra, previa confirmación, las carpetas de todos los sujetos que descargó la interfaz. Los resultados guardados se conservan. **Nunca borra carpetas descargadas a mano** (por ejemplo, `EEG-Paciente1` usado para el informe).

Mientras hay un análisis en curso, los controles del panel quedan deshabilitados salvo *Cancelar*.

### 4. Resultados

- **Resumen:** sujeto, run, cantidad de épocas, latencia del N20 y SNR del promedio homogéneo.
- **Guardar figuras…** (Ctrl+S): guarda las diez figuras en PNG (300 dpi) y PDF en la carpeta que se elija (por defecto, `results/figuras_sub-XXX/`).
- **Exportar CSV…** (Ctrl+E): exporta las tablas (componentes, SNR por método, reproducibilidad, bandas y referencias) en la carpeta que se elija (por defecto, `results/tablas_sub-XXX/`). Los CSV se abren bien en Excel.

Ambos botones se habilitan cuando hay resultados.

### Pestañas de figuras

Cada pestaña tiene una barra de herramientas para hacer zoom, desplazarse y guardar esa figura sola.

| Pestaña | Qué muestra |
|---|---|
| 1. Espectro | Densidad espectral de potencia antes y después del filtrado |
| 2. Artefacto | Artefacto de estímulo sin filtrar y promedio filtrado con y sin interpolación |
| 3. Filtros | PEP y SNR con tres bandas de filtrado (IFCN, 5–100 Hz y la del paper) |
| 4. Referencias | PEP y ruido residual con distintas referencias (RM, Fz, mastoides enlazadas y, si se eligió, promedio) |
| 5. Lateralidad | CP3 contra CP4 con referencia simétrica: el N20 aparece del lado contralateral |
| 6. PEP por método | PEP con los cuatro métodos de promediado y sus componentes (N20, P25, N35, P45) |
| 7. SNR vs. N | SNR en función de la cantidad de épocas, con la recta teórica de 10 dB/década |
| 8. Dif. de SNR | Ganancia de cada método inhomogéneo respecto del homogéneo, con IC 95 % |
| 9. Pesos | Varianza del ruido de cada época y peso que le asigna cada método |
| 10. Reproducib. | Primera mitad contra segunda mitad del registro (criterio IFCN) |
| Métricas | Tablas de componentes, de SNR por método y de reproducibilidad |

### Menú

- **Archivo:** *Descargar y analizar* (Ctrl+R), *Guardar figuras…* (Ctrl+S), *Exportar CSV…* (Ctrl+E) y *Salir* (Ctrl+Q). Si se cierra la ventana durante un análisis, pide confirmación para cancelarlo.
- **Ayuda → Acerca de:** datos del trabajo y parámetros del pipeline en uso.

### Dónde quedan los archivos

| Qué | Dónde |
|---|---|
| Registros descargados | `EEG-Paciente<n>/` en la raíz del repositorio |
| Resultados guardados (caché) | `results/cache_interfaz/` |
| Figuras y CSV exportados | La carpeta elegida al guardar (por defecto, dentro de `results/`) |

Los parámetros del análisis (canal, referencia, filtros, ventanas) **no se cambian desde la interfaz**, para que todos los sujetos se analicen igual: están en `TPS/main/config.py`. Más detalles de la interfaz en `TPS/interfaz/README.md`.

## E. Problemas frecuentes

| Problema | Solución |
|---|---|
| `'python' no se reconoce como un comando` | Python no está en el PATH: reinstalarlo tildando *Add python.exe to PATH*, o usar `py` en lugar de `python` |
| `ModuleNotFoundError: No module named 'PySide6'` (u otra librería) | El entorno virtual no está activado o faltó instalar: correr `.venv\Scripts\activate` y `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'TPS'` o `'main'` | VS Code reescribió un import. Los imports deben ser `import config`, `from ui_ventana import ...` (ver *Nota sobre los imports* al final) |
| No encuentra los datos o los resultados | Ejecutar el comando desde la raíz del repositorio, no desde `TPS/interfaz/` |
| `No se encontró curl` | Instalar curl y agregarlo al PATH (en Windows 10/11 ya viene instalado) |
| `Espacio insuficiente` | Liberar disco con *Eliminar datos descargados* o borrar carpetas `EEG-Paciente<n>` que no se usen |
| La descarga se cortó | Volver a apretar *Descargar y analizar*: se retoma desde donde quedó |

---

# Documentación técnica

## 1. Objetivo

Trabajo Práctico de Señales (TPS) de 16.63 *Procesamiento de Señales e Imágenes Biomédicas* (ITBA), 2026 – Q2.

**Objetivo general:** cuantificar cómo mejora la **relación señal/ruido (SNR)** del PES del nervio mediano
- según el **tipo de promediado**: homogéneo e inhomogéneo en sus modos `n` (pondera por ruido), `s` (por amplitud) y `sn` (por ambos);
- según la **cantidad de épocas promediadas** (N), contrastada con la predicción teórica de +10 dB por década.

**Objetivos puntuales:**
1. Comparar el promedio homogéneo con los tres inhomogéneos y medir si la diferencia de SNR es significativa.
2. Medir la SNR en función de N y contrastarla con la teoría.
3. Verificar que los resultados se repiten en un grupo de 10 sujetos.
4. Diseñar un preprocesamiento justificado por la bibliografía que no desplace las latencias, y contrastar el N20 con las normas IFCN y con el paper del dataset.

## 2. Datos y bibliografía

- **Dataset:** OpenNeuro **ds004388** v1.0.0 (BIDS, EEGLAB). Es el Experimento 1 de **[P] Nierula et al. (2024)**, *PLOS Biology* 22(10): e3002828, "A multichannel electrophysiological approach to noninvasively and precisely record human spinal cord activity".
- **El estudio:**
  - Es un trabajo **metodológico**: valida el registro no invasivo de la médula espinal (ESG multicanal más filtrado espacial por CCA), junto con el nervio periférico y la corteza.
  - Participaron 42 voluntarios **sanos** y diestros; se analizaron 36.
  - Estimulación eléctrica del **mediano izquierdo** en la muñeca, con pulsos de 0,2 ms apenas por encima del umbral motor. El dataset también tiene bloques de estimulación del tibial, que no se usan en este trabajo.
  - Intervalo entre estímulos de 763 ± 50 ms (≈ 1,3 Hz), en 4 bloques de 500 estímulos por nervio, alternados entre nervios y contrabalanceados.
- **Registro:** EEG de 64 canales a 10 kHz, contra la **mastoides derecha (RM)**, con Fz agregado para poder re-referenciar; filtro de hardware de 0,16 a 2500 Hz.
- **Datos analizados:** sujetos **sub-001 a sub-010**, con el primer bloque de 500 estímulos del mediano de cada uno (run-03 para 001, 002, 005, 007, 009 y 010; run-02 para 003, 004, 006 y 008). Cada registro ocupa ~1,8 GB y se guarda en `EEG-Paciente<n>/`, fuera de git. Se eligieron 10 de los 40 sujetos por tiempo de descarga y espacio en disco; la interfaz permite analizar cualquiera de los 40. sub-001 se usa para verificar las decisiones de diseño y mostrar el análisis en detalle.
- **Procesamiento cortical del paper**, como referencia:
  - interpolación PCHIP del artefacto;
  - remuestreo a 1 kHz e ICA;
  - **Butterworth de orden 4 de fase cero, 30–400 Hz**, más notch de 48–53 Hz;
  - referencia promedio y CCA;
  - N20 medio de **19,81 ± 0,20 ms** (media ± EE, N = 36);
  - **SNR** como el RMS en ±1 ms alrededor del pico dividido por el RMS en la misma ventana antes del estímulo.
- **[IFCN] Mauguière et al. (1999)**, *Recommendations for the Practice of Clinical Neurophysiology*, EEG Suppl. 52, cap. 2.4. Guía clínica con estas pautas:
  - estímulo a menos de 5 Hz y 500 barridos;
  - filtros de registro: pasaaltos < 3 Hz y pasabajos > 2000 Hz, con notch apagado; el filtrado digital posterior permite "seleccionar off-line las frecuencias de interés";
  - montaje **Pc–Fz**;
  - normas: N20 19,8 ms (límite 23,0 ms), N20–P25 3,2 µV (mínimo 0,8 µV);
  - reproducibilidad: 0,25 ms y 20 %.
- **Otras referencias del informe:** Schimmel (1967), promediado alternado; Lütkenhöner et al. (1985), promedio ponderado por el ruido; Davila y Mobin (1992), promedio ponderado de SNR máxima; Quian Quiroga y Garcia (2003), wavelets.
- **Teoría de promediado:** apuntes de la cátedra (modelo x_m = a_m·s + v_m, pesos óptimos, método par/impar).

## 3. Decisiones de diseño

| Decisión | Elección | Justificación | Verificación |
|---|---|---|---|
| Canal | **CP4** | [IFCN] N20 en la región parietal contralateral (Pc ≈ CP3/CP4). [P] estímulo en el brazo izquierdo | `05_lateralidad`: N20 solo en CP4 con referencia simétrica |
| Referencia | **Fz** | [IFCN] montaje Pc–Fz: el P20 frontal tiene polaridad opuesta al N20 y la derivación los suma. [P] Fz agregado para re-referenciar | `04_referencias`: Fz da la mayor SNR (26,9 dB) y el mayor N20 |
| Lateralidad | mastoides enlazadas | Con Fz, el P20 invertido produce un falso "N20" también en CP3 | `05_lateralidad` |
| Artefacto | **recta de −1 a +3 ms, antes de filtrar** | [P] interpola con PCHIP (variante). El artefacto dura ~1 ms y queda fuera de la ventana del PEP | `02_artefacto`, `chequeo_artefacto.py` |
| Filtro | **Butterworth de orden 4, fase cero, 30–400 Hz** | [P] misma banda y mismo tipo de filtro. La fase cero no desplaza latencias. [IFCN] el filtrado digital offline de la banda de interés es aceptable | `03_filtros`: 26,9 dB contra 18,7 dB (1–2000 Hz) y 17,3 dB (5–100 Hz) |
| Notch | 50 Hz, Q = 30 | [P] usa notch de 48–53 Hz. [IFCN] recomienda apagarlo en el registro clínico; se mantiene porque es angosto y de fase cero | `01_psd` |
| Ventana del PEP | 15–30 ms (N20–P25) | [IFCN] latencia del N20 y amplitud N20–P25. Con Fz, lo posterior a ~25 ms se mezcla con el N30 frontal | — |
| N de épocas | M = 500 | [IFCN] 500 barridos alcanzan. [P] bloques de 500 | `07_curvas_snr` |

**Consideraciones:**
- **Armónicos de la red:** el notch solo quita los 50 Hz. En CP4–Fz no se observan armónicos dentro de la banda de paso (`01_psd`); además, el promediado atenúa cualquier componente no sincronizada con el estímulo, gracias al jitter de ±50 ms.
- **Componentes tardíos:** el pasaaltos de 30 Hz atenúa el N35 y el P45. No afecta al objetivo, porque la ventana de SNR es 15–30 ms.
- **Amplitudes:** las normas IFCN de amplitud se definen con filtros clínicos más anchos; con 30–400 Hz son orientativas. Las latencias sí son comparables.

## 4. Estructura del repositorio

```
PSIB2026Q2-TPS-Grupo14-Dimentstein_Grin_PerezRaffo/
├── EEG-Paciente<n>/            # datos .set/.fdt/.tsv/.json de cada sujeto (FUERA de git)
├── TPS/
│   ├── main/                   # PIPELINE: lo que necesita main.py
│   │   ├── config.py           # parámetros (decisiones de diseño con su bibliografía; SUJETO y RUN)
│   │   ├── filtrado.py         # etapas 1-2: carga, re-referencia, artefacto, filtrado
│   │   ├── segmentacion.py     # etapa 3: eventos y épocas
│   │   ├── promedio.py         # etapa 4: promedio homogéneo e inhomogéneo (n, s, sn)
│   │   ├── snr.py              # etapa 5: SNR par/impar, jackknife, curva SNR vs. N, SNR del paper
│   │   ├── teoria.py           # etapa 6: componentes vs. IFCN y paper; reproducibilidad
│   │   └── main.py             # corre las 6 etapas para un sujeto, tablas en results/
│   ├── pruebas/                # VERIFICACIÓN de las decisiones de diseño (no las usa main.py)
│   │   ├── chequeo_artefacto.py    # artefacto de estímulo e interpolación
│   │   ├── comparar_filtros.py     # bandas IFCN / 5–100 Hz / paper
│   │   └── comparar_referencias.py # RM, Fz, mastoides enlazadas, promedio
│   ├── figuras/                # FIGURAS DEL INFORME
│   │   ├── graficos.py         # figuras 01-10 (sub-001) y sus CSV
│   │   └── grupal.py           # figuras 11-13: análisis de los 10 sujetos (lee results/)
│   └── interfaz/               # INTERFAZ GRÁFICA (PySide6), ver "Guía de uso"
│       ├── main_window.py      # ventana: descarga, análisis en segundo plano, figuras y tablas
│       ├── pacientes.py        # los 40 sujetos: run, tamaños, descarga con curl, borrado
│       ├── ventana.ui          # diseño de la ventana (Qt Designer)
│       └── ui_ventana.py       # generado desde ventana.ui (no editar a mano)
├── results/                    # CSV de cada sujeto y caché de la interfaz (FUERA de git)
├── informe/figuras/            # figuras del informe (PNG + PDF) y tablas, generadas por graficos.py y grupal.py
├── requirements.txt
└── README.md
```

## 5. Cómo ejecutar los scripts

Además de la interfaz, el análisis se puede correr por scripts. Desde la raíz del repositorio, con el entorno virtual activado:

```
python TPS/main/main.py                     # pipeline de un sujeto (SUJETO y RUN en config.py); tablas en results/
python TPS/pruebas/chequeo_artefacto.py     # justificación de la interpolación
python TPS/pruebas/comparar_filtros.py      # justificación de la banda
python TPS/pruebas/comparar_referencias.py  # justificación de la referencia
python TPS/figuras/graficos.py              # figuras 01-10 de sub-001 (--sin-promedio omite la ref. promedio, la más lenta)
python TPS/figuras/grupal.py                # figuras 11-13 del grupo (requiere haber corrido main.py con cada sujeto)
```

## 6. Pipeline y módulos

```
_events.tsv ─► cargar_eventos ─► muestras de estímulo
.set/.fdt ─► cargar_y_referenciar (CP4 − Fz) ─► interpolar_artefacto (−1 a +3 ms)
          ─► Butterworth 30–400 Hz + notch 50 Hz (sosfiltfilt) ─► segmentar_epocas (−30 a 80 ms, base −30 a 0)
          ─► promedios (homogéneo, n, s, sn) ─► SNR par/impar ± jackknife ─► curva SNR vs. N
          ─► SNR del paper ─► componentes vs. IFCN/paper ─► reproducibilidad
```

**El artefacto se interpola sobre el registro crudo, antes de filtrar.** Si se filtrara primero, el filtro de fase cero lo dispersaría hacia ambos lados de t = 0.

**Convenciones de datos:**
- `epocas`: `(M, C, N)` en V, **en orden temporal**;
- `tiempos`: en s, con 0 en el estímulo;
- `pe`: `(C, N)`;
- `pesos`: `(M, C)`.

### `promedio.py`

Modelo: x_m(n) = a_m·s(n) + v_m(n). Pesos óptimos sin sesgo: **w_m = (a_m/σ²_m) / Σ(a_k²/σ²_k)**. Hay cuatro modos:
- homogéneo: w = 1/M;
- `n`: w ∝ 1/σ²_m;
- `s`: w ∝ a_m;
- `sn`: w ∝ a_m/σ²_m.

Cómo se estiman los parámetros:
- **σ²_m:** sobre toda la época.
- **a_m:** por bloques de 50 épocas, comparando cada bloque contra el promedio de los otros. Los valores negativos se recortan a 0 y se normaliza a media 1.

### `snr.py`

- **SNR principal: promedio alternado** (*plus-minus*). Es equivalente al método par/impar de la cátedra, (s_par − s_impar)/2, con los pesos del método evaluado y 50 particiones. Se calcula así:
  - P_ruido = media de ruido² en la ventana;
  - P_señal = media de pe² − P_ruido;
  - SNR = 10·log10(P_señal/P_ruido).
- `jackknife_snr`: error estándar por jackknife de 10 bloques de épocas consecutivas. **No se usa bootstrap con reemplazo**: repite épocas, que se cancelan en el promedio alternado, y rompe el orden temporal.
- `diferencia_metodos`: IC 95 % por jackknife pareado.
- `curva_snr`: SNR vs. N con bloques disjuntos de N épocas consecutivas (al menos 4; si no, jackknife dentro de las N épocas).
- `ajustar_pendiente`: pendiente contra log10(N); la teórica es 10 dB/década.
- `snr_teorica_ajustada`: recta +10·log10(N) ajustada.
- **`snr_paper` y `curva_snr_paper`**: métrica complementaria de [P]. Es el RMS en ±1 ms alrededor del N20 dividido por el RMS en la ventana espejada antes del estímulo, pasado a dB con 20·log10. Como el numerador incluye ruido, con N chico tiende a 0 dB.

### `teoria.py`

- `COMPONENTES`: N20, P25, N35 y P45, con polaridad y ventana de búsqueda.
- `comparar_con_teoria`: latencias, amplitudes y N20–P25 pico a pico contra la IFCN y el paper. Marca `borde`, `polaridad_ok` y `valido`.
- `tabla_metodos`: componentes según el método de promediado.
- `reproducibilidad`: primera contra segunda mitad del registro (criterio IFCN).

### `graficos.py`: figuras del informe

| Figura | Contenido |
|---|---|
| 01_psd | PSD del crudo interpolado contra el filtrado (banda y notch) |
| 02_artefacto | Zoom sin filtrar y promedio filtrado, sin y con interpolación |
| 03_filtros | PEP con las bandas IFCN (1–2000 Hz), 5–100 Hz y del paper (30–400 Hz), y su SNR (homogéneo y `n`) |
| 04_referencias | PEP y ruido residual con RM, Fz, mastoides enlazadas y promedio |
| 05_lateralidad | CP3 contra CP4 con mastoides enlazadas |
| 06_pep_metodos | PEP de los 4 métodos, banda ±2·RMS y componentes; detalle de la ventana |
| 07_curvas_snr | SNR vs. N de los 4 métodos con la recta teórica, y SNR del paper vs. N |
| 08_diferencias_metodos | `n`, `s` y `sn` menos el homogéneo, con IC 95 % |
| 09_pesos | σ² por época y peso relativo de cada método inhomogéneo |
| 10_reproducibilidad | Primera contra segunda mitad (IFCN) |

Además guarda los CSV `03_filtros`, `04_referencias`, `06_componentes`, `07_snr_metodos` y `08_diferencias_metodos`.

## 7. Resultados

### Grupo: sub-001 a sub-010 (M = 500)

| Medida | Media [IC 95 % entre sujetos] | Prueba |
|---|---|---|
| Ganancia de `n` sobre el homogéneo | **+1,40 dB [0,43; 2,36]**, 9/10 positivos | Wilcoxon p = 0,004 |
| Ídem sin sub-009 | +1,04 dB [0,42; 1,67] | p = 0,008 |
| Ganancia de `sn` | +1,37 dB [0,41; 2,33] | p = 0,004 |
| Ganancia de `s` | −0,07 dB [−0,52; 0,38] | p = 0,70 |
| Pendiente del homogéneo | 10,2 dB/década [9,4; 11,1] | no difiere de 10 (p = 0,77) |
| SNR del homogéneo | 22,5 dB [19,3; 25,6] | — |
| N20 (9 sujetos confiables) | 19,4 ± 1,1 ms (paper: 19,81 ± 1,2 ms) | no difiere del paper (p = 0,24) |

**Sujetos atípicos:**
- **sub-009:** las primeras ~100 épocas son muy ruidosas (σ² de hasta ~430 µV²); ahí `n` gana +4,6 dB, la única ganancia individual significativa. Su N20 es débil (−0,7 µV) y no cumple la reproducibilidad, así que se excluye de la comparación de latencias (`SUJETOS_SENSIBILIDAD` en `grupal.py`).
- **sub-008:** una sola época con σ² ≈ 550 µV² eleva la pendiente del homogéneo a 13,4 dB/década.
- **sub-004:** no cumple la reproducibilidad de latencia (0,6 ms).
- **sub-003:** ruido parejo y ganancia nula (−0,14 dB).

### sub-001

| Método | SNR (dB) ± EE | Diferencia con el homogéneo (dB) [IC 95 %] | Pendiente (dB/década) |
|---|---|---|---|
| Homogéneo | 26,86 ± 0,74 | — | 10,4 ± 0,3 |
| `n` | 27,58 ± 0,97 | +0,72 [−0,24; 1,68] | 10,8 ± 0,3 |
| `s` | 26,92 ± 0,77 | +0,06 [−0,13; 0,25] | 10,4 ± 0,3 |
| `sn` | 27,56 ± 0,91 | +0,70 [−0,21; 1,61] | 10,7 ± 0,3 |

- N20 a 19,5 ms y N20–P25 de 7,26 µV, iguales con los cuatro métodos (±0,1 ms); cumple la reproducibilidad IFCN (Δlat 0,1 ms, Δamp 4 %).
- La métrica del paper da 27,8 dB con M = 500, pero con una pendiente de solo 5,2 dB/década y barras de error mucho más anchas.

### Conclusiones

- El promedio inhomogéneo `n` mejora la SNR en ~1,4 dB, de forma chica pero sistemática entre sujetos; equivale a promediar un 38 % más de estímulos con el homogéneo. `sn` rinde lo mismo y `s` no aporta, porque la amplitud del PEP no cambia en 500 estímulos (no hay habituación detectable).
- La ganancia crece con la no estacionariedad del ruido (G = media(σ²)·media(1/σ²) ≥ 1) y es menor cuanto mejor es el filtrado: en sub-001, `n` gana ~2 dB con 1–2000 o 5–100 Hz y 0,7 dB con 30–400 Hz.
- La SNR crece ~10 dB por década de N en todos los métodos, como predice la teoría; el promedio inhomogéneo desplaza la curva hacia arriba sin cambiar la pendiente.
- El filtro de fase cero conserva las latencias: el N20 coincide con la IFCN y con el paper.

**Posibles extensiones:** analizar los 40 sujetos y concatenar los cuatro bloques del mediano (~2000 épocas) para evaluar habituación; estimar σ² por época con más grados de libertad; interpolar el artefacto con PCHIP, como el paper.

## 8. Convenciones del código

- **Funciones puras** en los módulos de cálculo. Los parámetros están en `config.py` y se pasan desde los scripts.
- Las épocas se mantienen **en orden temporal** (lo requieren el promedio alternado, los bloques de amplitud y el jackknife).
- Los métodos se validaron con **datos sintéticos** (PEP conocido y ruido con tramos de varianza alta) antes de aplicarlos a los registros reales.
- Los scripts se ejecutan **desde la raíz del repositorio**.

## Nota sobre los imports

Los scripts de `pruebas/`, `figuras/` e `interfaz/` agregan `TPS/main` al `sys.path` en sus primeras líneas, para poder importar los módulos del pipeline con `import config`, `from filtrado import ...`, etc. No hay que convertir esos imports a la forma `TPS.main.config`: VS Code a veces lo propone, y rompe la ejecución desde la raíz del repo. Si Pylance marca los imports como no resueltos, se puede agregar `"python.analysis.extraPaths": ["TPS/main", "TPS/pruebas", "TPS/figuras", "TPS/interfaz"]` a la configuración de VS Code; es solo cosmético.