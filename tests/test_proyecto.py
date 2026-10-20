"""Pruebas de la interpretación del marcador y de los contratos HTTP."""
import unittest
from datetime import date
import pandas as pd
from fastapi.testclient import TestClient
from api.main import app, DATA, team_history
from scripts.preparar_datos import score90

client = TestClient(app)


class ProjectTests(unittest.TestCase):
    def test_extra_time_uses_90_minute_result(self):
        self.assertEqual(score90("4-2 a.e.t. (1-2, 0-0)"), (1,2,True,False))
        self.assertEqual(score90("3-4 pen. 1-1 a.e.t. (1-1, 0-1)"), (1,1,True,True))
        self.assertEqual(score90("4-2 pen. 1-0 a.e.t. (1-0, 1-0)"), (1,0,True,True))
        with self.assertRaises(ValueError):
            score90("4-3 pen.")

    def test_snapshot_and_reconciled_counts(self):
        report=client.get("/calidad").json()
        self.assertEqual(len(DATA),994)
        self.assertEqual(sum(report["temporadas"].values()),len(DATA))
        self.assertEqual(DATA.id.nunique(),len(DATA))
        self.assertEqual(DATA.fecha.min(),"2016-09-13")
        self.assertEqual(DATA.fecha.max(),"2024-06-01")

    def test_filters_and_download_agree(self):
        params={"equipo":"Real Madrid","temporada":"2023-24"}
        res=client.get("/partidos",params=params).json()
        self.assertEqual(res["total"],13)
        self.assertTrue(all(r["temporada"]=="2023-24" and "Real Madrid" in [r["local"],r["visitante"]] for r in res["partidos"]))
        import io
        exported=pd.read_csv(io.BytesIO(client.get("/descargar",params=params).content))
        self.assertEqual(set(exported.id),{r["id"] for r in res["partidos"]})
        self.assertEqual(client.get("/resumen",params=params).json()["partidos"],13)

    def test_comparison_excludes_current_and_future_matches(self):
        item=team_history("Real Madrid",date(2024,4,9))
        self.assertEqual(item["partidos_usados"],5)
        self.assertTrue(all(r["fecha"]<"2024-04-09" for r in item["ultimos_partidos"]))
        self.assertEqual(item["ultimos_partidos"][0]["fecha"],"2024-03-06")

    def test_input_validation(self):
        data={"local":"Real Madrid","visitante":"Real Madrid","fecha":"2024-04-09"}
        self.assertEqual(client.post("/comparaciones",json=data).status_code,422)
        data["visitante"]="No existe"
        self.assertEqual(client.post("/comparaciones",json=data).status_code,404)
        data.update(visitante="Manchester City",fecha="2026-10-06")
        self.assertEqual(client.post("/comparaciones",json=data).status_code,422)
        self.assertEqual(client.get("/partidos?limite=0").status_code,422)
        self.assertEqual(client.get("/partidos?temporada=2099-00").status_code,404)

    def test_empty_history_is_explicit(self):
        item=team_history("Newcastle United FC",date(2016,9,14))
        self.assertEqual(item["partidos_usados"],0)
        self.assertIsNone(item["promedio_goles_favor"])
        self.assertEqual(item["ultimos_partidos"],[])

    def test_model_does_not_fabricate_predictions(self):
        response=client.post("/predicciones",json={"local":"Real Madrid","visitante":"Manchester City","fecha":"2024-04-09"})
        self.assertEqual(response.status_code,503)
        self.assertNotIn("probabilidades",response.json())


if __name__ == "__main__":
    unittest.main()
