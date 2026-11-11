# Diccionario y preparación

La tabla `processed/partidos.csv` contiene una fila por partido con resultado disponible. Codificación UTF-8 con BOM. No se incluyen rondas clasificatorias. El formato de sus 17 columnas se mantiene compatible con la API y el modelo.

| Columna | Significado |
|---|---|
| id | Identificador estable calculado a partir de temporada, fecha y equipos |
| temporada | Temporada, por ejemplo 2023-24 |
| fecha | Fecha del partido en formato AAAA-MM-DD |
| fase | Grupos, Liga, Playoffs, Octavos, Cuartos, Semifinal o Final |
| local / visitante | Nombres unificados, designados así en la fuente |
| pais_local / pais_visitante | Código de país de tres letras, conservado de la fuente |
| goles_local_90 / goles_visitante_90 | Goles tras 90 minutos más tiempo añadido, sin prórroga ni penales |
| resultado | Local, Empate o Visitante. Etiqueta derivada de los goles a 90 minutos |
| hubo_prorroga / hubo_penales | Indicadores del formato original del encuentro |
| local_original / visitante_original | Nombres sin normalización |
| marcador_original | Texto del resultado sin modificar |
| fuente | Enlace permanente al archivo y línea de origen |

## Reglas

1. La fecha toma el año explícito si existe. En los demás casos, los grupos usan el año inicial y las eliminatorias el año final de la temporada. Para la fase liga, los meses de enero a junio pertenecen al segundo año. Esto cubre enero de las temporadas nuevas y las eliminatorias de agosto de 2020. Se verifica el día de la semana y se rechazan resultados con fecha futura respecto de `--fecha-referencia` (por defecto, fecha local de ejecución).
2. El mapa explícito de 26 aliases del script unifica variantes del mismo club, por ejemplo `Juventus FC` / `Juventus`, `Atalanta BC` / `Atalanta` y `Bayer 04 Leverkusen` / `Bayer Leverkusen`. `equipos_normalizados.csv` conserva la correspondencia completa.
3. En `4-2 a.e.t. (1-2, 0-0)`, el resultado a 90 minutos es **1-2**. En `3-4 pen. 1-1 a.e.t. (1-1, 0-1)`, es **1-1**. Se conservan los textos originales para revisión.
4. El procesamiento se detiene si una línea no se reconoce, si hay más partidos que los declarados o si aparecen duplicados. Si faltan registros o resultados, la temporada se marca **Parcial** y se informa la diferencia respecto al encabezado. No se omiten silenciosamente partidos.
5. El script comprueba los hashes de los archivos originales y la licencia contra `fuentes.json`. La descarga fija todas las temporadas a un mismo commit; `--commit` permite reproducir una versión.
6. Los encuentros sin marcador se conservan en `processed/programados.csv`, con las mismas columnas más `estado`: `Programado` para fecha igual o posterior a la de referencia y `Sin resultado` para fechas anteriores. Los goles, resultado y banderas de prórroga/penales quedan vacíos. No pasan a `partidos.csv`, no se convierten en empates y no deben usarse para entrenar. El archivo se guarda con encabezados aunque no haya filas.
7. Las correcciones verificadas se describen en `correcciones_90min.json`. `marcador_original` y los TXT se conservan intactos; `calidad.json` registra cada corrección aplicada, su identificador y fuente de verificación. Si el marcador original cambia de forma incompatible, el proceso se detiene para revisión.

## Correcciones verificadas a 90 minutos

OpenFootball omite la etiqueta de prórroga en dos registros de 2024-25. Se corrigen los campos calculados, manteniendo el valor original:

| Partido | Fecha | Marcador original | Marcador a 90 minutos | Evidencia |
|---|---|---|---|---|
| PSV Eindhoven - Juventus | 2025-02-19 | 3-1 (0-0) | 2-1 | [Acta UEFA, páginas 1 y 2](https://www.uefa.com/newsfiles/UCL/2025/2044483_FR.pdf): el tercer gol llegó en el minuto 98 |
| Inter - FC Barcelona | 2025-05-06 | 4-3 (2-0) | 3-3 | [Crónica UEFA](https://www.uefa.com/uefachampionsleague/news/0299-1db1e0d054c8-02dafe0b7237-1000--inter-4-3-barcelona-aet-agg-7-6-davide-frattesi-settles-/): empate en 90+3 y gol decisivo en la prórroga |

## Alcance de los controles

La versión procesada el **29 de octubre de 2026** contiene **1.372 partidos y 96 clubes unificados**, desde el 13 de septiembre de 2016 hasta el 30 de mayo de 2026. Hay 16 prórrogas, de las que 6 incluyen penales. No hay duplicados ni valores vacíos en los campos de `partidos.csv`.

| Temporada | Resultados disponibles | Conteo declarado por la fuente |
|---|---:|---:|
| 2016-17 | 125 | 125 |
| 2017-18 | 125 | 125 |
| 2018-19 | 125 | 125 |
| 2019-20 | 119 | 119 |
| 2020-21 | 125 | 125 |
| 2021-22 | 125 | 125 |
| 2022-23 | 125 | 125 |
| 2023-24 | 125 | 125 |
| 2024-25 | 189 | 189 |
| 2025-26 | 189 | 189 |

Cada una de las temporadas nuevas contiene 144 partidos de liga, 16 de playoffs y 29 desde octavos hasta la final. No hay encuentros sin resultado en esta copia. La etiqueta **Completa según conteo de la fuente** sólo describe esta reconciliación; no prueba que cada resultado de la fuente comunitaria sea correcto ni sustituye una auditoría independiente. No incluye la temporada 2026-27 ni se actualiza automáticamente.

`processed/calidad.json` expone `cobertura_temporadas` con resultados disponibles, registros sin resultado, registros ausentes respecto al encabezado, porcentaje de cobertura, última fecha y fases. `partidos_sin_resultado` cuenta los registros conservados en `programados.csv`. `registros_descartados` es cero porque todo registro reconocido se conserva en una de las dos tablas.

El dataset no tiene una columna uniforme de sede neutral, lesiones ni alineaciones. No se debe interpretar el primer equipo de una final como dueño del estadio. Para el futuro modelo habrá que auditar las sedes o documentar una estrategia de exclusión o tratamiento.

Fuente: https://github.com/openfootball/champions-league. Licencia CC0-1.0. La versión exacta y los hashes figuran en `fuentes.json`. Los archivos originales y su licencia están en `raw/`.
