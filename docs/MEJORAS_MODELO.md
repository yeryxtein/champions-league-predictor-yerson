# Evaluación de nuevas variables y modelos

La versión 0.4 añade una evaluación retrospectiva de 2025-26. La selección de cinco recetas se realizó con validaciones temporales anteriores. El procedimiento eligió regresión logística equilibrada con trece variables. En los 164 encuentros de prueba acertó seis de los 27 empates reales y obtuvo F1 macro 0,456. El Random Forest de seis variables obtuvo F1 macro 0,341 en esos mismos partidos y acertó cero empates.

## Variables y candidatos

Las seis variables de la primera versión resumen puntos, goles a favor y goles en contra de los últimos cinco partidos de cada equipo. Se añadieron siete variables.

| Variable añadida | Cálculo previo al encuentro |
|---|---|
| Frecuencia de empates del local y del visitante | Dos proporciones calculadas sobre sus cinco antecedentes de Champions |
| Diferencia Elo | Fuerza acumulada del local menos la del visitante, con valores iniciales 1.500 y K=20, sin bonificación por localía |
| Cantidad de enfrentamientos directos | Hasta cinco cruces anteriores, con ambas localías |
| Tres proporciones suavizadas de enfrentamientos directos | Victoria del local, empate y victoria del visitante desde la perspectiva del encuentro objetivo. Cada clase parte de un pseudoconteo de uno |

Cuando faltan cruces directos, su cantidad es cero y cada proporción suavizada vale un tercio. Se sigue exigiendo que cada club tenga cinco partidos anteriores de Champions. Todos los ejemplos de un día se calculan antes de incorporar sus resultados al historial y al Elo.

Se compararon Random Forest con seis variables, Random Forest ampliado, Random Forest ampliado equilibrado, regresión logística ampliada y regresión logística ampliada equilibrada. Las configuraciones completas están en el manifiesto de selección. [Selección registrada](../models/experimento_v2/seleccion.json).

## Protocolo temporal

1. Cada validación utiliza una temporada entre 2022-23, 2023-24 y 2024-25. Su entrenamiento sólo recibe temporadas anteriores.
2. Se elige la mayor media por temporada de F1 macro. Los desempates usan menor log loss medio y luego el nombre de la receta.
3. La elección se guarda antes de calcular la prueba de 2025-26.
4. La receta elegida, RF6 y la referencia Dummy se ajustan con los mismos 731 partidos elegibles hasta el 07/05/2025. Sus pesos quedan congelados durante la prueba.
5. Cada encuentro de prueba usa resultados de días anteriores, incluidos los ya terminados de la propia temporada.

| Candidato | F1 macro medio de validación | Log loss medio |
|---|---:|---:|
| RF6 | 0,4244 | 0,9837 |
| RF ampliado | 0,4052 | 0,9573 |
| RF ampliado equilibrado | 0,4310 | 1,0012 |
| Logística ampliada | 0,4202 | 0,9533 |
| Logística ampliada equilibrada | **0,4504** | 1,0135 |

El protocolo seleccionó la logística equilibrada por el criterio definido de F1 macro. La temporada 2025-26 se reservó de esta selección.

## Resultados en los mismos 164 partidos

La fuente contiene 189 partidos en 2025-26. Se excluyeron 24 por historial insuficiente y la final por sede neutral. Entre los 164 utilizables hubo 85 victorias locales, 27 empates y 52 victorias visitantes.

| Métrica de prueba 2025-26 | Logística ampliada equilibrada | RF6 | Dummy de clase mayoritaria |
|---|---:|---:|---:|
| Aciertos totales | 86 | 85 | 85 |
| Exactitud | 52,44 % | 51,83 % | 51,83 % |
| F1 macro | 0,4559 | 0,3406 | 0,2276 |
| Log loss, menor es mejor | 1,0137 | 0,9709 | 1,0056 |
| Empates reales | 27 | 27 | 27 |
| Empates pronosticados | 27 | 1 | 0 |
| Empates acertados | 6 | 0 | 0 |

La receta elegida mejora F1 macro y añade un acierto total frente a RF6. Recupera el 22,22 % de los empates reales. De sus 27 pronósticos de empate, seis fueron correctos y 21 fueron errores. El log loss empeora en aproximadamente 0,043 respecto de RF6, por lo que la mejora de clasificación convive con un peor resultado de probabilidades en esta muestra. Las probabilidades continúan sin calibración adicional.

| Resultado real / estimado de la logística | Local | Empate | Visitante |
|---|---:|---:|---:|
| Local | 51 | 11 | 23 |
| Empate | 8 | 6 | 13 |
| Visitante | 13 | 10 | 29 |

El 55,19 % mostrado en la primera versión pertenece a 154 partidos de 2024-25. La comparación de mejoras de esta sección utiliza 2025-26 y sus 164 partidos para los tres modelos. Cada cifra debe presentarse junto a su temporada y muestra.

## Decisión de integración y alcance

La pantalla **Predicción experimental** utiliza el Random Forest de la primera versión. La nueva pantalla **Evaluación de mejoras** presenta la comparación de trece variables, las matrices y la descarga del informe. La elección de receta identifica el resultado del procedimiento experimental. La decisión para esta entrega es utilizar RF v1 como predictor activo y reportar el experimento ampliado como evidencia. La mejora de F1 macro y el empeoramiento de log loss se documentan juntos para evaluar su integración en una versión posterior.

Esta es una evaluación retrospectiva. Los resultados de 2025-26 ya existían y habían formado parte del reajuste del modelo actual de la primera versión. Para este experimento, las recetas se seleccionaron con temporadas anteriores y los tres modelos de prueba se entrenaron hasta 2024-25. Una prueba prospectiva requiere guardar pronósticos antes de los partidos y contrastarlos después con sus resultados reales. Las conclusiones de una temporada necesitan confirmación en partidos futuros.

## Reproducción y evidencia

Con las dependencias instaladas, ejecuta desde la carpeta del proyecto.

```powershell
.venv\Scripts\python.exe scripts/evaluar_mejoras.py
```

En este espacio de trabajo también está disponible `../../work/champions_env/Scripts/python.exe`. El protocolo es fijo. Si se cambia la configuración después de examinar esta prueba, habrá que registrar la nueva iteración y su procedimiento de evaluación.

- `models/experimento_v2/seleccion.json` conserva la elección, las particiones y la configuración.
- `models/experimento_v2/informe.json` registra métricas, exclusiones, fecha, versión del código y hashes.
- `models/experimento_v2/predicciones.csv` permite inspeccionar las tres probabilidades de cada partido para cada modelo.

La API entrega el informe mediante `GET /experimentos/mejoras`. Comprueba la integridad de los datos, el código, el protocolo, la selección y las predicciones antes de presentar sus resultados. [Informe generado](../models/experimento_v2/informe.json).

## Verificación de la versión

El 9 de noviembre de 2026 se completaron 47 pruebas de datos, API y modelo y 19 comprobaciones de interfaz con AppTest y peticiones HTTP a la API local. El recorrido incluye la página de evaluación ampliada y sus estados de disponibilidad.
