# Modelo de predicción: método, evaluación y límites

Este proyecto utiliza aprendizaje supervisado para estimar tres resultados a **90 minutos más tiempo añadido**: victoria del local, empate o victoria del visitante. No estima un marcador exacto ni quién clasifica una eliminatoria. Las prórrogas y tandas de penales no forman parte de la etiqueta.

El modelo es un primer experimento académico. Sus probabilidades no están calibradas y no expresan certeza. La evaluación se limita a los partidos que cumplen los requisitos descritos aquí; no demuestra que el modelo funcione igual en todos los equipos o temporadas.

## Variables y prevención de fuga de información

Para cada equipo se calculan tres promedios sobre sus **últimos cinco partidos de Champions anteriores al día objetivo**:

| Variable | Cálculo |
|---|---|
| Puntos | Promedio de 3 por victoria, 1 por empate y 0 por derrota |
| Goles a favor | Goles anotados a 90 minutos, divididos entre cinco |
| Goles en contra | Goles recibidos a 90 minutos, divididos entre cinco |

El total es de seis variables: tres del local y tres del visitante. Se requieren cinco encuentros anteriores de cada uno. Si alguno no los tiene, el partido queda excluido del entrenamiento y evaluación, o la API devuelve un mensaje de historial insuficiente. No se completa su historial con ceros ni con resultados futuros.

Los cinco partidos pueden pertenecer a temporadas diferentes. Se muestran la fecha del último partido usado y los días transcurridos, con aviso cuando supera un año. No se incluye el rendimiento en otras ligas, lesiones, alineaciones, fichajes, valor de mercado ni estadísticas que no estén en el dataset.

La condición aplicada es `fecha_historial < fecha_objetivo`: no se admite ningún partido del mismo día. Los identificadores de las cinco filas usadas se devuelven en la respuesta para poder revisar el cálculo. El marcador y el resultado del encuentro objetivo nunca son variables.

El historial cara a cara que muestra la aplicación es una comparación descriptiva independiente. En esta primera versión no se usa como variable del modelo porque algunas parejas tienen muy pocos enfrentamientos previos.

## Sedes y exclusiones

La fuente comunitaria no ofrece una columna uniforme y auditada de sede neutral. Como primera aproximación conservadora se excluyen como objetivos:

- Todas las finales.
- Toda la temporada 2020-21, por las sedes excepcionales no auditadas.
- Octavos, cuartos y semifinales de 2019-20 jugados desde el 1 de agosto de 2020. La regla excluye también encuentros que pudieron jugarse en el estadio habitual; se prioriza no afirmar que todas sus sedes fueron verificadas.
- Encuentros sin cinco partidos previos disponibles para cualquiera de los dos clubes.

Una fila recibe un solo motivo principal de exclusión, en ese orden. Todas las filas originales permanecen en el dataset de consulta. `models/variables_y_exclusiones.csv` conserva la decisión de cada partido.

Los partidos excluidos por sede sí pueden aparecer en la **forma previa**, que usa puntos y goles desde la perspectiva del equipo, sin distinguir su condición local o visitante. No se usan como ejemplos cuya etiqueta represente una ventaja de campo. Las demás sedes tampoco cuentan con una auditoría exhaustiva: sigue siendo una limitación de la fuente.

La API rechaza partidos marcados como sede neutral y encuentros existentes sujetos a las exclusiones anteriores. Para una combinación hipotética se supone el estadio habitual del local y se informa de esa suposición.

## Modelos comparados

| Modelo | Función y configuración |
|---|---|
| DummyClassifier | Referencia con `strategy="prior"`: probabilidades iguales a las frecuencias de clase del entrenamiento; el resultado estimado es la clase mayoritaria |
| Regresión logística | `StandardScaler` y `LogisticRegression` dentro de una sola Pipeline; `C=1`, `max_iter=2000`, `random_state=42` |
| Random Forest | 300 árboles, profundidad máxima 6, mínimo 6 muestras por hoja, `random_state=42`, `n_jobs=1` |

El escalador se ajusta únicamente con la partición utilizada para entrenar cada modelo. La Pipeline evita calcular medias o escalas con datos reservados. No se buscan hiperparámetros utilizando la prueba.

Se elige entre regresión logística y Random Forest por **mayor F1 macro en validación**. Si coinciden, se prefiere el de menor log loss. La referencia Dummy se informa por separado. Si el modelo elegido no la supera en prueba, se muestra ese resultado; no se cambia de algoritmo para mejorar artificialmente la cifra de prueba.

## División temporal

| Etapa | Datos y uso |
|---|---|
| Entrenamiento inicial | Temporadas anteriores a 2023-24, con las exclusiones indicadas |
| Validación | Temporada 2023-24; permite elegir entre los dos algoritmos |
| Entrenamiento del modelo evaluado | Se vuelve a ajustar el algoritmo elegido con entrenamiento inicial más validación |
| Prueba reservada | Temporada 2024-25; sólo después de seleccionar el algoritmo se calcula su resultado y el de la referencia |
| Reajuste actual | Todos los partidos elegibles disponibles, incluida 2025-26; produce un archivo distinto |

La separación es por temporadas, sin mezcla aleatoria de partidos. La prueba requiere al menos 20 encuentros y las tres clases; el entrenamiento requiere al menos 60 y la validación al menos 20. Si no se cumple, el script se detiene sin publicar un nuevo modelo.

En validación y prueba se realiza una simulación con la información de cada día: al estimar un encuentro se pueden usar resultados de **días anteriores de la misma temporada**, ya terminados para entonces. Los parámetros del modelo permanecen congelados durante esa evaluación. Esto representa predicciones antes de cada partido, no una predicción de toda la temporada realizada el primer día.

La muestra de prueba sólo representa los equipos con suficiente historial y los partidos sin las exclusiones anteriores. El formato de Champions cambia desde 2024-25, por lo que también cambia la cantidad de partidos y la distribución de rivales. No debe suponerse que el resultado de una sola temporada permanecerá igual en el futuro.

## Métricas y evidencia

El informe generado en `models/metricas.json` contiene:

- **Accuracy:** proporción de partidos cuyo resultado más probable coincide con el real.
- **F1 macro:** promedio del F1 de Local, Empate y Visitante, dando el mismo peso a cada clase.
- **Log loss:** evalúa las probabilidades asignadas al resultado real; menor es mejor y penaliza errores muy seguros.
- **Matriz de confusión:** filas = resultado real, columnas = estimado; orden explícito Local, Empate, Visitante.
- Soporte de cada clase, total de partidos, exclusiones y rango de fechas por partición.
- Modelos y resultados de validación, resultado final de prueba y comparación con Dummy.
- Hash SHA-256 del CSV, firmas de los artefactos y versiones de Python, pandas, scikit-learn y joblib.

`models/predicciones_prueba.csv` permite inspeccionar cada resultado real, estimado y sus tres probabilidades. Las probabilidades siempre se ordenan por nombre de clase y suman uno; no se presupone el orden interno del estimador.

### Resultados de esta versión

La ejecución realizada con 1.372 partidos hasta el 30 de mayo de 2026 seleccionó **Random Forest**. La validación contenía 96 partidos: su F1 macro fue 0,4576 frente a 0,4101 de regresión logística y 0,2253 de Dummy. Ambos modelos de aprendizaje obtuvieron 58,33 % de accuracy en esa validación; la selección se hizo con F1 macro, como estaba definido.

| Partición | Total disponible | Utilizable | Excluido |
|---|---:|---:|---:|
| Entrenamiento inicial: 2016-17 a 2022-23 | 869 | 481 | 388 |
| Validación: 2023-24 | 125 | 96 | 29 |
| Prueba: 2024-25 | 189 | 154 | 35 |
| Reajuste actual: todas las temporadas | 1.372 | 895 | 477 |

El modelo evaluado se ajustó con **577 partidos** (481 + 96), hasta el 8 de mayo de 2024. El modelo actual se ajustó con 895 partidos, hasta el 6 de mayo de 2026. Las finales posteriores a esas fechas siguen en el dataset de consulta, pero se excluyeron como objetivos del entrenamiento.

| Métrica de prueba 2024-25 | Random Forest | Referencia Dummy |
|---|---:|---:|
| Partidos | 154 | 154 |
| Accuracy | 55,19 % (85 aciertos) | 51,30 % (79 aciertos) |
| F1 macro | 0,3808 | 0,2260 |
| Log loss | 0,9753 | 1,0029 |

La mejora observada de accuracy es de **3,90 puntos porcentuales**, equivalente a seis aciertos adicionales en esa muestra. Es una diferencia descriptiva de una sola temporada; no se ha demostrado significación estadística ni estabilidad en temporadas futuras.

La matriz de confusión del modelo evaluado es:

| Resultado real / estimado | Local | Empate | Visitante | Total real |
|---|---:|---:|---:|---:|
| Local | 62 | 0 | 17 | 79 |
| Empate | 19 | 0 | 4 | 23 |
| Visitante | 27 | 2 | 23 | 52 |

**No acertó ninguno de los 23 empates reales.** Aunque mejora la referencia en los indicadores globales, ese fallo es una limitación concreta del modelo. La siguiente iteración deberá trabajar esa clase y volver a evaluarse con un procedimiento temporal separado; esta prueba no debe convertirse en un conjunto para ajustar parámetros repetidamente.

## Dos archivos de modelo, dos alcances

`modelo_evaluado.joblib` sólo aprendió con las temporadas anteriores a la prueba y es el que tiene métricas independientes de 2024-25. Para demostrar un partido histórico posterior a su último día de entrenamiento, la API puede utilizar este modelo congelado.

`modelo_actual.joblib` se reajusta con todos los datos elegibles. **No tiene una nueva evaluación futura independiente.** No se le atribuyen las cifras de prueba del archivo anterior.

La API elige el modelo actual únicamente si su último día de entrenamiento es **estrictamente anterior** a la fecha solicitada. En caso contrario utiliza el modelo evaluado si cumple esa condición. Si ninguno la cumple, rechaza la solicitud: aplicar un modelo que ya aprendió el resultado del día o de días posteriores produciría una evaluación engañosa.

También se limita la fecha solicitada a un máximo de 365 días posteriores al último registro del dataset. Esta es una restricción operativa del prototipo, no un horizonte de precisión validado. Las fechas futuras usan el modelo reajustado y únicamente el historial disponible: se informa de la fecha final de los datos y del número de días sin resultados actualizados. No se afirma describir la forma real de los equipos meses después.

## Reproducción

Con las dependencias de `requirements-lock.txt` instaladas, ejecutar desde la carpeta del proyecto:

```powershell
python scripts/preparar_datos.py
python scripts/entrenar_modelo.py
python -m unittest discover -s tests -v
```

Después hay que reiniciar la API y la interfaz para cargar la nueva copia. Si el CSV cambia después del entrenamiento, el servicio bloquea las predicciones y solicita volver a entrenar. Si la API conserva el CSV anterior en memoria, lo detecta mediante una firma de su contenido y pide reiniciar.

El entrenamiento genera los dos archivos de modelo, el informe de métricas, las variables con exclusiones y las predicciones de prueba. No se necesita internet para entrenar con los datos ya incluidos. Se deben cargar únicamente los artefactos locales producidos por este proyecto: el formato joblib no está diseñado para ejecutar archivos de origen desconocido.

## Contrato de integración

```python
from ml.model_service import get_status, predict_match

estado = get_status()  # estado: entrenado, pendiente, desactualizado o no_disponible
resultado = predict_match(DATA, "Real Madrid", "Manchester City", "2025-02-19")
```

`get_status()` devuelve el informe completo cuando está listo; de lo contrario devuelve `estado` y `mensaje`. `predict_match` acepta un DataFrame del mismo dataset, dos clubes, fecha ISO o `date` y el indicador opcional `sede_neutral=False`. Su respuesta incluye `probabilidades`, `resultado_mas_probable`, `version_modelo`, `entrenado_hasta`, `historial`, `variables` y `advertencias`.

`PredictionError` indica una solicitud fuera del alcance (HTTP 422). `ModelUnavailableError` indica que el modelo o los datos necesitan preparación o reinicio (HTTP 503). La API valida además nombres, fechas y formato de la petición.

## Pruebas automatizadas

`tests/test_modelo.py` comprueba que cambiar resultados del día objetivo y futuros no modifica sus variables; exige cinco antecedentes; verifica exclusiones, fechas de entrenamiento y orden de probabilidades; comprueba log loss, suma de probabilidades y detección de un dataset modificado. Con los artefactos presentes también reproduce una predicción reservada y comprueba que sus identificadores no aparecen en el entrenamiento.

## Referencias técnicas

- [Documentación de DummyClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.dummy.DummyClassifier.html).
- [Errores frecuentes y prevención de fuga de información](https://scikit-learn.org/stable/common_pitfalls.html).
- [Definición de log loss y orden de etiquetas](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html).
- [Fuente de partidos: OpenFootball](https://github.com/openfootball/champions-league); la revisión exacta y las correcciones auditadas están documentadas en los archivos de datos del proyecto.
