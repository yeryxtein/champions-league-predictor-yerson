"""Enfrentamientos directos: ambas localías, corte temporal y contrato HTTP."""
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from api import main


class DirectHistoryTests(unittest.TestCase):
    def setUp(self):
        # Los goles grandes del día de corte y del futuro hacen visible una fuga.
        self.data = pd.DataFrame([
            {"id": "1", "fecha": "2024-01-01", "local": "A", "visitante": "B", "goles_local_90": 2, "goles_visitante_90": 0},
            {"id": "2", "fecha": "2024-02-01", "local": "B", "visitante": "A", "goles_local_90": 3, "goles_visitante_90": 1},
            {"id": "3", "fecha": "2024-03-01", "local": "B", "visitante": "A", "goles_local_90": 1, "goles_visitante_90": 1},
            {"id": "4", "fecha": "2024-04-01", "local": "A", "visitante": "B", "goles_local_90": 20, "goles_visitante_90": 0},
            {"id": "5", "fecha": "2024-05-01", "local": "B", "visitante": "A", "goles_local_90": 0, "goles_visitante_90": 30},
            {"id": "6", "fecha": "2024-02-15", "local": "A", "visitante": "C", "goles_local_90": 9, "goles_visitante_90": 0},
        ])
        self.patch = patch.object(main, "DATA", self.data)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.cutoff = date(2024, 4, 1)

    def test_both_venues_are_included_and_other_opponents_excluded(self):
        result = main.direct_history("A", "B", self.cutoff)
        self.assertEqual([row["id"] for row in result["encuentros"]], ["3", "2", "1"])
        self.assertEqual(result["partidos"], 3)
        self.assertEqual(result["victorias_equipo_a"], 1)
        self.assertEqual(result["empates"], 1)
        self.assertEqual(result["victorias_equipo_b"], 1)
        self.assertEqual((result["goles_equipo_a"], result["goles_equipo_b"]), (4, 4))

    def test_reversing_teams_reverses_wins_and_goals(self):
        # Antes de marzo: A gana 2-0 y pierde 1-3; usamos también el primer cruce.
        for cutoff in (date(2024, 1, 2), date(2024, 2, 2)):
            normal = main.direct_history("A", "B", cutoff)
            reverse = main.direct_history("B", "A", cutoff)
            self.assertEqual(normal["victorias_equipo_a"], reverse["victorias_equipo_b"])
            self.assertEqual(normal["victorias_equipo_b"], reverse["victorias_equipo_a"])
            self.assertEqual(normal["goles_equipo_a"], reverse["goles_equipo_b"])
            self.assertEqual(normal["goles_equipo_b"], reverse["goles_equipo_a"])
            self.assertEqual(normal["empates"], reverse["empates"])
            self.assertEqual(normal["encuentros"], reverse["encuentros"])

    def test_same_day_and_future_are_excluded(self):
        result = main.direct_history("A", "B", self.cutoff)
        self.assertTrue(all(row["fecha"] < "2024-04-01" for row in result["encuentros"]))
        self.assertEqual(result["goles_equipo_a"], 4)
        next_day = main.direct_history("A", "B", date(2024, 4, 2))
        self.assertEqual(next_day["partidos"], result["partidos"] + 1)
        self.assertEqual(next_day["goles_equipo_a"], 24)

    def test_empty_history_has_explicit_zero_counts(self):
        result = main.direct_history("B", "C", self.cutoff)
        self.assertEqual(result["encuentros"], [])
        for field in ("partidos", "victorias_equipo_a", "empates", "victorias_equipo_b", "goles_equipo_a", "goles_equipo_b"):
            self.assertEqual(result[field], 0)

    def test_result_counts_reconcile_to_total(self):
        for cutoff in (date(2023, 1, 1), date(2024, 1, 2), self.cutoff, date(2024, 6, 1)):
            result = main.direct_history("A", "B", cutoff)
            self.assertEqual(result["partidos"], len(result["encuentros"]))
            self.assertEqual(result["partidos"], result["victorias_equipo_a"] + result["empates"] + result["victorias_equipo_b"])


class ComparisonContractTests(unittest.TestCase):
    def test_real_madrid_city_demo_at_90_minutes(self):
        result = main.compare(main.MatchRequest(local="Real Madrid", visitante="Manchester City", fecha=date(2024, 6, 2)))
        direct = result["enfrentamientos_directos"]
        self.assertEqual(result["fecha_corte"], "2024-06-02")
        self.assertFalse(result["es_prediccion"])
        self.assertEqual(result["local"]["partidos_usados"], 5)
        self.assertEqual(result["visitante"]["partidos_usados"], 5)
        self.assertEqual(direct["partidos"], 8)
        self.assertEqual((direct["victorias_equipo_a"], direct["empates"], direct["victorias_equipo_b"]), (1, 3, 4))
        self.assertEqual((direct["goles_equipo_a"], direct["goles_equipo_b"]), (12, 18))
        # Madrid avanza por penales en 2024; a los 90 minutos fue un empate.
        penalties = next(row for row in direct["encuentros"] if row["fecha"] == "2024-04-17")
        self.assertTrue(penalties["hubo_penales"])
        self.assertEqual((penalties["goles_local_90"], penalties["goles_visitante_90"]), (1, 1))

    def test_direct_history_is_not_limited_to_five(self):
        before = main.direct_history("Real Madrid", "Manchester City", date(2024, 4, 9))
        after = main.direct_history("Real Madrid", "Manchester City", date(2024, 4, 10))
        self.assertEqual(before["partidos"], 6)
        self.assertEqual(after["partidos"], 7)
        self.assertTrue(all(row["fecha"] < "2024-04-09" for row in before["encuentros"]))


class ComparisonHttpTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def test_http_response_contains_recent_and_direct_history(self):
        response = self.client.post("/comparaciones", json={"local": "Real Madrid", "visitante": "Manchester City", "fecha": "2024-06-02"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["es_prediccion"])
        self.assertEqual(body["local"]["partidos_usados"], 5)
        self.assertEqual(body["enfrentamientos_directos"]["partidos"], 8)
        self.assertNotIn("probabilidades", body)

    def test_http_validation_keeps_invalid_queries_out(self):
        for fields, expected in (
            ({"local": "Real Madrid", "visitante": "Real Madrid", "fecha": "2024-06-02"}, 422),
            ({"local": "Equipo inexistente", "visitante": "Manchester City", "fecha": "2024-06-02"}, 404),
            ({"local": "Real Madrid", "visitante": "Manchester City", "fecha": "2026-06-01"}, 422),
        ):
            with self.subTest(fields=fields):
                self.assertEqual(self.client.post("/comparaciones", json=fields).status_code, expected)


if __name__ == "__main__":
    unittest.main()
