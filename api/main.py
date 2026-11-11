"""API propia. La interfaz accede a los datos exclusivamente por HTTP."""
from datetime import date, timedelta
from pathlib import Path
from typing import Literal
import json

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]
DATA = pd.read_csv(ROOT / "data/processed/partidos.csv", encoding="utf-8-sig")
REPORT = json.loads((ROOT / "data/processed/calidad.json").read_text(encoding="utf-8"))
TEAMS = sorted(set(DATA["local"]) | set(DATA["visitante"]))
SEASONS = sorted(DATA["temporada"].unique().tolist())
PHASES = DATA["fase"].drop_duplicates().tolist()
MIN_DATE = date.fromisoformat(REPORT["fecha_desde"])
MAX_DATE = date.fromisoformat(REPORT["fecha_hasta"])
app = FastAPI(title="Champions Lab - API académica", version="0.4.0",
              description="Datos históricos y enfrentamientos directos a 90 minutos. El estado del modelo se consulta en /modelo.")


def model_status():
    try:
        from ml.model_service import get_status
        return get_status(root=ROOT)
    except ImportError:
        return {"estado": "pendiente", "mensaje": "Instala las dependencias y ejecuta scripts/entrenar_modelo.py."}


def filtered(temporada=None, equipo=None, resultado=None, fase=None):
    data = DATA
    if temporada:
        if temporada not in SEASONS:
            raise HTTPException(404, "Temporada no disponible")
        data = data[data.temporada == temporada]
    if equipo:
        if equipo not in TEAMS:
            raise HTTPException(404, "Equipo no disponible")
        data = data[(data.local == equipo) | (data.visitante == equipo)]
    if resultado:
        data = data[data.resultado == resultado]
    if fase:
        if fase not in PHASES:
            raise HTTPException(404, "Fase no disponible")
        data = data[data.fase == fase]
    return data


@app.get("/salud", tags=["Servicio"])
def health():
    return {"proyecto": "champions-lab", "api": "lista", "version": "0.4.0", "partidos": len(DATA), "modelo": model_status()}


@app.get("/modelo", tags=["Modelo"])
def model_report():
    """Estado, evaluación temporal y límites del modelo entrenado."""
    return model_status()


@app.get("/experimentos/mejoras", tags=["Modelo"])
def improvement_report():
    """Evaluación retrospectiva de las nuevas variables y recetas de entrenamiento."""
    from ml.experiment import get_report
    return get_report(root=ROOT)


@app.get("/equipos", tags=["Dataset"])
def teams():
    return {"equipos": TEAMS, "temporadas": SEASONS, "fases": PHASES,
            "fecha_desde": MIN_DATE.isoformat(), "fecha_hasta": MAX_DATE.isoformat()}


@app.get("/partidos", tags=["Dataset"])
def matches(temporada: str | None = None, equipo: str | None = None,
            resultado: Literal["Local", "Empate", "Visitante"] | None = None,
            fase: str | None = None, limite: int = Query(5000, ge=1, le=5000),
            desplazamiento: int = Query(0, ge=0)):
    data = filtered(temporada, equipo, resultado, fase).sort_values(["fecha", "local"], ascending=[False, True])
    return {"total": len(data), "partidos": data.iloc[desplazamiento:desplazamiento+limite].to_dict(orient="records")}


@app.get("/resumen", tags=["Dataset"])
def summary(temporada: str | None = None, equipo: str | None = None,
            resultado: Literal["Local", "Empate", "Visitante"] | None = None, fase: str | None = None):
    data = filtered(temporada, equipo, resultado, fase)
    return {"partidos": len(data), "equipos": len(set(data.local) | set(data.visitante)),
            "goles": int(data.goles_local_90.sum() + data.goles_visitante_90.sum()),
            "promedio_goles": round(float((data.goles_local_90 + data.goles_visitante_90).mean()), 2) if len(data) else 0,
            "resultados": {r: int((data.resultado == r).sum()) for r in ["Local", "Empate", "Visitante"]},
            "por_temporada": {str(k): int(v) for k,v in data.groupby("temporada").size().items()}}


@app.get("/calidad", tags=["Dataset"])
def quality():
    return REPORT


@app.get("/descargar", tags=["Dataset"])
def download(temporada: str | None = None, equipo: str | None = None,
             resultado: Literal["Local", "Empate", "Visitante"] | None = None, fase: str | None = None):
    content = filtered(temporada, equipo, resultado, fase).to_csv(index=False).encode("utf-8-sig")
    return Response(content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="partidos_champions.csv"'})


class MatchRequest(BaseModel):
    local: str = Field(min_length=1, max_length=120)
    visitante: str = Field(min_length=1, max_length=120)
    fecha: date

    @model_validator(mode="after")
    def validate_teams(self):
        if self.local == self.visitante:
            raise ValueError("Selecciona dos equipos diferentes")
        return self


class PredictionRequest(MatchRequest):
    sede_neutral: bool = False


def check_request(request, *, allow_future=False):
    if request.local not in TEAMS or request.visitante not in TEAMS:
        raise HTTPException(404, "Uno de los equipos no pertenece al dataset")
    latest = MAX_DATE + timedelta(days=365 if allow_future else 1)
    if not MIN_DATE < request.fecha <= latest:
        detail = "La fecha de predicción" if allow_future else "El corte histórico"
        raise HTTPException(422, f"{detail} debe estar entre {MIN_DATE + timedelta(days=1)} y {latest}")


def team_history(team, before):
    past = DATA[(DATA.fecha < before.isoformat()) & ((DATA.local == team) | (DATA.visitante == team))]
    recent = past.sort_values("fecha", ascending=False).head(5)
    records = []
    for row in recent.to_dict(orient="records"):
        home = row["local"] == team
        gf, ga = (row["goles_local_90"], row["goles_visitante_90"]) if home else (row["goles_visitante_90"], row["goles_local_90"])
        records.append({"fecha": row["fecha"], "rival": row["visitante"] if home else row["local"],
                        "condicion": "Local" if home else "Visitante", "goles_favor": gf, "goles_contra": ga,
                        "resultado_equipo": "Victoria" if gf > ga else "Derrota" if gf < ga else "Empate"})
    n = len(records)
    return {"equipo": team, "partidos_previos_disponibles": len(past), "partidos_usados": n,
            "victorias": sum(r["resultado_equipo"] == "Victoria" for r in records),
            "empates": sum(r["resultado_equipo"] == "Empate" for r in records),
            "derrotas": sum(r["resultado_equipo"] == "Derrota" for r in records),
            "promedio_goles_favor": round(sum(r["goles_favor"] for r in records)/n, 2) if n else None,
            "promedio_goles_contra": round(sum(r["goles_contra"] for r in records)/n, 2) if n else None,
            "ultimos_partidos": records}


def direct_history(local, visitante, before):
    """Todos los cruces previos, incluyendo la localía invertida."""
    past = DATA[(DATA.fecha < before.isoformat()) & (
        ((DATA.local == local) & (DATA.visitante == visitante)) |
        ((DATA.local == visitante) & (DATA.visitante == local))
    )].sort_values(["fecha", "id"], ascending=[False, True])
    records = past.to_dict(orient="records")
    wins_local = wins_away = draws = goals_local = goals_away = 0
    for row in records:
        gf, ga = (row["goles_local_90"], row["goles_visitante_90"]) if row["local"] == local else (row["goles_visitante_90"], row["goles_local_90"])
        goals_local += gf
        goals_away += ga
        wins_local += int(gf > ga)
        wins_away += int(gf < ga)
        draws += int(gf == ga)
    return {"equipo_a": local, "equipo_b": visitante, "partidos": len(records),
            "victorias_equipo_a": wins_local, "empates": draws, "victorias_equipo_b": wins_away,
            "goles_equipo_a": goals_local, "goles_equipo_b": goals_away,
            "encuentros": records,
            "nota": "Cruces disponibles en el dataset antes del corte, con ambas localías. Resultados a 90 minutos; estos conteos no son probabilidades de victoria."}


@app.post("/comparaciones", tags=["Historial"])
def compare(request: MatchRequest):
    check_request(request)
    return {"fecha_corte": request.fecha.isoformat(), "local": team_history(request.local, request.fecha),
            "visitante": team_history(request.visitante, request.fecha), "es_prediccion": False,
            "enfrentamientos_directos": direct_history(request.local, request.visitante, request.fecha),
            "nota": "Últimos cinco partidos de cada equipo y todos sus cruces directos previos disponibles. Solo Champions, a 90 minutos."}


@app.post("/predicciones", tags=["Modelo"], responses={503:{"description":"Modelo no disponible o dataset modificado"}})
def predict(request: PredictionRequest):
    check_request(request, allow_future=True)
    if request.sede_neutral:
        raise HTTPException(422, "Este primer modelo no admite partidos en sede neutral.")
    try:
        from ml.model_service import predict_match, ModelUnavailableError, PredictionError
    except ImportError:
        raise HTTPException(503, "Instala las dependencias y ejecuta scripts/entrenar_modelo.py.")
    try:
        return predict_match(DATA, request.local, request.visitante, request.fecha, root=ROOT)
    except ModelUnavailableError as error:
        raise HTTPException(503, str(error))
    except PredictionError as error:
        raise HTTPException(422, str(error))
