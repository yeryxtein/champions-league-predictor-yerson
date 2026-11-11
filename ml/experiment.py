"""Comparación temporal fija de cinco recetas con prueba retrospectiva 2025-26."""
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from ml.features import CLASSES, FEATURES
from ml.features_v2 import FEATURES_V2, build_training_table_v2
from ml.training import ROOT, ordered_probabilities, sha256, split_summary

PROTOCOL = "expansivo-2025-26-v1"
VALIDATION_SEASONS = ["2022-23", "2023-24", "2024-25"]
TEST_SEASON = "2025-26"
RF_PARAMS = dict(n_estimators=300, max_depth=6, min_samples_leaf=6, random_state=42, n_jobs=1)
LOGISTIC_PARAMS = dict(C=1.0, max_iter=2000, random_state=42)


def code_signature():
    """Identifica el protocolo y las variables con saltos de línea portables."""
    folder = Path(__file__).resolve().parent
    content = "\n".join((folder / name).read_text(encoding="utf-8") for name in
                        ("features.py", "features_v2.py", "training.py", "experiment.py"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_report(root=ROOT):
    """Rechaza publicaciones incompletas o resultados de otra copia de datos."""
    root = Path(root)
    output = root / "models/experimento_v2"
    lock = output / ".evaluacion.lock"
    if lock.exists():
        return {"estado": "pendiente", "mensaje": "La evaluación está en curso. Vuelve a consultar al terminar."}
    report_path = output / "informe.json"
    if not report_path.exists():
        return {"estado": "pendiente", "mensaje": "Ejecuta python scripts/evaluar_mejoras.py para generar la evaluación."}
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report["protocolo"] != PROTOCOL or report["codigo_sha256"] != code_signature():
            return {"estado": "desactualizado", "mensaje": "El protocolo cambió. Vuelve a ejecutar la evaluación."}
        if report["dataset_sha256"] != sha256(root / "data/processed/partidos.csv"):
            return {"estado": "desactualizado", "mensaje": "Los datos cambiaron. Vuelve a ejecutar la evaluación."}
        for filename, key in (("seleccion.json", "seleccion_sha256"), ("predicciones.csv", "predicciones_sha256")):
            if sha256(output / filename) != report["hashes"][key]:
                raise ValueError("Publicación incompleta")
        selection = json.loads((output / "seleccion.json").read_text(encoding="utf-8"))
        if (report["estado"] != "evaluado" or report["elegido"] != selection["elegido"]
                or report["dataset_sha256"] != selection["dataset_sha256"]
                or report["codigo_sha256"] != selection["codigo_sha256"]
                or report["prueba"]["temporada"] != TEST_SEASON):
            raise ValueError("Informe inconsistente")
        # Valida los campos que utiliza la interfaz antes de publicarlos.
        for role in ("elegido", "rf6", "referencia"):
            metrics = report["prueba"]["metricas"][role]
            if metrics["partidos"] != report["prueba"]["utilizables"]:
                raise ValueError("Conteos inconsistentes")
            for key in ("accuracy", "f1_macro", "log_loss"):
                if not np.isfinite(metrics[key]):
                    raise ValueError("Métrica inválida")
            for key in ("reales", "predichos", "aciertos"):
                if metrics["empates"][key] < 0:
                    raise ValueError("Conteo inválido")
        if lock.exists():
            return {"estado": "pendiente", "mensaje": "La evaluación está actualizando sus archivos. Vuelve a consultar al terminar."}
        return report
    except (OSError, ValueError, KeyError, TypeError):
        return {"estado": "no_disponible", "mensaje": "La evaluación está incompleta o sus archivos cambiaron. Ejecuta scripts/evaluar_mejoras.py de nuevo."}


def candidates():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "RF6": (FEATURES, RandomForestClassifier(**RF_PARAMS)),
        "RF_ampliado": (FEATURES_V2, RandomForestClassifier(**RF_PARAMS)),
        "RF_ampliado_equilibrado": (FEATURES_V2, RandomForestClassifier(**RF_PARAMS, class_weight="balanced_subsample")),
        "Logistica_ampliada": (FEATURES_V2, make_pipeline(StandardScaler(), LogisticRegression(**LOGISTIC_PARAMS))),
        "Logistica_ampliada_equilibrada": (FEATURES_V2, make_pipeline(StandardScaler(), LogisticRegression(**LOGISTIC_PARAMS, class_weight="balanced"))),
    }


def measure(estimator, table, features):
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss

    probabilities = ordered_probabilities(estimator, table[features])
    observed = np.array([CLASSES.index(label) for label in table.resultado])
    predicted = probabilities.argmax(axis=1)
    matrix = confusion_matrix(observed, predicted, labels=[0, 1, 2])
    true_draws = int(matrix[1].sum())
    predicted_draws = int(matrix[:, 1].sum())
    correct_draws = int(matrix[1, 1])
    metrics = {
        "partidos": len(table),
        "accuracy": float(accuracy_score(observed, predicted)),
        "f1_macro": float(f1_score(observed, predicted, labels=[0, 1, 2], average="macro", zero_division=0)),
        "log_loss": float(log_loss(observed, probabilities, labels=[0, 1, 2])),
        "soporte": {label: int(matrix[index].sum()) for index, label in enumerate(CLASSES)},
        "empates": {
            "reales": true_draws, "predichos": predicted_draws, "aciertos": correct_draws,
            "recall": correct_draws / true_draws if true_draws else 0.0,
            "precision": correct_draws / predicted_draws if predicted_draws else 0.0,
        },
        "matriz_confusion": matrix.tolist(), "orden_clases": CLASSES,
        "matriz_filas": "resultado_real", "matriz_columnas": "resultado_estimado",
    }
    return metrics, probabilities


def require_sample(table, name, minimum):
    if len(table) < minimum or set(table.resultado) != set(CLASSES):
        raise ValueError(f"{name} necesita al menos {minimum} partidos y las tres clases.")
    if table.id.duplicated().any():
        raise ValueError(f"{name} contiene identificadores repetidos.")
    if not np.isfinite(table[FEATURES_V2].to_numpy(dtype=float)).all():
        raise ValueError(f"{name} contiene variables ausentes o no finitas.")


def choose_candidate(scores):
    """Mayor media de F1 macro, menor media de log loss y nombre alfabético."""
    return min(scores, key=lambda name: (-scores[name]["f1_macro_medio"], scores[name]["log_loss_medio"], name))


def select_candidate(development):
    """Esta función recibe exclusivamente registros anteriores a la prueba."""
    from sklearn.base import clone

    if development.empty or (development.temporada >= TEST_SEASON).any():
        raise ValueError("La selección sólo admite temporadas anteriores a 2025-26.")
    table = build_training_table_v2(development)
    eligible = table[table.exclusion.isna()]
    recipes = candidates()
    scores = {name: {"por_temporada": {}} for name in recipes}
    partitions = {}
    for season in VALIDATION_SEASONS:
        training = eligible[eligible.temporada < season]
        validation = eligible[eligible.temporada == season]
        require_sample(training, f"Entrenamiento antes de {season}", 60)
        require_sample(validation, f"Validación {season}", 20)
        if training.fecha.max() >= validation.fecha.min():
            raise ValueError("Las fechas de entrenamiento y validación se solapan.")
        partitions[season] = {
            "entrenamiento": split_summary(table, table.temporada < season),
            "validacion": split_summary(table, table.temporada == season),
        }
        for name, (features, estimator) in recipes.items():
            fitted = clone(estimator).fit(training[features], training.resultado)
            scores[name]["por_temporada"][season], _ = measure(fitted, validation, features)
    for values in scores.values():
        by_season = list(values["por_temporada"].values())
        values["f1_macro_medio"] = float(np.mean([item["f1_macro"] for item in by_season]))
        values["log_loss_medio"] = float(np.mean([item["log_loss"] for item in by_season]))
    return {
        "elegido": choose_candidate(scores),
        "validacion": {"temporadas": VALIDATION_SEASONS, "candidatos": scores, "particiones": partitions},
    }, table


def write_json(path, content):
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def run_experiment(root=ROOT):
    import sklearn
    from sklearn.base import clone
    from sklearn.dummy import DummyClassifier

    root = Path(root).resolve()
    dataset_path = root / "data/processed/partidos.csv"
    original_bytes = dataset_path.read_bytes()
    dataset_hash = hashlib.sha256(original_bytes).hexdigest()
    data = pd.read_csv(BytesIO(original_bytes), encoding="utf-8-sig")
    development = data[data.temporada < TEST_SEASON].copy()
    if not (data.temporada == TEST_SEASON).any():
        raise ValueError("Faltan los partidos de la temporada de prueba 2025-26.")
    output = root / "models/experimento_v2"
    output.mkdir(parents=True, exist_ok=True)
    lock_path = output / ".evaluacion.lock"
    try:
        lock = lock_path.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise RuntimeError("Hay otra evaluación en curso. Si terminó de forma inesperada, elimina models/experimento_v2/.evaluacion.lock antes de repetir.") from error

    try:
        with lock:
            lock.write(datetime.now(timezone.utc).isoformat())
        return _evaluate_locked(root, output, dataset_path, dataset_hash, data, development, sklearn.__version__, clone, DummyClassifier)
    finally:
        lock_path.unlink(missing_ok=True)


def _evaluate_locked(root, output, dataset_path, dataset_hash, data, development, sklearn_version, clone, dummy_class):
    print("Seleccionando con las temporadas 2022-23, 2023-24 y 2024-25...", flush=True)
    selection, development_table = select_candidate(development)
    chosen = selection["elegido"]
    recipes = candidates()
    chosen_features, chosen_estimator = recipes[chosen]
    selection.update({
        "version": 2, "protocolo": PROTOCOL, "dataset_sha256": dataset_hash, "codigo_sha256": code_signature(),
        "registrado_antes_de_prueba_utc": datetime.now(timezone.utc).isoformat(),
        "temporada_prueba": TEST_SEASON, "variables_elegido": chosen_features,
        "regla_seleccion": "Media por temporada de F1 macro; desempate por menor log loss medio y nombre alfabético.",
        "configuracion": {
            "RandomForest": RF_PARAMS, "Logistica": LOGISTIC_PARAMS,
            "balanceo_RF": "balanced_subsample", "balanceo_Logistica": "balanced",
            "variables_base": FEATURES, "variables_ampliadas": FEATURES_V2,
            "Elo": {"inicial": 1500, "K": 20, "ventaja_local": 0},
            "directos": {"ventana": 5, "pseudoconteo_por_clase": 1},
        },
    })
    # El manifiesto queda persistido antes de calcular variables o métricas del test.
    # Las tres salidas se publican con el informe al final para validar sus hashes.
    with TemporaryDirectory(prefix="evaluacion_", dir=output) as folder:
        staging = Path(folder)
        selection_path = staging / "seleccion.json"
        write_json(selection_path, selection)
        print(f"Selección guardada: {chosen}. Evaluando 2025-26...", flush=True)
        all_table = build_training_table_v2(data[data.temporada <= TEST_SEASON])
        fitting = development_table[development_table.exclusion.isna()]
        testing = all_table[(all_table.temporada == TEST_SEASON) & all_table.exclusion.isna()]
        require_sample(fitting, "Reajuste anterior a prueba", 60)
        require_sample(testing, "Prueba 2025-26", 20)
        if fitting.fecha.max() >= testing.fecha.min() or set(fitting.id) & set(testing.id):
            raise ValueError("El conjunto de prueba se solapa con el reajuste.")
        roles = {
            "elegido": (chosen, chosen_features, chosen_estimator),
            "rf6": ("RF6", *recipes["RF6"]),
            "referencia": ("Dummy_prior", FEATURES, dummy_class(strategy="prior")),
        }
        metrics, prediction_frames = {}, []
        for role, (name, features, estimator) in roles.items():
            fitted = clone(estimator).fit(fitting[features], fitting.resultado)
            metrics[role], probabilities = measure(fitted, testing, features)
            rows = testing[["id", "fecha", "local", "visitante", "resultado"]].rename(columns={"resultado": "real"}).copy()
            rows["rol"], rows["receta"] = role, name
            rows["estimado"] = [CLASSES[index] for index in probabilities.argmax(axis=1)]
            for index, label in enumerate(CLASSES):
                rows[f"probabilidad_{label.lower()}"] = probabilities[:, index]
            prediction_frames.append(rows)
        prediction_path = staging / "predicciones.csv"
        pd.concat(prediction_frames, ignore_index=True).to_csv(prediction_path, index=False, encoding="utf-8-sig")
        report = {
            "estado": "evaluado", "version": 2, "protocolo": PROTOCOL,
            "codigo_sha256": selection["codigo_sha256"],
            "generado_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_sha256": dataset_hash, "dataset_fecha_hasta": str(data.fecha.max()),
            "elegido": chosen, "variables_elegido": chosen_features,
            "validacion": selection["validacion"],
            "entrenamiento_final": split_summary(development_table, pd.Series(True, index=development_table.index)),
            "prueba": {"temporada": TEST_SEASON, **split_summary(all_table, all_table.temporada == TEST_SEASON), "metricas": metrics},
            "versiones": {"python": platform.python_version(), "scikit-learn": sklearn_version, "pandas": pd.__version__},
            "hashes": {"seleccion_sha256": sha256(selection_path), "predicciones_sha256": sha256(prediction_path)},
            "limitaciones": [
                "Prueba retrospectiva de una temporada. Los resultados de 2025-26 ya existían y se usaron en el reajuste de la versión anterior; las recetas de este experimento se seleccionan con temporadas anteriores.",
                "Los pesos quedan congelados antes de 2025-26. Las variables de cada encuentro incorporan resultados conocidos de días previos de esa temporada.",
                "Se requiere historial de cinco partidos por equipo y se conservan las exclusiones de sede de la primera versión.",
                "Las probabilidades se reportan sin calibración adicional. Las ponderaciones de clase pueden modificar su interpretación probabilística.",
                "Una mejora en esta muestra requiere confirmación en partidos futuros y en temporadas adicionales.",
            ],
        }
        if sha256(dataset_path) != dataset_hash:
            raise RuntimeError("El dataset cambió durante la evaluación. Repite con una copia estable.")
        write_json(staging / "informe.json", report)
        for name in ("seleccion.json", "predicciones.csv", "informe.json"):
            (staging / name).replace(output / name)
    return report
