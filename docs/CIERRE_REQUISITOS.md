# Revisión de requisitos de Champions Lab

**Alcance.** Se revisó la versión local del proyecto contra la sección 6 del [informe de avance](Informe_proyecto_Champions.docx), los seis objetivos de la propuesta y la consigna de presentar objetivos, API propia, interfaz con UI/UX y exposición con diapositivas.

**Resultado.** Los ocho requisitos funcionales y los siete no funcionales cuentan con evidencia en la aplicación local. Para RNF-01 se verificaron controles, estados y mensajes. Por decisión del estudiante, las sesiones con compañeros quedaron fuera del alcance. La entrega incluye el [informe final](Informe_final_Champions.pdf), la presentación y el guion.

| ID | Qué se pidió | Evidencia en el proyecto local |
|---|---|---|
| RF-01 | Cargar partidos y conservar su origen | El CSV tiene 1.372 filas con identificador y enlace a la línea original. El manifiesto identifica el origen de cada temporada. |
| RF-02 | Filtrar por temporada, equipo, fase y resultado | La API y la pantalla **Explorar partidos** admiten los cuatro filtros. Combinados para 2024-25, Real Madrid, Playoffs y victoria local, devuelven el partido del 19/02/2025 contra Manchester City. |
| RF-03 | Mostrar cobertura y calidad | **Calidad de los datos** muestra diez temporadas, conteos, duplicados, faltantes, prórrogas y limitaciones. |
| RF-04 | Comparar dos equipos con una fecha de corte exclusiva | La API toma hasta cinco partidos anteriores por equipo. La pantalla distingue esa forma reciente de los cruces directos. Con Madrid–City aparecen ocho cruces antes del 02/06/2024 y seis antes del 09/04/2024. |
| RF-05 | Descargar la selección en CSV | La descarga recibe los mismos filtros que la tabla. Las comprobaciones incluyen exportaciones de 189 partidos para cada una de las temporadas 2024-25 y 2025-26. |
| RF-06 | Ofrecer una API propia documentada | FastAPI expone las rutas de consulta y predicción y añade `GET /experimentos/mejoras`. Valida equipos y fechas y comunica los errores. |
| RF-07 | Consultar un clasificador evaluado | El servicio comprueba los artefactos y devuelve tres probabilidades. El ejemplo del 19/02/2025 usa el modelo entrenado hasta el 08/05/2024. |
| RF-08 | Presentar resultados y limitaciones | La pantalla muestra fecha, modelo, tres clases, métricas, límites y avisos para consultas fuera de alcance. |

| ID | Qué se pidió | Evidencia y estado |
|---|---|---|
| RNF-01 | Usabilidad | Hay etiquetas, indicación de carga, estados vacíos y mensajes de error. El estudiante decidió excluir la prueba con compañeros del alcance de esta entrega. |
| RNF-02 | Reproducibilidad de la preparación | Se regeneraron partidos, programados, nombres normalizados y reporte de calidad en una carpeta temporal con los originales incluidos y la fecha de referencia del reporte. Los cuatro archivos coincidieron byte por byte. |
| RNF-03 | Trazabilidad | Cada registro de partidos conserva un ID y la URL de la línea de OpenFootball en la revisión utilizada. |
| RNF-04 | Integridad temporal | Las variables usan encuentros anteriores al día objetivo. El modelo evaluado se seleccionó en 2023-24 y se probó en 2024-25. Hay pruebas para cambios de datos del propio día y posteriores. |
| RNF-05 | Mantenibilidad | La interfaz está en `app.py`. El servicio, el procesamiento del modelo, la preparación de datos y las pruebas tienen módulos separados. |
| RNF-06 | Transparencia | La interfaz identifica OpenFootball como fuente comunitaria y muestra el último resultado del 30/05/2026. El informe inicial abarcaba hasta junio de 2024. La tercera diapositiva de la presentación final documenta las diez temporadas del dataset ampliado. |
| RNF-07 | Manejo de errores | Un historial insuficiente o una sede neutral generan un error. La ausencia o desactualización del modelo impide calcular la estimación. |

La propuesta incluía preparar y analizar datos, entrenar, evaluar, construir una interfaz e interpretar los resultados. Hay evidencia para los seis objetivos. En la prueba de 2024-25 el modelo acertó 85 de 154 encuentros, frente a 79 de la referencia simple, y acertó 0 de 23 empates. El informe pide medir y explicar el rendimiento y no fija un mínimo de aciertos. Para esta entrega se utiliza el Random Forest de la primera versión en la pantalla predictiva. La versión 0.4 añade una evaluación retrospectiva de trece variables. En los mismos 164 partidos de 2025-26, la logística seleccionada acertó seis de 27 empates y RF6 acertó cero. La clasificación mejoró y el log loss empeoró. [Metodología del primer modelo](MODELO.md) y [evaluación de mejoras](MEJORAS_MODELO.md).

## Evidencia para la entrega

- Utilizar la [guía de demostración](PRUEBA_Y_DEMO.md) para mostrar la API, la interfaz y los resultados. El 9 de noviembre de 2026 se ejecutaron correctamente 47 pruebas de datos, API y modelo y 19 comprobaciones de interfaz con la API local.
- Exponer la cobertura, la división temporal y los resultados con la [presentación final de diez diapositivas](Presentacion_final_Champions.pptx) y el [guion correspondiente](Guion_final.md).
- El 11 de noviembre de 2026, la copia de entrega pasó las mismas 47 pruebas y 19 comprobaciones en un entorno nuevo de Windows x64 con Python 3.12.14 y las 52 dependencias fijadas. La presentación oral y el envío a la plataforma del curso corresponden al estudiante. [Repositorio del proyecto](https://github.com/yeryxtein/champions-league-predictor-yerson).

## Alcance acordado

El estudiante decidió continuar el desarrollo sin realizar sesiones con compañeros. Esa actividad queda excluida del cierre y su estado se registra como decisión de alcance. Las comprobaciones automatizadas y la revisión de la aplicación aportan la evidencia técnica de esta entrega.
