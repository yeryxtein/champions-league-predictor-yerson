"""Controles de fechas, resultados, cobertura y trazabilidad de OpenFootball."""
import csv
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.preparar_datos import ROOT, FIELDS, parse_file, parse_season, score90


class DataTests(unittest.TestCase):
    def parse_text(self, text, season="2024-25", reference=date(2026, 10, 29)):
        with tempfile.TemporaryDirectory(prefix="parser_", dir=ROOT / "tests") as folder:
            file = Path(folder) / f"{season}.txt"
            file.write_text(text, encoding="utf-8")
            return parse_season(file, "test", corrections=[], reference_date=reference)

    def test_league_january_and_playoffs_dates(self):
        played, pending, coverage, _ = self.parse_text(
            "# Matches 3\n▪ League, Matchday 6\nTue Dec 10\nA (ESP) v B (ENG) 1-0\n"
            "▪ League, Matchday 8\nWed Jan 29\nB (ENG) v A (ESP) 2-2\n"
            "▪ Playoffs, Matchday 1\nTue Feb 11\nA (ESP) v B (ENG) 0-1\n")
        self.assertEqual([r["fecha"] for r in played], ["2024-12-10", "2025-01-29", "2025-02-11"])
        self.assertEqual([r["fase"] for r in played], ["Liga", "Liga", "Playoffs"])
        self.assertEqual(pending, [])
        self.assertEqual(coverage["cobertura_resultados_pct"], 100)

    def test_pending_and_absent_are_not_fabricated_draws(self):
        played, pending, coverage, _ = self.parse_text(
            "# Matches 4\n▪ League, Matchday 1\nTue Sep 17 2024\nA (ESP) v B (ENG) 0-0\n"
            "C (ESP) v D (ENG)\n▪ League, Matchday 8\nWed Jan 29\nA (ESP) v C (ESP) -:-\n",
            reference=date(2024, 10, 1))
        self.assertEqual(len(played), 1)
        self.assertEqual(played[0]["resultado"], "Empate")
        self.assertEqual([r["estado"] for r in pending], ["Sin resultado", "Programado"])
        self.assertTrue(all(r["resultado"] is None and r["goles_local_90"] is None for r in pending))
        self.assertEqual(coverage["ausentes_en_fuente"], 1)
        self.assertEqual(coverage["cobertura_resultados_pct"], 25)
        self.assertEqual(coverage["estado"], "Parcial")

    def test_malformed_or_future_result_fails(self):
        for suffix in ("something unknown", "1-0 trailing text"):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                self.parse_text(f"# Matches 1\n▪ League, Matchday 1\nTue Sep 17 2024\nA (ESP) v B (ENG) {suffix}\n")
        with self.assertRaisesRegex(ValueError, "futuro"):
            self.parse_text("# Matches 1\n▪ League, Matchday 8\nWed Jan 29\nA (ESP) v B (ENG) 1-0\n", reference=date(2024, 10, 1))
        with self.assertRaisesRegex(ValueError, "Día de semana"):
            self.parse_text("# Matches 1\n▪ League, Matchday 8\nTue Jan 29\nA (ESP) v B (ENG) 1-0\n")

    def test_new_phase_requires_own_date(self):
        with self.assertRaisesRegex(ValueError, "Línea no reconocida"):
            self.parse_text("# Matches 2\n▪ League, Matchday 1\nTue Sep 17 2024\nA (ESP) v B (ENG) 1-0\n▪ Playoffs, Matchday 1\nA (ESP) v B (ENG) 2-0\n")

    def test_extra_time_never_becomes_90_minute_score(self):
        self.assertEqual(score90("3-2 a.e.t. (3-0, 1-0)"), (3, 0, True, False))
        self.assertEqual(score90("4-3 pen. 1-1 a.e.t. (1-1, 0-1)"), (1, 1, True, True))
        with self.assertRaises(ValueError):
            score90("4-3 pen.")

    def test_source_hashes_and_old_season_identity_preserved(self):
        manifest = json.loads((ROOT / "data/fuentes.json").read_text(encoding="utf-8"))
        for item in manifest["archivos"] + [manifest["archivo_licencia"]]:
            self.assertEqual(hashlib.sha256((ROOT / item["archivo"]).read_bytes()).hexdigest(), item["sha256"])
        rows = parse_file(ROOT / "data/raw/2019-20.txt", manifest["commit"])
        final = next(r for r in rows if r["fase"] == "Final")
        self.assertEqual(final["fecha"], "2020-08-23")
        self.assertEqual(len(rows), 119)

    def test_saved_dataset_and_corrections(self):
        with (ROOT / "data/processed/partidos.csv").open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, FIELDS)
            rows = list(reader)
        quality = json.loads((ROOT / "data/processed/calidad.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 1372)
        self.assertEqual(len({r["id"] for r in rows}), len(rows))
        self.assertEqual(quality["partidos"], len(rows))
        self.assertEqual(quality["fecha_hasta"], "2026-05-30")
        for season in ("2024-25", "2025-26"):
            self.assertEqual(quality["temporadas"][season], 189)
            self.assertEqual(quality["cobertura_temporadas"][season]["fases"]["Liga"], 144)
        psv = next(r for r in rows if r["fecha"] == "2025-02-19" and r["local"] == "PSV Eindhoven")
        inter = next(r for r in rows if r["fecha"] == "2025-05-06" and r["local"] == "Inter")
        self.assertEqual((psv["goles_local_90"], psv["goles_visitante_90"]), ("2", "1"))
        self.assertEqual((inter["goles_local_90"], inter["goles_visitante_90"], inter["resultado"]), ("3", "3", "Empate"))
        self.assertEqual(inter["marcador_original"], "4-3 (2-0)")
        self.assertEqual(len(quality["correcciones_90min"]), 2)
        self.assertTrue(all(c["fuente_verificacion"].startswith("https://www.uefa.com/") for c in quality["correcciones_90min"]))


if __name__ == "__main__":
    unittest.main()
