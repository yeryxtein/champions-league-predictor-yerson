# Champions Lab: datos, comparación y predicción experimental

Proyecto académico de Yerson Chaparro Varón. Versión 0.4: Python, FastAPI, Streamlit y scikit-learn.

Para exponer, abre la [presentación final de diez diapositivas](docs/Presentacion_final_Champions.pptx) y el [guion oral de seis a ocho minutos](docs/Guion_final.md). La [guía de demostración](docs/PRUEBA_Y_DEMO.md) indica qué equipos elegir y qué resultados mostrar en la aplicación.

El [informe final en PDF](docs/Informe_final_Champions.pdf) contiene el árbol de problemas, los objetivos, el marco teórico, los requisitos y la evaluación de los modelos. También está disponible en [Word editable](docs/Informe_final_Champions.docx).

## Abrir la aplicación

En Windows, abre **INICIAR.cmd**. Mantén la consola abierta durante la demostración.

- Interfaz: http://127.0.0.1:8501
- API documentada: http://127.0.0.1:8000/docs

El iniciador utiliza el entorno ya preparado en este equipo. Si extraes el ZIP en otra ubicación, busca Python y crea un entorno `.venv`. La primera instalación requiere internet. Los datos vienen incluidos y la aplicación no necesita descargarlos para funcionar. Swagger puede necesitar internet para sus recursos visuales, pero los endpoints y la interfaz consultan archivos locales.

## Lo que ya funciona

- 1.372 partidos de diez temporadas, de 2016/17 a 2025/26, con 96 clubes unificados; 189 partidos en cada una de las dos temporadas nuevas.
- Archivos fuente, procedencia, licencia, hashes y enlaces a cada fila original.
- Conversión a CSV, fase de liga y playoffs, fechas comprobadas, 26 variantes de nombres unificadas y marcador a 90 minutos. Dos correcciones documentadas con fuentes oficiales.
- API propia de consulta, resumen, calidad, descarga y comparación histórica.
- Interfaz con filtros, gráficos, tablas, exportación y estados vacíos o de error.
- Comparación de los últimos cinco partidos de Champions anteriores a una fecha.
- Enfrentamientos directos entre dos equipos, con ambas localías: victorias, empates, goles, tabla y descarga en CSV.
- Notebook inicial de análisis y pruebas de los casos relevantes.
- Modelo Random Forest entrenado, comparado con regresión logística y referencia simple; probabilidades de victoria local, empate y victoria visitante.
- Evaluación temporal, informe de métricas y matriz de confusión. Artefactos evaluado y reajustado separados.
- Ejemplo histórico listo para cargar, tabla de variables utilizadas y descarga de la estimación completa en JSON.
- Evaluación de cinco recetas mediante validación temporal y comparación retrospectiva en 2025-26, visible en **Evaluación de mejoras**.

## Alcance de la entrega

La versión 0.4 incluye la aplicación, las pruebas técnicas y el material para la exposición. El estado de cada requisito y su evidencia figuran en la [revisión de cierre](docs/CIERRE_REQUISITOS.md). Por decisión del estudiante, la sesión con compañeros quedó fuera del alcance. La investigación posterior incluye auditar sedes, calibrar probabilidades y evaluar pronósticos guardados antes de partidos futuros.

Los datos terminan el **30 de mayo de 2026**; no contienen 2026-27 ni se actualizan automáticamente. El corte histórico máximo es el 31 de mayo de 2026 y excluye partidos del propio día. Se permiten escenarios predictivos hasta 365 días después del último registro, con aviso explícito de datos faltantes; ese horizonte no implica precisión validada.

## Resultado del primer modelo

Se entrenaron candidatos con las temporadas anteriores a 2023-24 y se seleccionó Random Forest por F1 macro en la validación 2023-24. Tras reajustar con entrenamiento y validación, se evaluó una vez en 154 de los 189 partidos de 2024-25; se excluyeron 34 por historial insuficiente y la final por sede neutral.

| Métrica en prueba 2024-25 | Random Forest | Referencia simple |
|---|---:|---:|
| Exactitud | 55,19 % | 51,30 % |
| F1 macro | 0,381 | 0,226 |
| Log loss (menor es mejor) | 0,975 | 1,003 |

**No acertó ninguno de los 23 empates reales.** La mejora global es modesta y las probabilidades no están calibradas. El modelo reajustado con todos los datos elegibles no tiene una nueva prueba futura independiente: las cifras anteriores pertenecen al modelo evaluado. Metodología, exclusiones y resultados completos en [docs/MODELO.md](docs/MODELO.md).

## Evaluación ampliada de 2025-26

La validación expansiva en 2022-23, 2023-24 y 2024-25 seleccionó regresión logística equilibrada con trece variables. En los mismos 164 partidos de prueba de 2025-26 obtuvo 52,44 % de exactitud, F1 macro 0,4559 y log loss 1,0137. RF6, reajustado con los mismos datos anteriores a esa prueba, obtuvo 51,83 %, F1 macro 0,3406 y log loss 0,9709.

La logística acertó seis de los 27 empates reales, con 27 pronósticos de empate. RF6 acertó cero, con un pronóstico de empate. La ganancia de clasificación viene acompañada de un peor log loss. La decisión para esta entrega es utilizar Random Forest de la primera versión en **Predicción experimental** y presentar el experimento ampliado en **Evaluación de mejoras**. La selección del experimento queda registrada como evidencia. Su F1 macro mejoró y su log loss empeoró frente a RF6 en la misma prueba.

Los resultados son retrospectivos. La selección de recetas usa temporadas anteriores a 2025-26 y los pesos de prueba quedan congelados hasta 2024-25. Los resultados de 2025-26 ya habían formado parte del reajuste de la primera versión. Metodología, decisiones y evidencia en [docs/MEJORAS_MODELO.md](docs/MEJORAS_MODELO.md).

## Recorrido de demostración

1. En **Explorar partidos**, muestra las 1.372 filas. Selecciona 2024-25 o 2025-26: aparecen 189 partidos en cada temporada.
2. En **Calidad de los datos**, muestra las diez temporadas, los controles y el origen de la información.
3. En **Comparar equipos**, selecciona Real Madrid y Manchester City con corte 02/06/2024 y pulsa **Comparar historial**. En **Últimos 5 partidos** verás la forma reciente de cada equipo. En **Enfrentamientos directos** verás 8 cruces: 1 victoria de Real Madrid, 3 empates y 4 victorias de Manchester City, a 90 minutos. El 1-1 del 17/04/2024 cuenta como empate aunque Madrid ganó la tanda de penales. Cambia el corte a 09/04/2024 y consulta de nuevo: aparecen 6 cruces, excluyendo el partido de ese día y los posteriores.
4. En **Predicción experimental**, muestra las métricas y su limitación con los empates. Pulsa **Cargar ejemplo histórico** y luego **Calcular estimación**: Real Madrid local, Manchester City visitante, 19/02/2025. Usa el modelo histórico entrenado hasta el 08/05/2024, sin conocer el resultado de ese partido. Abre **Qué datos usó el modelo** y descarga el JSON si necesitas guardar evidencia.
5. En **Evaluación de mejoras**, revisa la selección temporal, compara los tres modelos en 2025-26 y descarga el informe.
6. En **Avance del proyecto**, presenta los objetivos con su evidencia y el trabajo pendiente.

Frase para exponer: “Actualicé el dataset hasta 2025-26, amplié la comparación con enfrentamientos directos y entrené un primer modelo Random Forest. En la prueba histórica acertó el 55,2 % de 154 partidos, aunque todavía falla al detectar empates. La API ya entrega estimaciones y la interfaz permite verlas junto con sus límites”.

Recorrido ampliado y lista de comprobaciones en [docs/PRUEBA_Y_DEMO.md](docs/PRUEBA_Y_DEMO.md).

## Estructura

```text
api/main.py                   API y comparación histórica
app.py                        Interfaz que consume la API por HTTP
ml/                           Variables previas, entrenamiento y predicción
models/                       Modelos, métricas, variables y predicciones de prueba
data/raw/                     Archivos originales y licencia
data/processed/                CSV y controles de calidad
data/DICCIONARIO.md            Campos, reglas y limitaciones
data/fuentes.json              Versión de la fuente y hashes
data/correcciones_90min.json   Ajustes auditados de marcadores con prórroga
scripts/descargar_datos.py     Descarga explícita de originales
scripts/preparar_datos.py      Transformación reproducible
scripts/entrenar_modelo.py     Selección, prueba y reajuste del modelo
scripts/probar_interfaz.py    Recorrido de Streamlit con API real y errores simulados
scripts/evaluar_mejoras.py    Validación expansiva y prueba retrospectiva 2025-26
models/experimento_v2/        Selección registrada, informe y predicciones por modelo
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
.venv\Scripts\python.exe scripts/entrenar_modelo.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para reproducir el laboratorio de mejoras, ejecuta `.venv\Scripts\python.exe scripts/evaluar_mejoras.py`. Guarda sus salidas en `models/experimento_v2/`. La interfaz consulta el informe por HTTP.

El script de descarga consulta la versión actual de la fuente y reemplaza los originales sólo tras completar la descarga. No es necesario ejecutarlo para la demostración. Tras una nueva descarga, vuelve a preparar los datos, revisa las diferencias, entrena y reinicia los servicios. Si el CSV cambia, las predicciones se bloquean hasta disponer de un entrenamiento coherente con los datos. Conserva los bytes originales de los TXT y del CSV para no invalidar sus hashes.

### Verificar la interfaz con la API

Con `INICIAR.cmd` abierto, ejecuta en una segunda terminal del proyecto:

```powershell
.venv\Scripts\python.exe scripts/probar_interfaz.py
```

En este espacio de trabajo también puedes usar `../../work/champions_env/Scripts/python.exe` en lugar del ejecutable de `.venv`.

El 11/11/2026 se verificó la copia de entrega en un entorno limpio de Windows x64 con Python 3.12.14. Las 52 dependencias coincidieron con las versiones fijadas y `pip check` confirmó su compatibilidad. Pasaron **47 pruebas de datos, API y modelo y 19 comprobaciones de interfaz**. El recorrido comprueba filtros, descarga CSV, cruces directos y probabilidades mediante peticiones HTTP a una instancia local de la API. También simula demoras, desconexión y un modelo no disponible para verificar los mensajes que recibe el usuario.

## API

| Ruta | Función |
|---|---|
| GET /salud | Estado de la API y del modelo |
| GET /equipos | Equipos, temporadas, fases y rango de fechas |
| GET /partidos | Registros filtrados y paginados |
| GET /resumen | Conteos y goles de la selección |
| GET /calidad | Controles, cobertura y procedencia |
| GET /descargar | CSV de la selección |
| POST /comparaciones | Últimos cinco partidos y todos los cruces directos antes de una fecha |
| GET /modelo | Estado, modelo seleccionado, métricas, particiones y límites |
| POST /predicciones | Probabilidades a 90 minutos; 422 fuera de alcance, 503 si faltan o cambian artefactos |
| GET /experimentos/mejoras | Informe de la evaluación ampliada con comprobaciones de integridad |

## Comparación directa

La fecha del formulario es exclusiva: se incluyen únicamente partidos anteriores a ese día. Los equipos A y B conservan sus nombres en las estadísticas aunque hayan alternado localía. Los conteos corresponden a la cobertura del dataset, no a toda la historia de los clubes, y no son probabilidades predictivas. Si no existen cruces previos, la interfaz lo indica sin fabricar resultados.

Si ya estaba abierta la versión anterior, detén su consola con Ctrl+C y ejecuta `INICIAR.cmd` otra vez. La API carga los datos y el código al iniciar.

## Fuentes y decisiones

- OpenFootball: https://github.com/openfootball/champions-league (CC0-1.0, fuente comunitaria).
- FastAPI: https://fastapi.tiangolo.com/
- Streamlit: https://docs.streamlit.io/

## Documentos del proyecto

El [índice de documentos](docs/README.md) reúne los materiales de entrega, la evidencia del modelo y los archivos de la primera presentación. En la aplicación, **Avance del proyecto** permite mostrar los objetivos y sus resultados.

## Repositorio y licencia

El [repositorio del proyecto](https://github.com/yeryxtein/champions-league-predictor-yerson) reúne el código y la documentación. El conjunto de datos fuente pertenece a OpenFootball y se distribuye bajo CC0-1.0. Consulta `data/raw/LICENSE_OpenFootball.md` para su atribución y procedencia. El código de la aplicación todavía carece de una licencia específica.
