"""Verifica el orden temporal real, la perspectiva de localía y la paridad con v1."""
import unittest

import pandas as pd

from ml.features import FEATURES, build_training_table
from ml.features_v2 import FEATURES_V2, build_training_table_v2


def match(day, identifier, home, away, gf, ga, phase="Liga"):
    return {
        "id": identifier, "fecha": f"2024-09-{day:02}", "temporada": "2024-25",
        "fase": phase, "local": home, "visitante": away,
        "goles_local_90": gf, "goles_visitante_90": ga,
        "resultado": "Local" if gf > ga else "Visitante" if gf < ga else "Empate",
    }


class FeatureV2Tests(unittest.TestCase):
    def test_v1_eligibility_and_base_values_including_id_tie_break(self):
        # Seis partidos sintéticos del mismo día fuerzan el desempate por ID.
        records = [match(1, str(i), "A", "B", i, 0) for i in reversed(range(6))]
        records += [match(2, "normal", "B", "A", 2, 1), match(3, "final", "B", "A", 0, 0, "Final")]
        data = pd.DataFrame(records)
        v1 = build_training_table(data).set_index("id")
        v2 = build_training_table_v2(data).set_index("id")
        cols = [*FEATURES, "exclusion", "local_ultimo_previo", "visitante_ultimo_previo"]
        pd.testing.assert_frame_equal(v1[cols], v2[cols])
        self.assertTrue(v2.loc["final", FEATURES_V2].isna().all())
        self.assertEqual(v2.loc["normal", "visitante_empates_5"], 0.2)

    def test_same_day_and_future_outcomes_never_change_its_features(self):
        records = [match(i, str(i), "A", "B", 1, 1) for i in range(1, 6)]
        records += [match(6, "am", "A", "B", 2, 0), match(6, "pm", "A", "B", 1, 0),
                    match(7, "next", "A", "B", 1, 0)]
        original = build_training_table_v2(pd.DataFrame(records)).set_index("id")
        altered = [row if row["fecha"] < "2024-09-06" else {**row, "resultado": "Visitante",
                  "goles_local_90": 0, "goles_visitante_90": 9} for row in records]
        changed = build_training_table_v2(pd.DataFrame(altered)).set_index("id")
        day = ["am", "pm"]
        pd.testing.assert_frame_equal(original.loc[day, FEATURES_V2], changed.loc[day, FEATURES_V2])
        self.assertEqual(original.loc["pm", "elo_diferencia"], 0)
        # Cada victoria sobre un club de la misma fuerza aporta 10 puntos
        # al ganador y resta 10 al perdedor. Los dos cambios se aplican juntos.
        self.assertEqual(original.loc["next", "elo_diferencia"], 40)
        self.assertEqual(changed.loc["next", "elo_diferencia"], -40)

    def test_direct_history_smoothing_both_venues_and_only_five_recent_games(self):
        records = []
        for day in range(1, 6):
            records += [match(day, f"a{day}", "A", "C", 1, 0), match(day, f"b{day}", "D", "B", 1, 0)]
        records += [match(6, "first", "A", "B", 2, 0), match(7, "reverse", "B", "A", 0, 0)]
        records += [match(day, f"a{day}", "A", "B", 0, 1) for day in range(8, 12)]
        records += [match(12, "last", "B", "A", 1, 0)]
        table = build_training_table_v2(pd.DataFrame(records)).set_index("id")
        self.assertEqual(table.loc["first", "directos_partidos_5"], 0)
        for name in ["local", "empate", "visitante"]:
            self.assertAlmostEqual(table.loc["first", f"directos_{name}_suavizado"], 1 / 3)
        self.assertEqual(table.loc["reverse", "directos_partidos_5"], 1)
        self.assertAlmostEqual(table.loc["reverse", "directos_visitante_suavizado"], 0.5)
        self.assertEqual(table.loc["last", "directos_partidos_5"], 5)
        self.assertAlmostEqual(table.loc["last", "directos_local_suavizado"], 5 / 8)
        self.assertAlmostEqual(table.loc["last", "directos_empate_suavizado"], 2 / 8)
        self.assertAlmostEqual(table.loc["last", "directos_visitante_suavizado"], 1 / 8)
