# Guía de prueba y demostración de Champions Lab

Este recorrido sirve para preparar una demostración de aproximadamente siete minutos. Los resultados esperados se basan en el dataset y los artefactos incluidos en esta versión. La prueba con compañeros quedó fuera del alcance por decisión del estudiante. Este recorrido permite comprobar la aplicación y preparar la exposición.

## 1. Preparar la demostración

Abre la carpeta del proyecto en Visual Studio Code y ejecuta `INICIAR.cmd`. Mantén su consola abierta. Si tenías abierta una versión anterior, detenla con Ctrl+C y vuelve a iniciarla.

- Interfaz: [Champions Lab](http://127.0.0.1:8501/).
- API propia y documentación interactiva: [FastAPI](http://127.0.0.1:8000/docs).

Si la interfaz indica que no puede conectar con la API, revisa el mensaje de la consola antes de continuar.

## 2. Mostrar los datos — un minuto

En **Explorar partidos**, deja los filtros en Todas/Todos. La copia actual contiene **1.372 partidos, 96 equipos y 10 temporadas**, desde 2016-17 hasta 2025-26. Su último resultado tiene fecha **30/05/2026**. Comprueba también los filtros de las temporadas 2024-25 y 2025-26: cada una contiene 189 partidos en la fuente incluida.

Puedes explicar: «El proyecto utiliza datos históricos de OpenFootball. Conservamos la fuente y procesamos los resultados a 90 minutos más tiempo añadido. La copia no se actualiza en vivo y todavía no incluye 2026-27».

En **Calidad de los datos**, muestra la cobertura por temporada. “Completa según conteo de la fuente” significa que el conteo coincide con lo declarado por esa fuente; no implica una auditoría independiente de todos los marcadores.

## 3. Comparar equipos — un minuto

En **Comparar equipos**, selecciona:

| Campo | Valor |
|---|---|
| Equipo A | Real Madrid |
| Equipo B | Manchester City |
| Analizar partidos anteriores al | 02/06/2024 |

Pulsa **Comparar historial** y muestra **Últimos 5 partidos** y **Enfrentamientos directos**. Con ese corte, el dataset tiene **8 enfrentamientos directos**: 1 victoria de Real Madrid, 3 empates y 4 victorias de Manchester City, con 12 y 18 goles respectivamente a 90 minutos.

Explica: «La fecha es un límite exclusivo: sólo entran partidos anteriores a ese día. Comparamos la forma reciente y los duelos directos. La pantalla predictiva usa seis variables de forma reciente. El laboratorio de mejoras evalúa además información de duelos directos».

El encuentro del 17/04/2024 aparece como empate 1–1: la tanda de penales no cambia la etiqueta de resultado a 90 minutos.

## 4. Probar la predicción — dos minutos

En **Predicción experimental**, pulsa **Cargar ejemplo histórico**. Comprueba que el formulario tenga estos valores; también puedes introducirlos manualmente:

| Campo | Valor |
|---|---|
| Equipo local | Real Madrid |
| Equipo visitante | Manchester City |
| Fecha del escenario | 19/02/2025 |
| El partido se juega en sede neutral | Desmarcado |

Pulsa **Calcular estimación**. Cargar el ejemplo sólo completa el formulario; este segundo botón solicita el cálculo a la API. Revisa que aparezcan las tres probabilidades, el resultado más probable y la identificación del modelo utilizado. Las probabilidades suman 100 %, salvo pequeñas diferencias de redondeo en la pantalla.

Abre **Qué datos usó el modelo**: muestra una fila por equipo con cinco partidos previos, la fecha del último partido usado y los promedios de puntos, goles a favor y goles en contra. La fecha de ese último antecedente debe ser anterior al 19/02/2025. No son necesariamente cinco enfrentamientos entre ambos clubes: cada equipo aporta su historial contra distintos rivales.

Pulsa **Descargar estimación (JSON)** si necesitas guardar evidencia. El archivo contiene la respuesta completa de la API, incluidas las probabilidades, las seis variables y los identificadores de los partidos usados. Si cambias los equipos o la fecha, vuelve a pulsar **Calcular estimación**: el resultado visible identifica la última consulta realizada.

Para esta fecha corresponde el **modelo evaluado**, entrenado hasta el **08/05/2024**. La demostración reconstruye una estimación antes de un partido histórico; no es una predicción en vivo. No cambies la fecha por una anterior al entrenamiento para intentar reproducir un partido que el modelo ya conocía.

Puedes decir: «Usamos Random Forest, seleccionado por su F1 macro en validación frente a regresión logística. Recibe seis variables: los promedios de puntos, goles a favor y goles en contra de los últimos cinco partidos de Champions de cada equipo. Estima victoria local, empate o victoria visitante; no un marcador exacto ni quién clasifica».

Muestra las métricas de la prueba reservada de **2024-25**:

| Evidencia | Random Forest | Referencia de clase mayoritaria |
|---|---:|---:|
| Partidos evaluados | 154 | 154 |
| Aciertos | 85 | 79 |
| Accuracy | 55,19 % | 51,30 % |
| F1 macro | 0,3808 | 0,2260 |

Explica también la limitación principal: **el modelo no acertó ninguno de los 23 empates reales**. Los seis aciertos adicionales frente a la referencia no demuestran por sí solos estabilidad futura. Las probabilidades no están calibradas.

Estas cifras pertenecen al archivo `modelo_evaluado.joblib`. El archivo `modelo_actual.joblib` se reajustó con datos más recientes y **no tiene una prueba futura independiente**; no se le deben atribuir automáticamente las métricas anteriores.

## 5. Mostrar la evaluación de mejoras — un minuto

Abre **Evaluación de mejoras**. Muestra los 189 partidos disponibles de 2025-26, sus 164 utilizables y los 25 excluidos. La receta elegida fue logística equilibrada con trece variables, seleccionada por la media de F1 macro en las validaciones 2022-23, 2023-24 y 2024-25.

Compara la logística, RF6 y la referencia en esos mismos 164 partidos. La logística obtuvo 52,44 % de exactitud, F1 macro 0,456 y seis de 27 empates acertados. RF6 obtuvo 51,83 %, F1 macro 0,341 y cero empates acertados. Revisa también log loss, que fue peor para la logística, 1,014 frente a 0,971. El modelo elegido pronosticó 27 empates y acertó seis de ellos.

Explica que es una prueba retrospectiva con pesos entrenados hasta 2024-25. Los resultados de 2025-26 ya existían y habían formado parte del reajuste de la primera versión. La selección de recetas de este experimento utilizó temporadas anteriores. La pantalla **Predicción experimental** usa el Random Forest de la primera versión. Abre **Resultados por clase** y pulsa **Descargar evaluación (JSON)** para conservar el informe.

## 6. Enseñar la API y cerrar — un minuto

Abre la documentación de la API y muestra `GET /salud`: permite comprobar el estado del servicio y del modelo. Puedes presentar la arquitectura como **interfaz Streamlit → API FastAPI → procesamiento de datos y modelo scikit-learn**.

Si necesitas enseñar la evidencia del cálculo, abre `POST /predicciones`, pulsa **Try it out** y envía este cuerpo:

```json
{
  "local": "Real Madrid",
  "visitante": "Manchester City",
  "fecha": "2025-02-19",
  "sede_neutral": false
}
```

En la respuesta, revisa `historial`, `variables` y `probabilidades`. Para cada equipo, `partidos_usados` debe ser 5 y `fecha_ultimo_partido` debe ser anterior al 19/02/2025. `ids_historial` contiene los cinco identificadores que permiten buscar esos partidos en el CSV. Esta revisión de la API es opcional si el tiempo de exposición es limitado.

Puedes cerrar la demostración con estas palabras. «La aplicación permite consultar partidos, comparar equipos y pedir una estimación a nuestra API. En 2025-26, la regresión logística ampliada acertó seis de los 27 empates y mejoró el F1 macro frente al Random Forest. Su log loss fue peor. El siguiente paso de investigación es registrar cada pronóstico antes del partido y evaluarlo cuando se conozca el resultado a 90 minutos».

Para continuar con la exposición oral, vuelve a la diapositiva de conclusiones. [Presentación final](Presentacion_final_Champions.pptx) y [guion final](Guion_final.md).

## Comprobaciones manuales antes de exponer

Marca sólo las comprobaciones que hayas ejecutado y conserva una captura si necesitas evidencia.

- [ ] La interfaz y la documentación de la API abren desde los enlaces locales.
- [ ] Sin filtros aparecen 1.372 partidos, 96 equipos y 10 temporadas.
- [ ] Se pueden consultar 2024-25 y 2025-26, con 189 partidos cada una.
- [ ] Real Madrid–Manchester City, corte 02/06/2024, muestra los 8 duelos y el balance 1–3–4 descrito.
- [ ] Al cambiar el corte a 09/04/2024, quedan 6 duelos: no se incluye el partido de ese mismo día ni el del 17/04/2024.
- [ ] Cargar ejemplo histórico completa Real Madrid–Manchester City y 19/02/2025; Calcular estimación muestra las tres clases.
- [ ] Qué datos usó el modelo muestra dos equipos, cinco partidos por equipo y sus promedios.
- [ ] Descargar estimación (JSON) permite guardar la respuesta de la consulta mostrada.
- [ ] La respuesta de la API indica cinco partidos usados por equipo, conserva sus identificadores y sitúa su último partido antes del 19/02/2025.
- [ ] Esa estimación identifica el modelo evaluado y su entrenamiento hasta 08/05/2024.
- [ ] Con la opción de sede neutral marcada, el sistema informa que ese escenario no está admitido y no presenta una predicción nueva.
- [ ] El mismo club como local y visitante se rechaza con un mensaje comprensible.
- [ ] Evaluación de mejoras muestra 164 partidos evaluados y seis empates acertados por la logística.
- [ ] La comparación de log loss y las exclusiones están visibles y se puede descargar el informe.

Las cifras y limitaciones pueden revisarse en [MEJORAS_MODELO.md](MEJORAS_MODELO.md), [MODELO.md](MODELO.md), [metricas.json](../models/metricas.json) y [predicciones_prueba.csv](../models/predicciones_prueba.csv). El notebook de exploración conserva su código, pero se limpiaron sus salidas antiguas: ejecútalo de nuevo antes de usar sus resultados como evidencia de esta versión.

## Comprobación automatizada de la interfaz

El script [probar_interfaz.py](../scripts/probar_interfaz.py) recorre controles de Streamlit y consulta la API real. Requiere que el proyecto esté abierto con `INICIAR.cmd`; conserva esa primera terminal y abre una segunda en la carpeta del proyecto.

En la instalación compartida de este espacio de trabajo, ejecuta en PowerShell:

```powershell
& "../../work/champions_env/Scripts/python.exe" scripts/probar_interfaz.py
```

Si descargaste el repositorio en otra carpeta y `INICIAR.cmd` creó el entorno local `.venv`, usa en su lugar:

```powershell
& ".venv/Scripts/python.exe" scripts/probar_interfaz.py
```

Lee el resultado en la terminal y conserva su salida si necesitas evidencia. La existencia del script no significa que haya pasado en tu equipo: sólo una ejecución que termine correctamente confirma sus comprobaciones. Este recorrido automatizado complementa la lista manual anterior. Revisa también el aspecto visual al preparar la exposición.

La verificación del 09/11/2026 completó 47 pruebas de datos, API y modelo y 19 comprobaciones de interfaz con AppTest y la API local. La decisión de entrega mantiene Random Forest v1 en la pantalla predictiva y presenta el experimento de trece variables como evidencia en Evaluación de mejoras.
