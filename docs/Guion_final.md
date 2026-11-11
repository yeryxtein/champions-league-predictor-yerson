# Guion de exposición de Champions Lab

Duración orientativa de seis a ocho minutos. Versión 0.4 del 9 de noviembre de 2026.

## 1 Presentación

Mi proyecto analiza resultados históricos de Champions y estima tres clases a 90 minutos. Hoy presento una aplicación funcional, un primer modelo evaluado y un experimento con variables adicionales. La interfaz consulta una API propia.

## 2 Problema y objetivos

La fuente contiene muchos resultados y el proyecto busca analizarlos de manera sistemática. Organicé los objetivos en preparación de datos, variables disponibles antes del encuentro, entrenamiento, evaluación, API, interfaz y análisis de resultados. Cada objetivo tiene evidencia en el repositorio y en la demostración.

## 3 Dataset

Convertimos los archivos de texto a CSV, unificamos nombres y conservamos enlaces a la línea original. El dataset tiene diez temporadas. Hay dos correcciones de marcadores con prórroga documentadas con fuentes oficiales. La cobertura coincide con los conteos declarados por la fuente. Los datos terminan el 30 de mayo de 2026.

## 4 Arquitectura

La interfaz y la API son servicios separados. El servicio carga el CSV y los artefactos, valida los equipos y la fecha y obtiene las probabilidades. Hay rutas de equipos, partidos, resumen, calidad, descarga, comparación, predicción y evaluación. La documentación interactiva está en http://127.0.0.1:8000/docs.

## 5 Modelo activo

Se compararon la referencia de clase mayoritaria, la regresión logística y Random Forest. Elegimos Random Forest por su F1 macro en 2023-24. Lo reajustamos con 577 encuentros hasta el 8 de mayo de 2024 y medimos sus resultados en 2024-25. La aplicación también dispone de un modelo reajustado con los 895 encuentros elegibles. Su desempeño en partidos futuros sigue por medir. Las variables se calculan sólo con partidos anteriores al día objetivo.

## 6 Resultados del modelo activo

La mejora global frente a la referencia es modesta. El modelo acertó seis partidos adicionales y tuvo dificultades claras con la clase empate. El conjunto original de prueba tuvo 189 encuentros disponibles, de los cuales se evaluaron 154 por los requisitos de historial y sede. Accuracy cuenta aciertos globales. F1 macro da el mismo peso a las tres clases. Log loss evalúa las probabilidades y se interpreta mejor cuanto menor es.

## 7 Experimento ampliado

A las seis variables previas añadimos siete variables sobre empates, fuerza Elo y enfrentamientos directos. Se compararon dos Random Forest ampliados, dos regresiones logísticas ampliadas y la receta RF6. Se guardó la selección antes de calcular la prueba 2025-26. La logística equilibrada fue elegida por la media de F1 macro. Esta evaluación es retrospectiva, con resultados históricos ya disponibles.

## 8 Comparación ampliada

Los tres modelos de prueba se ajustaron con los mismos 731 encuentros anteriores a 2025-26. Se excluyeron 24 partidos por historial insuficiente y la final por sede neutral. La logística acertó seis empates, pero pronosticó 27 empates y falló en 21 de esas ocasiones. Su ventaja de exactitud fue un solo acierto. La calidad de las probabilidades medida con log loss empeoró respecto a RF6. El 55,19 por ciento de la slide anterior usa otra temporada y otra muestra. La aplicación conserva RF v1 como predictor y presenta el experimento en una sección aparte.

## 9 Demostración

En la pantalla puedo mostrar los datos, su procedencia y los filtros. Al comparar equipos distingo la forma reciente de sus enfrentamientos directos. El ejemplo histórico de Madrid y City usa un modelo entrenado antes de su fecha. La descarga JSON registra la emisión, la copia del dataset y el modelo. En la sección de mejoras enseño las cifras de 2025-26. La verificación realizada el 9 de noviembre de 2026 superó 47 pruebas y 19 comprobaciones de interfaz. Las sesiones con compañeros se excluyeron por decisión del estudiante.

## 10 Conclusiones

La API, la interfaz, el dataset y el primer modelo están implementados y comprobados. La evaluación adicional mejoró el F1 macro y obtuvo un peor log loss. La cobertura de OpenFootball llega hasta mayo de 2026 y las variables describen resultados históricos de Champions. Una futura evaluación permitiría registrar cada pronóstico antes del inicio y contrastarlo después con el resultado a 90 minutos. La copia local reúne el código, los datos y los resultados que utilicé en esta demostración.

## Enlaces para la demostración

- [Presentación final](Presentacion_final_Champions.pptx)
- [Interfaz para la demostración](http://127.0.0.1:8501)
- [Documentación de la API](http://127.0.0.1:8000/docs)
- [Repositorio del estudiante](https://github.com/yeryxtein/champions-league-predictor-yerson)

Conserva la consola de INICIAR.cmd abierta durante la exposición.
