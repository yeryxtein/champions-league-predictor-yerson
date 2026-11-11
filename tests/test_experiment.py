"""Controles del criterio de selección y de las métricas por clase."""
import unittest
from unittest.mock import patch
import json
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from ml.experiment import PROTOCOL, code_signature, choose_candidate, get_report, measure, select_candidate
from ml.training import ROOT, sha256


class FixedProbabilities:
    classes_ = np.array(["Empate", "Visitante", "Local"])

    def predict_proba(self, table):
        return np.array([[0.6, 0.3, 0.1], [0.2, 0.7, 0.1], [0.2, 0.1, 0.7]])


class ExperimentTests(unittest.TestCase):
    def test_selection_rejects_test_rows_before_building_features(self):
        data = pd.DataFrame({"temporada": ["2024-25", "2025-26"]})
        with patch("ml.experiment.build_training_table_v2") as build:
            with self.assertRaisesRegex(ValueError, "anteriores"):
                select_candidate(data)
        build.assert_not_called()

    def test_selection_weights_f1_first_and_resolves_ties_deterministically(self):
        scores = {
            "Z": {"f1_macro_medio": 0.5, "log_loss_medio": 0.9},
            "A": {"f1_macro_medio": 0.5, "log_loss_medio": 0.9},
            "B": {"f1_macro_medio": 0.49, "log_loss_medio": 0.2},
            "C": {"f1_macro_medio": 0.5, "log_loss_medio": 1.0},
        }
        self.assertEqual(choose_candidate(scores), "A")

    def test_draw_counts_and_log_loss_use_explicit_class_order(self):
        table = pd.DataFrame({"x": [1, 2, 3], "resultado": ["Empate", "Empate", "Local"]})
        metrics, probabilities = measure(FixedProbabilities(), table, ["x"])
        np.testing.assert_allclose(probabilities[0], [0.1, 0.6, 0.3])
        self.assertEqual(metrics["empates"], {"reales": 2, "predichos": 1, "aciertos": 1, "recall": 0.5, "precision": 1.0})
        self.assertAlmostEqual(metrics["accuracy"], 2 / 3)
        self.assertAlmostEqual(metrics["log_loss"], -np.log([0.6, 0.2, 0.7]).mean())
        self.assertEqual(metrics["matriz_confusion"], [[1, 0, 0], [0, 1, 1], [0, 0, 0]])


class ReportPublicationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="informe_", dir=ROOT / "tests")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.output = self.root / "models/experimento_v2"
        self.output.mkdir(parents=True)
        (self.root / "data/processed").mkdir(parents=True)
        self.dataset = self.root / "data/processed/partidos.csv"
        self.dataset.write_text("datos de prueba", encoding="utf-8")

    def publish(self):
        selection = {"elegido": "RF6", "dataset_sha256": sha256(self.dataset),
                     "codigo_sha256": code_signature()}
        (self.output / "seleccion.json").write_text(json.dumps(selection), encoding="utf-8")
        (self.output / "predicciones.csv").write_text("predicciones de prueba", encoding="utf-8")
        metrics = {"partidos": 20, "accuracy": 0.5, "f1_macro": 0.3, "log_loss": 1.0,
                   "empates": {"reales": 4, "predichos": 3, "aciertos": 1}}
        self.report = {"estado": "evaluado", "protocolo": PROTOCOL, **selection,
                       "hashes": {"seleccion_sha256": sha256(self.output / "seleccion.json"),
                                  "predicciones_sha256": sha256(self.output / "predicciones.csv")},
                       "prueba": {"temporada": "2025-26", "utilizables": 20,
                                  "metricas": {role: metrics for role in ("elegido", "rf6", "referencia")}}}
        self.write_report()

    def write_report(self):
        (self.output / "informe.json").write_text(json.dumps(self.report), encoding="utf-8")

    def test_absent_and_in_progress_never_publish_old_metrics(self):
        self.assertEqual(get_report(self.root)["estado"], "pendiente")
        self.publish()
        self.assertEqual(get_report(self.root)["estado"], "evaluado")
        (self.output / ".evaluacion.lock").touch()
        result = get_report(self.root)
        self.assertEqual(result["estado"], "pendiente")
        self.assertNotIn("prueba", result)

    def test_interrupted_replacement_rejects_mixed_generation(self):
        self.publish()
        (self.output / "predicciones.csv").write_text("nueva generación incompleta", encoding="utf-8")
        result = get_report(self.root)
        self.assertEqual(result["estado"], "no_disponible")
        self.assertNotIn("prueba", result)

    def test_changed_data_or_protocol_requires_new_evaluation(self):
        self.publish()
        self.dataset.write_text("datos modificados", encoding="utf-8")
        self.assertEqual(get_report(self.root)["estado"], "desactualizado")
        self.publish()
        self.report["protocolo"] = "otro"
        self.write_report()
        self.assertEqual(get_report(self.root)["estado"], "desactualizado")

    def test_report_cannot_change_chosen_recipe_after_selection(self):
        self.publish()
        self.report["elegido"] = "Otro_modelo"
        self.write_report()
        self.assertEqual(get_report(self.root)["estado"], "no_disponible")


if __name__ == "__main__":
    unittest.main()
