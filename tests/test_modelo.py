"""Pruebas de fuga temporal, exclusiones y orden de probabilidades del modelo."""
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from ml.features import CLASSES, FEATURES, PredictionError, build_training_table, exclusion_reason, match_features
from ml.model_service import ModelUnavailableError, choose_artifact, get_status, predict_match
from ml.training import ROOT, dataframe_signature, metrics_for, ordered_probabilities, sha256


def synthetic_matches():
    rows = []
    for index in range(8):
        gf, ga = [(2, 0), (1, 1), (0, 2)][index % 3]
        rows.append({
            "id": str(index), "temporada": "2024-25", "fecha": (date(2024, 9, 1) + timedelta(days=index)).isoformat(),
            "fase": "Liga", "local": "A", "visitante": "B",
            "goles_local_90": gf, "goles_visitante_90": ga,
            "resultado": "Local" if gf > ga else "Empate" if gf == ga else "Visitante",
        })
    return pd.DataFrame(rows)


class FixedEstimator:
    # Deliberadamente usa otro orden: el servicio debe reordenar por etiquetas.
    classes_ = np.array(["Empate", "Local", "Visitante"])

    def predict_proba(self, x):
        return np.tile([0.2, 0.5, 0.3], (len(x), 1))


class ModelTests(unittest.TestCase):
    def test_features_ignore_target_day_and_future_outcomes(self):
        data = synthetic_matches()
        before, history = match_features(data, "A", "B", "2024-09-06")
        altered = data.copy()
        altered.loc[altered.fecha >= "2024-09-06", ["goles_local_90", "goles_visitante_90"]] = 99
        altered.loc[altered.fecha >= "2024-09-06", "resultado"] = "Empate"
        after, _ = match_features(altered, "A", "B", "2024-09-06")
        self.assertEqual(before, after)
        self.assertEqual(history["local"]["ids_historial"], ["4", "3", "2", "1", "0"])
        self.assertEqual(history["local"]["fecha_ultimo_partido"], "2024-09-05")

    def test_exact_five_previous_games_required(self):
        with self.assertRaisesRegex(PredictionError, "hay 4"):
            match_features(synthetic_matches(), "A", "B", "2024-09-05")
        values, _ = match_features(synthetic_matches(), "A", "B", "2024-09-06")
        self.assertEqual(list(values), FEATURES)
        self.assertAlmostEqual(values["local_puntos_5"], 1.6)

    def test_exclusions_preserve_rows_and_never_fill_features_with_future(self):
        data = synthetic_matches()
        data.loc[7, "fase"] = "Final"
        table = build_training_table(data)
        self.assertEqual(len(table), len(data))
        self.assertEqual(table.exclusion.value_counts().to_dict(), {
            "menos_de_5_partidos_previos_por_equipo": 5, "final_sede_neutral": 1,
        })
        available = table[table.exclusion.isna()]
        self.assertEqual(len(available), 2)
        self.assertTrue((available.local_ultimo_previo < available.fecha).all())
        self.assertTrue((available.visitante_ultimo_previo < available.fecha).all())

    def test_pandemic_exclusions(self):
        self.assertIsNotNone(exclusion_reason({"temporada": "2020-21", "fase": "Grupos", "fecha": "2020-10-20"}))
        self.assertIsNotNone(exclusion_reason({"temporada": "2019-20", "fase": "Octavos", "fecha": "2020-08-07"}))
        self.assertIsNone(exclusion_reason({"temporada": "2019-20", "fase": "Octavos", "fecha": "2020-02-18"}))

    def test_prediction_probabilities_have_explicit_class_order_and_sum_one(self):
        probabilities = ordered_probabilities(FixedEstimator(), pd.DataFrame([[0] * 6], columns=FEATURES))
        np.testing.assert_allclose(probabilities[0], [0.5, 0.2, 0.3])
        self.assertAlmostEqual(probabilities[0].sum(), 1.0)

    def test_log_loss_uses_same_order_as_probabilities(self):
        data = pd.DataFrame([[0] * len(FEATURES)], columns=FEATURES)
        data["resultado"] = "Local"
        metrics, _ = metrics_for(FixedEstimator(), data)
        self.assertAlmostEqual(metrics["log_loss"], -np.log(0.5))
        self.assertEqual(metrics["matriz_confusion"], [[1, 0, 0], [0, 0, 0], [0, 0, 0]])

    def test_artifact_never_trained_on_target_day_or_future(self):
        report = {"artefactos": {"evaluado": {"entrenado_hasta": "2024-05-08"}, "actual": {"entrenado_hasta": "2026-05-06"}}}
        with self.assertRaises(PredictionError):
            choose_artifact(report, "2024-05-08")
        with self.assertRaises(PredictionError):
            choose_artifact(report, "2024-04-01")
        self.assertEqual(choose_artifact(report, "2024-09-17"), "evaluado")
        self.assertEqual(choose_artifact(report, "2026-05-06"), "evaluado")
        self.assertEqual(choose_artifact(report, "2026-05-07"), "actual")

    def test_status_detects_changed_csv(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="test_modelo_") as folder:
            root = Path(folder)
            (root / "models").mkdir()
            (root / "data/processed").mkdir(parents=True)
            csv = root / "data/processed/partidos.csv"
            csv.write_text("original", encoding="utf-8")
            report = {"dataset_sha256": sha256(csv), "artefactos": {}, "estado": "entrenado"}
            (root / "models/metricas.json").write_text(json.dumps(report), encoding="utf-8")
            csv.write_text("modificado", encoding="utf-8")
            self.assertEqual(get_status(root)["estado"], "desactualizado")

    def test_prediction_rejects_neutral_and_beyond_dataset(self):
        data = synthetic_matches()
        with self.assertRaisesRegex(PredictionError, "sede neutral"):
            predict_match(data, "A", "B", "2024-09-07", sede_neutral=True)
        with self.assertRaisesRegex(PredictionError, "hasta 2025-09-08"):
            predict_match(data, "A", "B", "2025-09-09")
        data.loc[7, "fase"] = "Final"
        with self.assertRaisesRegex(PredictionError, "final"):
            predict_match(data, "A", "B", "2024-09-08")

    def test_prediction_contract_and_stale_memory(self):
        data = synthetic_matches()
        report = {"modelo": "Prueba", "dataset_sha256": "dataset-prueba", "dataframe_sha256": dataframe_signature(data),
                  "artefactos": {"evaluado": {"entrenado_hasta": "2024-05-08", "sha256": "evaluado-prueba"},
                                "actual": {"entrenado_hasta": "2026-05-06", "sha256": "actual-prueba"}}}
        bundle = {"metadata": report, "evaluado": FixedEstimator(), "actual": FixedEstimator()}
        with patch("ml.model_service.load_bundle", return_value=bundle):
            result = predict_match(data, "A", "B", "2024-09-07")
            self.assertEqual(list(result["probabilidades"]), CLASSES)
            self.assertAlmostEqual(sum(result["probabilidades"].values()), 1.0)
            self.assertEqual(result["version_modelo"], "evaluado")
            self.assertEqual(result["resultado_mas_probable"], "Local")
            self.assertEqual(result["modelo_sha256"], "evaluado-prueba")
            self.assertEqual(result["dataset_sha256"], "dataset-prueba")
            self.assertTrue(result["emitido_utc"].endswith("+00:00"))
            report["artefactos"]["actual"]["entrenado_hasta"] = "2024-09-08"
            future_result = predict_match(data, "A", "B", "2024-09-10")
            self.assertEqual(future_result["version_modelo"], "actual")
            self.assertTrue(any("faltan los 2 días" in item for item in future_result["advertencias"]))
            changed = data.copy()
            changed.loc[0, "goles_local_90"] = 99
            with self.assertRaisesRegex(ModelUnavailableError, "memoria"):
                predict_match(changed, "A", "B", "2024-09-07")

    @unittest.skipUnless((ROOT / "models/metricas.json").exists(), "Artefactos aún no entrenados")
    def test_actual_artifact_matches_held_out_prediction_and_has_disjoint_ids(self):
        report = get_status(ROOT)
        self.assertEqual(report["estado"], "entrenado")
        self.assertLess(report["particiones"]["entrenamiento"]["fecha_hasta"], report["particiones"]["validacion"]["fecha_desde"])
        self.assertLess(report["particiones"]["validacion"]["fecha_hasta"], report["particiones"]["prueba"]["fecha_desde"])
        all_rows = pd.read_csv(ROOT / "models/variables_y_exclusiones.csv", encoding="utf-8-sig")
        test_rows = pd.read_csv(ROOT / "models/predicciones_prueba.csv", encoding="utf-8-sig")
        training_ids = set(all_rows.loc[all_rows.temporada <= "2023-24", "id"])
        self.assertFalse(training_ids & set(test_rows.id))
        real_data = pd.read_csv(ROOT / "data/processed/partidos.csv", encoding="utf-8-sig")
        chosen = test_rows.iloc[0]
        result = predict_match(real_data, chosen.local, chosen.visitante, chosen.fecha)
        for label in CLASSES:
            self.assertAlmostEqual(result["probabilidades"][label], chosen[f"probabilidad_{label.lower()}"], places=12)
        self.assertEqual(result["version_modelo"], "evaluado")


if __name__ == "__main__":
    unittest.main()
