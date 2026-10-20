# Guion para exponer el primer avance

Duración orientativa: 4 a 6 minutos. Lee el contenido y explícalo con tus palabras. Las diapositivas también contienen estas notas del presentador.

## 1. Presentación y alcance

Mi proyecto busca estimar el resultado de un partido de Champions League a partir de su historial. La salida tendrá tres clases: victoria del local, empate o victoria del visitante, al finalizar los 90 minutos más el tiempo añadido. Hoy presento un avance de definición y diseño: objetivos ajustados, una fuente de datos revisada y la propuesta de una API propia conectada a una interfaz web. El objetivo general es desarrollar y evaluar este sistema utilizando únicamente los datos históricos seleccionados.

## 2. Objetivos específicos

Organicé los objetivos en seis entregables. Primero prepararé los datos. Después crearé variables que describan el rendimiento antes del encuentro. Compararé modelos con una referencia simple. La predicción se ofrecerá mediante una API desarrollada por mí y una interfaz que consuma esa API. Finalmente analizaré los errores y las limitaciones. Así cada objetivo se relaciona con una evidencia concreta del proyecto.

## 3. Fuente de datos

Seleccioné OpenFootball porque ofrece datos abiertos de Champions por temporada. Revisé los archivos de 2022/23 y 2023/24. La tabla muestra tres partidos reales consultados en la fuente. El periodo que propongo reunir va de 2016/17 a 2023/24. Los archivos vienen en texto, por lo que aún debo convertirlos a una tabla, confirmar su cobertura y unificar los nombres. También debo extraer correctamente los resultados de los 90 minutos cuando hay prórroga o penales. Todavía no he consolidado ni contado el dataset completo.

## 4. Tecnologías

Usaré Python como lenguaje principal. pandas servirá para preparar los datos y scikit-learn para los modelos. FastAPI permitirá construir nuestra API y validar las entradas con Pydantic. Streamlit será la interfaz web y enviará las consultas a FastAPI. Empezaré el análisis en Colab y desarrollaré la aplicación localmente en VS Code. Para esta primera versión guardaré la información en CSV y el modelo con joblib.

## 5. API propia

La API será un servicio separado de la interfaz. La pantalla consultará el catálogo de equipos y enviará un partido a la ruta de predicciones. El servicio recuperará el historial anterior a la fecha solicitada, calculará las variables y ejecutará el modelo. Responderá con las probabilidades y la clase estimada. Validaré que los equipos sean diferentes, que haya historial suficiente y que el modelo esté disponible. Si no está disponible, la API devolverá un error claro. Hoy está definido el contrato, pero aún falta programarlo.

## 6. Metodología

La predicción tendrá tres clases al terminar los 90 minutos, incluido el tiempo añadido. Usaré el rendimiento en los cinco partidos anteriores de Champions y los promedios de goles. Los goles del partido que intento predecir solo servirán para crear su etiqueta, nunca como entrada. Primero compararé con un modelo que siempre elige la clase más frecuente. Probaré regresión logística y Random Forest. Entrenaré con temporadas antiguas, elegiré el modelo con validación y reservaré 2023/24 para una prueba final. Aún no hay resultados de entrenamiento.

## 7. UI y UX

La interfaz tendrá un formulario breve con listas de equipos, una fecha y la condición de sede neutral. UI se refiere a cómo se presenta la pantalla. UX se refiere a qué tan fácil resulta usarla. El botón de predicción mostrará que la consulta está en curso. Los resultados incluirán las tres probabilidades con etiquetas, para no depender solo del color. Habrá mensajes claros cuando se repita un equipo o falte historial. Planeo probar estas tareas con tres compañeros y ajustar la pantalla según las dificultades. Por ahora esta es la especificación de la interfaz, no una pantalla funcional.

## 8. Cierre del avance

El avance de esta entrega consiste en aclarar el alcance, ajustar los objetivos, revisar una fuente de datos y definir las tecnologías, la API y los criterios de interfaz. El sistema todavía no está entrenado ni implementado. La siguiente entrega será un notebook con la carga y limpieza inicial: cantidad de partidos, columnas, faltantes y distribución de resultados. Con esa evidencia podré comenzar el entrenamiento y después conectar el modelo a la API y a la interfaz.

## Respuestas a preguntas posibles

**¿Ya funciona el modelo?** Aún no. Este avance corresponde a definición, revisión inicial de la fuente y diseño.

**¿Por qué FastAPI y Streamlit?** FastAPI será la API propia. Streamlit será una interfaz separada que la consulta por HTTP. Ambas permiten trabajar en Python.

**¿Por qué este dataset?** Contiene partidos de Champions organizados por temporada y declara licencia abierta CC0. Primero debo verificar cobertura y calidad. Es comunitario, no oficial de UEFA.

**¿Por qué 90 minutos?** Define un resultado consistente por partido. La clasificación de una eliminatoria y los penales son tareas distintas. Los casos ambiguos se revisarán o excluirán de forma documentada.

**¿Cómo evito que el modelo copie la respuesta?** Los goles finales crean la etiqueta. Las entradas se calculan únicamente con partidos anteriores.

**¿Qué significa F1 macro?** Resume el desempeño dando el mismo peso a local, empate y visitante, para que una clase frecuente no oculte los errores en las otras.

**¿Por qué no dar un porcentaje de acierto ahora?** Solo se puede calcular después de entrenar y evaluar en partidos reservados.

**¿Cómo mostraré UI/UX?** Con una pantalla comprensible, validación de entradas, estados de carga, errores claros y una prueba de tareas con compañeros. Esa prueba todavía está pendiente.

## Próximo paso concreto

Crear un notebook en Colab que convierta los archivos seleccionados a una tabla, documente nombres y marcadores, y muestre cantidad de filas, temporadas, faltantes, duplicados y distribución de resultados. Después construir variables históricas y entrenar.

## Fuentes consultadas el 6 de octubre de 2026

- [dataset](https://github.com/openfootball/champions-league)
- [s23](https://github.com/openfootball/champions-league/blob/master/2023-24/cl.txt)
- [s22](https://github.com/openfootball/champions-league/blob/master/2022-23/cl.txt)
- [api](https://fastapi.tiangolo.com/)
- [ui](https://docs.streamlit.io/)
- [ml](https://scikit-learn.org/stable/common_pitfalls.html)
- [colab](https://developers.google.com/colab)
