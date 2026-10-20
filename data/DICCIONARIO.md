# Diccionario y preparación

La tabla `processed/partidos.csv` contiene una fila por partido. Codificación UTF-8 con BOM. No se incluyen rondas clasificatorias.

| Columna | Significado |
|---|---|
| id | Identificador estable calculado a partir de temporada, fecha y equipos |
| temporada | Temporada, por ejemplo 2023-24 |
| fecha | Fecha del partido en formato AAAA-MM-DD |
| fase | Grupos, Octavos, Cuartos, Semifinal o Final |
| local / visitante | Nombres unificados, designados así en la fuente |
| pais_local / pais_visitante | Código de país de tres letras, conservado de la fuente |
| goles_local_90 / goles_visitante_90 | Goles tras 90 minutos más tiempo añadido, sin prórroga ni penales |
| resultado | Local, Empate o Visitante. Etiqueta derivada de los goles a 90 minutos |
| hubo_prorroga / hubo_penales | Indicadores del formato original del encuentro |
| local_original / visitante_original | Nombres sin normalización |
| marcador_original | Texto del resultado sin modificar |
| fuente | Enlace permanente al archivo y línea de origen |

## Reglas

1. La fecha toma el año explícito si existe. En los demás casos, los grupos usan el año inicial y las eliminatorias el año final de la temporada. Esto cubre también agosto de 2020. Se verifica el día de la semana.
2. El mapa explícito de 15 aliases del script unifica variantes del mismo club. `equipos_normalizados.csv` conserva la correspondencia completa.
3. En `4-2 a.e.t. (1-2, 0-0)`, el resultado a 90 minutos es **1-2**. En `3-4 pen. 1-1 a.e.t. (1-1, 0-1)`, es **1-1**. Se conservan los textos originales para revisión.
4. El procesamiento se detiene si una línea no se reconoce, si el conteo difiere del encabezado o si aparecen duplicados. No se omiten silenciosamente partidos.
5. El script comprueba los hashes de los archivos originales contra `fuentes.json`.

## Alcance de los controles

Los ocho archivos suman 994 filas y 83 clubes unificados. Hay 9 prórrogas, de las que 3 incluyen penales. No hay duplicados ni valores vacíos en los campos exportados. Esto no prueba que cada resultado de la fuente comunitaria sea correcto.

El dataset no tiene una columna uniforme de sede neutral, lesiones ni alineaciones. No se debe interpretar el primer equipo de una final como dueño del estadio. Para el futuro modelo habrá que auditar las sedes o documentar una estrategia de exclusión o tratamiento.

Fuente: https://github.com/openfootball/champions-league. Licencia CC0-1.0. La versión exacta y los hashes figuran en `fuentes.json`. Los archivos originales y su licencia están en `raw/`.
