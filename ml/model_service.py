"""Contrato pequeño para FastAPI: estado y predicción con restricciones temporales."""
from functools import lru_cache
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import pandas as pd

from ml.features import CLASSES, FEATURES, PredictionError, as_iso, exclusion_reason, match_features
from ml.training import ROOT, dataframe_signature, ordered_probabilities, sha256


class ModelUnavailableError(RuntimeError):
    """Falta entrenamiento, dependencias o los artefactos no corresponden a los datos."""


def get_status(root=ROOT):
    root = Path(root)
    report_path = root / "models/metricas.json"
    if not report_path.exists():
        return {"estado": "pendiente", "mensaje": "Ejecuta python scripts/entrenar_modelo.py para entrenar y evaluar."}
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report["dataset_sha256"] != sha256(root / "data/processed/partidos.csv"):
            return {"estado": "desactualizado", "mensaje": "Los datos cambiaron; vuelve a entrenar antes de predecir."}
        for meta in report["artefactos"].values():
            if sha256(root / "models" / meta["archivo"]) != meta["sha256"]:
                return {"estado": "no_disponible", "mensaje": "Un artefacto cambió; vuelve a entrenar."}
        return report
    except (OSError, KeyError, ValueError):
        return {"estado": "no_disponible", "mensaje": "No se pudo verificar el modelo; vuelve a entrenar."}


@lru_cache(maxsize=4)
def _load_estimator(path, mtime_ns, expected_hash):
    try:
        import joblib
        return joblib.load(path)
    except (ImportError, OSError, ValueError) as exc:
        raise ModelUnavailableError("Instala requirements-lock.txt y vuelve a entrenar el modelo.") from exc


def load_bundle(root=ROOT):
    root = Path(root)
    report = get_status(root)
    if report["estado"] != "entrenado":
        raise ModelUnavailableError(report["mensaje"])
    bundle = {"metadata": report}
    for name, meta in report["artefactos"].items():
        path = root / "models" / meta["archivo"]
        bundle[name] = _load_estimator(str(path), path.stat().st_mtime_ns, meta["sha256"])
    return bundle


def choose_artifact(report, cutoff):
    """Nunca aplicar pesos que aprendieron de un resultado del mismo día o posterior."""
    for name in ["actual", "evaluado"]:
        if cutoff > report["artefactos"][name]["entrenado_hasta"]:
            return name
    first = report["artefactos"]["evaluado"]["entrenado_hasta"]
    raise PredictionError(
        f"No hay un modelo entrenado sólo con datos anteriores a {cutoff}. El modelo histórico usa resultados hasta {first}; elige una fecha posterior."
    )


def predict_match(data, local, visitante, fecha, root=ROOT, sede_neutral=False):
    cutoff = as_iso(fecha)
    dataset_end = date.fromisoformat(str(data.fecha.max()))
    maximum = (dataset_end + timedelta(days=365)).isoformat()
    if cutoff > maximum:
        raise PredictionError(f"El horizonte experimental admite cortes hasta {maximum}, un año después del último dato.")
    if sede_neutral:
        raise PredictionError("Este primer modelo no admite partidos en sede neutral.")
    matching = data[(data.fecha == cutoff) & (data.local == local) & (data.visitante == visitante)]
    known_pair = data[(data.fecha == cutoff) & (
        ((data.local == local) & (data.visitante == visitante)) |
        ((data.local == visitante) & (data.visitante == local))
    )]
    for record in known_pair.to_dict(orient="records"):
        if exclusion_reason(record):
            raise PredictionError("El partido pertenece a una final o un periodo con sedes no auditadas y está fuera del alcance del modelo.")
    bundle = load_bundle(root)
    report = bundle["metadata"]
    if dataframe_signature(data) != report["dataframe_sha256"]:
        raise ModelUnavailableError("Los datos en memoria no corresponden al modelo. Reinicia la API después de actualizar y entrenar.")
    kind = choose_artifact(report, cutoff)
    values, history = match_features(data, local, visitante, cutoff)
    probabilities = ordered_probabilities(bundle[kind], pd.DataFrame([values], columns=FEATURES))[0]
    best = int(probabilities.argmax())
    warnings = ["Estimación experimental a 90 minutos; no garantiza el resultado y no está calibrada."]
    if kind == "actual":
        warnings.append("Modelo reajustado con todos los datos elegibles; las métricas mostradas pertenecen a una versión anterior evaluada.")
    else:
        warnings.append("Se utiliza el modelo histórico congelado para evitar aprender de resultados posteriores a esta fecha.")
    if not len(matching):
        warnings.append("Escenario hipotético: se supone sede habitual del local; el sistema no verifica un calendario futuro.")
    if cutoff > dataset_end.isoformat():
        gap = (date.fromisoformat(cutoff) - dataset_end).days
        warnings.append(f"El dataset termina el {dataset_end.isoformat()}: faltan los {gap} días posteriores de resultados y cambios de equipos; esta proyección usa únicamente el historial disponible.")
    for details in history.values():
        if details["dias_sin_partidos_en_dataset"] > 365:
            warnings.append(f"{details['equipo']}: el último partido disponible tiene más de un año; su forma puede estar desactualizada.")
    return {
        "local": local, "visitante": visitante, "fecha_corte": cutoff,
        "emitido_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": report["dataset_sha256"],
        "modelo_sha256": report["artefactos"][kind]["sha256"],
        "modelo": report["modelo"], "version_modelo": kind,
        "dataset_fecha_hasta": dataset_end.isoformat(),
        "entrenado_hasta": report["artefactos"][kind]["entrenado_hasta"],
        "probabilidades": {label: float(probabilities[index]) for index, label in enumerate(CLASSES)},
        "resultado_mas_probable": CLASSES[best], "probabilidad_mayor": float(probabilities[best]),
        "variables": values, "historial": history, "es_prediccion": True,
        "advertencias": warnings,
    }
