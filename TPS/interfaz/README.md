# Interfaz gráfica

Interfaz en **PySide6** para analizar el PES del nervio mediano de cualquiera de los 40 sujetos del dataset ds004388. Se elige el sujeto y, si su registro no está en la computadora, la interfaz lo descarga. Después corre el pipeline completo (`TPS/figuras/graficos.py → calcular`) y muestra las 10 figuras y las tablas de métricas.

## Ejecutar

Desde la raíz del repo:

```
pip install pyside6
python TPS/interfaz/main_window.py
```

La descarga usa `curl`, que viene instalado en Windows 10 y 11.

## Archivos

| Archivo | Contenido |
|---|---|
| `main_window.py` | Lógica de la ventana: hilo de trabajo (descarga + cálculo), figuras, tablas, exportación |
| `pacientes.py` | Los 40 sujetos: primer run del mediano, tamaño exacto de sus archivos, descarga con `curl` y borrado |
| `ventana.ui` | Diseño de la ventana (se edita con `pyside6-designer`) |
| `ui_ventana.py` | Código generado desde el `.ui`. **No editar a mano**: se regenera con `pyside6-uic TPS/interfaz/ventana.ui -o TPS/interfaz/ui_ventana.py` |

## Uso

1. **Paciente:** elegir el sujeto. La interfaz muestra el run (el primer bloque del mediano, 02 o 03 según el sujeto) y el estado de los datos: descargado, a descargar (con el espacio necesario) o ya analizado.
2. **Opciones:**
   - *Incluir referencia promedio:* suma la referencia promedio a la figura 4. Es lenta, porque lee los 64 canales.
   - *Usar resultados guardados:* si el sujeto ya se analizó con los mismos parámetros, se muestran sin descargar ni recalcular.
   - *Datos descargados:* se pueden eliminar al terminar el análisis (opción por defecto), eliminar al cambiar de paciente o conservar.
3. **Analizar:** descarga lo que falte, corre el pipeline y muestra las figuras en las pestañas, que tienen barra de zoom. La barra de progreso avanza por etapas, y *Cancelar* detiene el trabajo al terminar la etapa en curso.
4. **Resultados:** *Guardar figuras* (PNG 300 dpi y PDF) y *Exportar CSV* (componentes, SNR por método, reproducibilidad, bandas y referencias).

## Descarga

- Cada sujeto se guarda en `EEG-Paciente<n>/` en la raíz del repo, igual que las descargas a mano. Si la carpeta ya tiene el run completo, no se descarga nada.
- Se bajan los 6 archivos del run desde el espejo de OpenNeuro en S3:
  ```
  curl -L -O https://s3.amazonaws.com/openneuro.org/ds004388/sub-XXX/eeg/sub-XXX_task-median_run-YY_<ext>
  ```
- Antes de descargar se verifica el espacio libre (~1,8 GB por sujeto).
- Al terminar, el `.set` y el `.fdt` tienen que tener exactamente el tamaño publicado en el dataset. Si una descarga se corta, el próximo intento la retoma desde donde quedó.
- **Solo se borran las carpetas que creó la interfaz** (llevan una marca `.descargado_por_interfaz`). Lo que se descargó a mano, como `EEG-Paciente1` para el informe, nunca se borra desde la interfaz.
- Los resultados se guardan en `results/cache_interfaz/`, unos MB por sujeto. Volver a abrir un sujeto ya analizado es inmediato, aunque sus datos se hayan borrado.

## Notas

- Los parámetros del pipeline no se eligen desde la interfaz: están en `TPS/main/config.py`. Para cambiar de sujeto, la interfaz llama a `config.usar_sujeto()`.
- El cálculo corre en un hilo aparte. Las figuras se arman en el hilo principal, porque matplotlib no es seguro entre hilos.
- Un análisis completo tarda unos minutos, más la descarga.
