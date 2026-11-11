"""Selección en 2023-24; prueba 2024-25 reservada hasta elegir el modelo."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from ml.features import CLASSES, FEATURES, WINDOW, build_training_table

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_SEASON = "2023-24"
TEST_SEASON = "2024-25"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dataframe_signature(data):
    """Detecta que la API conserva en memoria un CSV anterior al entrenamiento."""
    columns = ["id", "temporada", "fecha", "fase", "local", "visitante", "goles_local_90", "goles_visitante_90", "resultado"]
    canonical = data[columns].sort_values("id").to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ordered_probabilities(estimator, x):
    raw = estimator.predict_proba(x)
    columns = {str(label): index for index, label in enumerate(estimator.classes_)}
    if set(columns) != set(CLASSES):
        raise ValueError("El modelo debe contener las tres clases de resultado.")
    probabilities = raw[:, [columns[label] for label in CLASSES]]
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError("El modelo devolvió probabilidades inválidas.")
    if not np.allclose(probabilities.sum(axis=1), 1.0):
        raise ValueError("Las probabilidades no suman uno.")
    return probabilities


def metrics_for(estimator, table):
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss

    probabilities = ordered_probabilities(estimator, table[FEATURES])
    encoded = np.array([CLASSES.index(label) for label in table.resultado])
    predicted = probabilities.argmax(axis=1)
    # Etiquetas numéricas 0,1,2 preservan el orden Local, Empate, Visitante en log_loss.
    return {
        "partidos": len(table),
        "accuracy": float(accuracy_score(encoded, predicted)),
        "f1_macro": float(f1_score(encoded, predicted, labels=[0, 1, 2], average="macro", zero_division=0)),
        "log_loss": float(log_loss(encoded, probabilities, labels=[0, 1, 2])),
        "soporte": {label: int((encoded == idx).sum()) for idx, label in enumerate(CLASSES)},
        "matriz_confusion": confusion_matrix(encoded, predicted, labels=[0, 1, 2]).tolist(),
        "orden_clases": CLASSES,
        "matriz_filas": "resultado_real", "matriz_columnas": "resultado_estimado",
    }, probabilities


def split_summary(table, season_filter):
    subset = table.loc[season_filter]
    eligible = subset[subset.exclusion.isna()]
    return {
        "temporadas": sorted(subset.temporada.unique().tolist()),
        "total": len(subset), "utilizables": len(eligible),
        "excluidos": len(subset) - len(eligible),
        "motivos_exclusion": dict(Counter(subset.exclusion.dropna().tolist())),
        "fecha_desde": str(eligible.fecha.min()) if len(eligible) else None,
        "fecha_hasta": str(eligible.fecha.max()) if len(eligible) else None,
        "soporte": {label: int((eligible.resultado == label).sum()) for label in CLASSES},
    }


def train(root=ROOT):
    import joblib
    import sklearn
    from sklearn.base import clone
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    root = Path(root)
    data_path = root / "data/processed/partidos.csv"
    data = pd.read_csv(data_path, encoding="utf-8-sig")
    table = build_training_table(data)
    eligible = table[table.exclusion.isna()].copy()
    training = eligible[eligible.temporada < VALIDATION_SEASON]
    validation = eligible[eligible.temporada == VALIDATION_SEASON]
    testing = eligible[eligible.temporada == TEST_SEASON]
    for name, subset, minimum in [("entrenamiento", training, 60), ("validación", validation, 20), ("prueba", testing, 20)]:
        if len(subset) < minimum or set(subset.resultado) != set(CLASSES):
            raise ValueError(f"{name}: faltan datos suficientes y las tres clases; no se publicará un modelo sin evaluación.")
    if not training.fecha.max() < validation.fecha.min() or not validation.fecha.max() < testing.fecha.min():
        raise ValueError("Las particiones temporales se solapan.")

    candidates = {
        "Referencia": DummyClassifier(strategy="prior"),
        "RegresionLogistica": make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, random_state=42)),
        "RandomForest": RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=6, random_state=42, n_jobs=1),
    }
    validation_metrics = {}
    for name, estimator in candidates.items():
        estimator.fit(training[FEATURES], training.resultado)
        validation_metrics[name], _ = metrics_for(estimator, validation)

    # El test no participa en la elección ni en la configuración de hiperparámetros.
    chosen = max(["RegresionLogistica", "RandomForest"],
                 key=lambda name: (validation_metrics[name]["f1_macro"], -validation_metrics[name]["log_loss"]))
    fitting = pd.concat([training, validation]).sort_values(["fecha", "id"])
    evaluated = clone(candidates[chosen]).fit(fitting[FEATURES], fitting.resultado)
    reference = DummyClassifier(strategy="prior").fit(fitting[FEATURES], fitting.resultado)
    test_metrics, test_probabilities = metrics_for(evaluated, testing)
    baseline_metrics, _ = metrics_for(reference, testing)

    # Artefacto distinto: aprovecha todos los datos, pero NO hereda una evaluación independiente.
    current = clone(candidates[chosen]).fit(eligible[FEATURES], eligible.resultado)
    output = root / "models"
    output.mkdir(exist_ok=True)
    joblib.dump(evaluated, output / "modelo_evaluado.joblib", compress=3)
    joblib.dump(current, output / "modelo_actual.joblib", compress=3)
    table.to_csv(output / "variables_y_exclusiones.csv", index=False, encoding="utf-8-sig")
    prediction_rows = testing[["id", "fecha", "local", "visitante", "resultado"]].copy()
    prediction_rows["estimado"] = [CLASSES[index] for index in test_probabilities.argmax(axis=1)]
    for index, label in enumerate(CLASSES):
        prediction_rows[f"probabilidad_{label.lower()}"] = test_probabilities[:, index]
    prediction_rows.to_csv(output / "predicciones_prueba.csv", index=False, encoding="utf-8-sig")
    quality_path = root / "data/processed/calidad.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}
    report = {
        "version": 1, "estado": "entrenado", "modelo": chosen,
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": sha256(data_path), "dataframe_sha256": dataframe_signature(data), "dataset_partidos": len(data),
        "dataset_fecha_hasta": str(data.fecha.max()),
        "dataset_cobertura": quality.get("cobertura_temporadas", quality.get("temporadas", {})),
        "versiones": {"python": platform.python_version(), "scikit-learn": sklearn.__version__, "joblib": joblib.__version__, "pandas": pd.__version__},
        "clases": CLASSES, "variables": FEATURES, "historial_minimo_por_equipo": WINDOW,
        "objetivo": "Resultado a 90 minutos más añadido: Local, Empate o Visitante; sin prórroga ni penales.",
        "seleccion": "Mayor F1 macro en 2023-24 entre RegresionLogistica y RandomForest; empate por menor log loss. Referencia se informa por separado.",
        "hiperparametros": {"RegresionLogistica": {"C": 1.0, "max_iter": 2000, "escalado": "StandardScaler dentro de Pipeline"}, "RandomForest": {"n_estimators": 300, "max_depth": 6, "min_samples_leaf": 6, "random_state": 42}, "Referencia": {"strategy": "prior"}},
        "particiones": {
            "entrenamiento": split_summary(table, table.temporada < VALIDATION_SEASON),
            "validacion": split_summary(table, table.temporada == VALIDATION_SEASON),
            "prueba": split_summary(table, table.temporada == TEST_SEASON),
            "reajuste_actual": split_summary(table, pd.Series(True, index=table.index)),
        },
        "validacion": {"temporada": VALIDATION_SEASON, "metricas": validation_metrics},
        "prueba": {"temporada": TEST_SEASON, "modelo": chosen, "metricas_modelo": test_metrics, "metricas_referencia": baseline_metrics,
                   "supera_referencia_f1_macro": test_metrics["f1_macro"] > baseline_metrics["f1_macro"],
                   "supera_referencia_accuracy": test_metrics["accuracy"] > baseline_metrics["accuracy"]},
        "artefactos": {
            "evaluado": {"archivo": "modelo_evaluado.joblib", "sha256": sha256(output / "modelo_evaluado.joblib"),
                         "entrenado_hasta": str(fitting.fecha.max()), "partidos_entrenamiento": len(fitting),
                         "evaluado_en": TEST_SEASON},
            "actual": {"archivo": "modelo_actual.joblib", "sha256": sha256(output / "modelo_actual.joblib"),
                       "entrenado_hasta": str(eligible.fecha.max()), "partidos_entrenamiento": len(eligible),
                       "evaluado_en": None},
        },
        "limitaciones": [
            "Modelo académico inicial; sus probabilidades no están calibradas ni garantizan resultados.",
            f"En prueba acertó {test_metrics['matriz_confusion'][1][1]} de {test_metrics['soporte']['Empate']} empates reales; revisar la matriz por clase y no sólo el accuracy global.",
            "Las métricas de prueba corresponden sólo al artefacto evaluado; el reajustado con todos los datos no tiene prueba futura independiente.",
            "Se exigen cinco partidos previos por equipo. La cobertura de evaluación excluye clubes con poco historial.",
            "Se excluyen como objetivos todas las finales, toda 2020-21 y octavos/cuartos/semifinales de agosto de 2020 por sedes no auditadas.",
            "Las seis variables sólo resumen puntos y goles de los últimos cinco partidos de Champions; no usan lesiones, plantillas ni otras ligas.",
            "El historial de forma puede incluir partidos en sede neutral porque no separa rendimiento local/visitante.",
            "En evaluación, cada partido usa resultados conocidos de días anteriores, incluidos partidos ya terminados de la temporada de prueba; los pesos quedan congelados.",
            "El nuevo formato de 2024-25 cambia rivales, número de partidos y distribución de los datos.",
            "La fuente comunitaria no cuenta con auditoría independiente de todos sus resultados ni sedes.",
        ],
    }
    (output / "metricas.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
