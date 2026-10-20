# Champions Lab: primer avance funcional

Proyecto académico de Yerson Chaparro Varón. Python, FastAPI y Streamlit.

## Abrir la aplicación

En Windows, abre **INICIAR.cmd**. Mantén la consola abierta durante la demostración.

- Interfaz: http://127.0.0.1:8501
- API documentada: http://127.0.0.1:8000/docs

El iniciador utiliza el entorno ya preparado en este equipo. Si extraes el ZIP en otra ubicación, busca Python y crea un entorno `.venv`. La primera instalación requiere internet. Los datos vienen incluidos y la aplicación no necesita descargarlos para funcionar. Swagger puede necesitar internet para sus recursos visuales, pero los endpoints y la interfaz consultan archivos locales.

## Lo que ya funciona

- 994 partidos de ocho temporadas, de 2016/17 a 2023/24, con 83 clubes unificados.
- Archivos fuente, procedencia, licencia, hashes y enlaces a cada fila original.
- Conversión a CSV, fechas comprobadas, 15 aliases y marcador a 90 minutos.
- API propia de consulta, resumen, calidad, descarga y comparación histórica.
- Interfaz con filtros, gráficos, tablas, exportación y estados vacíos o de error.
- Comparación de los últimos cinco partidos de Champions anteriores a una fecha.
- Notebook inicial de análisis y pruebas de los casos relevantes.

## Lo que todavía falta

Entrenar y evaluar un modelo, completar las variables para todos los partidos, resolver la condición de sede neutral para entrenamiento y probar la usabilidad con compañeros. **No se generan probabilidades ni ganadores estimados**. `POST /predicciones` devuelve HTTP 503 con un mensaje explícito. El historial comparativo es descriptivo.

Los datos terminan el 1 de junio de 2024. No representan el estado actual de los equipos. El corte histórico máximo admitido es el 2 de junio de 2024 y excluye los partidos del propio día de corte.

## Recorrido de demostración (3 minutos)

1. En **Explorar partidos**, muestra las 994 filas y selecciona 2023-24 y Real Madrid. Aparecen 13 partidos y las estadísticas se actualizan.
2. En **Calidad de los datos**, muestra las ocho temporadas, los controles y el origen de la información.
3. En **Comparar equipos**, selecciona Real Madrid y Manchester City con corte 09/04/2024. Explica que el resumen usa solo encuentros anteriores a esa fecha.
4. Abre la documentación de la API. Expande `GET /resumen`, pulsa **Try it out** y **Execute**. La API devuelve JSON.
5. En **Avance del proyecto**, presenta los objetivos con su evidencia y el trabajo pendiente.

Frase para exponer: “Ya preparé una primera versión del dataset y desarrollé una API propia conectada a una interfaz. Puedo explorar partidos y comparar el historial previo. La siguiente etapa será entrenar y evaluar el modelo antes de ofrecer predicciones”.

## Estructura

```text
api/main.py                   API y comparación histórica
app.py                        Interfaz que consume la API por HTTP
data/raw/                     Archivos originales y licencia
data/processed/                CSV y controles de calidad
data/DICCIONARIO.md            Campos, reglas y limitaciones
data/fuentes.json              Versión de la fuente y hashes
scripts/descargar_datos.py     Descarga explícita de originales
scripts/preparar_datos.py      Transformación reproducible
notebooks/01_exploracion.ipynb  Análisis inicial para Jupyter/Colab
tests/test_proyecto.py         Casos de datos y API
```

## Ejecutar manualmente

Requiere Python 3.12 o superior. En una terminal dentro de la carpeta:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe iniciar.py
```

Para reproducir la transformación y verificar:

```powershell
.venv\Scripts\python.exe scripts/preparar_datos.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

El script de descarga consulta la versión actual de la fuente y reemplaza los originales de esta copia. No es necesario ejecutarlo para la demostración. Tras una nueva descarga, vuelve a preparar los datos, revisa las diferencias y reinicia los servicios. Las pruebas que fijan el tamaño de esta copia pueden requerir una revisión justificada.

## API

| Ruta | Función |
|---|---|
| GET /salud | Estado de la API y del modelo |
| GET /equipos | Equipos, temporadas, fases y rango de fechas |
| GET /partidos | Registros filtrados y paginados |
| GET /resumen | Conteos y goles de la selección |
| GET /calidad | Controles, cobertura y procedencia |
| GET /descargar | CSV de la selección |
| POST /comparaciones | Historial de dos equipos antes de una fecha |
| POST /predicciones | HTTP 503 hasta implementar un modelo evaluado |

## Fuentes y decisiones

- OpenFootball: https://github.com/openfootball/champions-league (CC0-1.0, fuente comunitaria).
- FastAPI: https://fastapi.tiangolo.com/
- Streamlit: https://docs.streamlit.io/

Este avance desarrolla la consulta y la interfaz planteadas en las diapositivas iniciales. Las diapositivas descargadas antes de esta implementación describen un estado anterior. Para mostrar el estado nuevo, utiliza la sección **Avance del proyecto** de la aplicación.

## Documentos del proyecto

En `docs/` se incluyen el informe, el guion de exposición y la presentación inicial. La presentación es anterior a la versión funcional de la API y la interfaz; para explicar el avance actualizado, consulta esta documentación y la sección **Avance del proyecto** de la aplicación.

## Subir una copia a GitHub

Este repositorio está preparado para publicarse. El conjunto de datos fuente pertenece al proyecto comunitario OpenFootball y se distribuye bajo CC0-1.0; revisa `data/raw/LICENSE_OpenFootball.md` y conserva la atribución y procedencia documentadas. No se ha asignado todavía una licencia al código de esta aplicación.
