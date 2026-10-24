# Interfaz gráfica – Análisis de SEP

Interfaz gráfica hecha con **PySide6** para el análisis de potenciales evocados somatosensoriales (SEP). Permite cargar una señal, filtrarla, promediar las épocas, visualizar los resultados y calcular métricas como la latencia y la amplitud de cada componente.

> Esta carpeta contiene únicamente el diseño de la interfaz. La lógica de procesamiento (filtrado, promediado, métricas) se implementa por separado.

## Requisitos

- Python 3.9 o superior
- [PySide6](https://pypi.org/project/PySide6/)
- [pyqtgraph](https://pypi.org/project/pyqtgraph/) (los gráficos son widgets `PlotWidget`)

```bash
pip install pyside6 pyqtgraph
```

## Archivos

| Archivo | Descripción |
|---|---|
| `ventana.ui` | Diseño de la interfaz, editable con Qt Designer. |
| `ui_ventana.py` | Código Python generado a partir del `.ui`. **No editar a mano**: se sobrescribe al regenerarlo. |
| `main_window.py` | Lógica de la ventana (conexión de botones, llamadas al procesamiento). |

## Editar la interfaz

Abrir Qt Designer con:

```bash
pyside6-designer
```

Luego `Archivo > Abrir` y elegir `ventana.ui`. Con **Ctrl+R** se obtiene una vista previa sin guardar.

Después de cada cambio guardado, regenerar el código Python:

```bash
pyside6-uic ventana.ui -o ui_ventana.py
```

## Organización de la ventana

La ventana principal (`MainWindow`, un `QMainWindow`) se divide en tres zonas:

- **Panel izquierdo:** controles organizados en cuatro etapas, siguiendo el flujo de trabajo.
- **Panel derecho:** pestañas con los gráficos y la tabla de métricas.
- **Parte inferior:** registro de eventos y barra de progreso.

Además tiene un menú **Archivo** (Abrir, Exportar CSV, Salir) y un menú **Ayuda** (Acerca de).

### Panel de controles

**1. Carga de datos**

| Widget | Nombre de objeto | Función |
|---|---|---|
| Botón "Abrir archivo..." | `btnAbrir` | Selecciona el archivo con la señal. |
| Etiqueta | `lblArchivo` | Muestra el nombre del archivo cargado. |
| Selector numérico | `spinFs` | Frecuencia de muestreo (Hz). |
| Lista desplegable | `comboCanal` | Canal a analizar. |

**2. Filtrado**

| Widget | Nombre de objeto | Función |
|---|---|---|
| Botón "Aplicar filtro" | `btnFiltrar` | Aplica a la señal los filtros predefinidos en el código. |

**3. Épocas y promediado**

| Widget | Nombre de objeto | Función |
|---|---|---|
| Botón "Promediar" | `btnPromediar` | Segmenta la señal en épocas y calcula el promedio, con los parámetros predefinidos en el código. |

**4. Resultados**

| Widget | Nombre de objeto | Función |
|---|---|---|
| Botón "Calcular métricas" | `btnMetricas` | Calcula latencias y amplitudes de los componentes. |
| Botón "Exportar CSV" | `btnExportar` | Guarda las métricas en un archivo CSV. |

### Pestañas de visualización

| Pestaña | Widget | Nombre de objeto |
|---|---|---|
| Señal cruda | `PlotWidget` | `graficoCrudo` |
| Filtrada / Promedio | `PlotWidget` | `graficoPromedio` |
| Espectro (PSD) | `PlotWidget` | `graficoPSD` |
| Métricas | `QTableWidget` | `tablaMetricas` |

La tabla de métricas tiene las columnas *Componente*, *Latencia (ms)* y *Amplitud (µV)*, con las filas N9, N13, N20 y P25 precargadas.

### Parte inferior

| Widget | Nombre de objeto | Función |
|---|---|---|
| Registro de eventos (solo lectura) | `txtLog` | Mensajes del proceso (archivo cargado, filtro aplicado, etc.). |
| Barra de progreso | `barraProgreso` | Avance de las operaciones largas. |

### Acciones del menú

`actionAbrir` (Ctrl+O), `actionExportar` (Ctrl+E), `actionSalir` (Ctrl+Q) y `actionAcercaDe`.

## Flujo de uso

1. **Abrir archivo** y elegir la frecuencia de muestreo y el canal.
2. **Aplicar filtro** para filtrar la señal.
3. **Promediar** para obtener el potencial evocado promedio.
4. **Calcular métricas** para obtener latencias y amplitudes.
5. **Exportar CSV** para guardar los resultados.

## Notas

- Los parámetros del filtrado y del promediado (frecuencias de corte, orden, ventana de épocas, umbral de artefactos) **no se eligen desde la interfaz**: están definidos en el código de procesamiento.
- Los gráficos son widgets promovidos a `pyqtgraph.PlotWidget`. En Qt Designer se ven como widgets vacíos y recién se dibujan al ejecutar la aplicación.
- Los nombres de objeto listados arriba son los que se usan en la lógica (`self.btnAbrir`, `self.spinFs`, etc.). Si se renombra alguno en Designer, hay que actualizarlo también en `main_window.py`.
