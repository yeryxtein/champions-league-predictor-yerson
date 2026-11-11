"""Variables disponibles antes del día del partido; sin resultados futuros."""
from datetime import date

import pandas as pd

CLASSES = ["Local", "Empate", "Visitante"]
WINDOW = 5
FEATURES = [
    "local_puntos_5", "local_goles_favor_5", "local_goles_contra_5",
    "visitante_puntos_5", "visitante_goles_favor_5", "visitante_goles_contra_5",
]


class PredictionError(ValueError):
    """Solicitud fuera del alcance o con historial insuficiente."""


def as_iso(value):
    return date.fromisoformat(str(value)[:10]).isoformat()


def exclusion_reason(row):
    """Exclusiones conservadoras: la fuente no tiene sede neutral uniforme."""
    if row["fase"] == "Final":
        return "final_sede_neutral"
    if row["temporada"] == "2020-21":
        return "temporada_2020_21_sedes_no_auditadas"
    if (row["temporada"] == "2019-20" and row["fecha"] >= "2020-08-01"
            and row["fase"] in {"Octavos", "Cuartos", "Semifinal"}):
        return "eliminatorias_agosto_2020_sedes_no_auditadas"
    return None


def team_form(data, team, cutoff):
    """La comparación es estricta por día, incluso si hay dos filas el mismo día."""
    cutoff = as_iso(cutoff)
    previous = data[(data.fecha < cutoff) & ((data.local == team) | (data.visitante == team))]
    recent = previous.sort_values(["fecha", "id"], ascending=[False, True]).head(WINDOW)
    if len(recent) < WINDOW:
        raise PredictionError(
            f"{team}: se necesitan {WINDOW} partidos previos de Champions; hay {len(recent)} antes de {cutoff}."
        )
    home = recent.local == team
    gf = recent.goles_local_90.where(home, recent.goles_visitante_90)
    ga = recent.goles_visitante_90.where(home, recent.goles_local_90)
    points = (gf > ga).astype(int) * 3 + (gf == ga).astype(int)
    last = str(recent.fecha.max())
    return {
        "puntos_5": float(points.mean()),
        "goles_favor_5": float(gf.mean()),
        "goles_contra_5": float(ga.mean()),
    }, {
        "equipo": team, "partidos_usados": WINDOW,
        "ids_historial": recent.id.astype(str).tolist(),
        "fecha_ultimo_partido": last,
        "dias_sin_partidos_en_dataset": (date.fromisoformat(cutoff) - date.fromisoformat(last)).days,
    }


def match_features(data, local, visitante, cutoff):
    if local == visitante:
        raise PredictionError("Selecciona dos equipos diferentes.")
    known = set(data.local) | set(data.visitante)
    if local not in known or visitante not in known:
        raise PredictionError("Uno de los equipos no pertenece al dataset.")
    features, history = {}, {}
    for side, team in [("local", local), ("visitante", visitante)]:
        values, details = team_form(data, team, cutoff)
        features.update({f"{side}_{key}": value for key, value in values.items()})
        history[side] = details
    return features, history


def build_training_table(data):
    """Conserva todas las filas y explica por qué cada una puede o no usarse."""
    rows = []
    for record in data.sort_values(["fecha", "id"]).to_dict(orient="records"):
        row = {key: record[key] for key in ["id", "temporada", "fecha", "local", "visitante", "resultado"]}
        row["exclusion"] = exclusion_reason(record)
        if not row["exclusion"]:
            try:
                values, history = match_features(data, record["local"], record["visitante"], record["fecha"])
                row.update(values)
                row["local_ultimo_previo"] = history["local"]["fecha_ultimo_partido"]
                row["visitante_ultimo_previo"] = history["visitante"]["fecha_ultimo_partido"]
            except PredictionError:
                row["exclusion"] = "menos_de_5_partidos_previos_por_equipo"
        rows.append(row)
    return pd.DataFrame(rows)
