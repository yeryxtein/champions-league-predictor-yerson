"""Recorrido reproducible de Streamlit con peticiones HTTP a la API local.

Ejecutar con el entorno del proyecto y la API abierta mediante INICIAR.cmd.
AppTest comprueba los controles y resultados; no sustituye la revisión visual
en un navegador. Sólo los fallos de conexión/modelo se simulan al final.
"""
from datetime import date
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
API = os.environ.get("CHAMPIONS_API_URL", "http://127.0.0.1:8000").rstrip("/")


def main():
    try:
        health = requests.get(API + "/salud", timeout=(3, 10))
        health.raise_for_status()
        status = health.json()
        if status.get("proyecto") != "champions-lab" or status["modelo"]["estado"] != "entrenado":
            raise ValueError("La API debe pertenecer a Champions Lab y tener el modelo entrenado.")
    except (requests.RequestException, ValueError, KeyError) as error:
        raise SystemExit(f"No se puede iniciar la prueba. Abre INICIAR.cmd primero. Detalle: {error}")

    checks = []
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=55).run()

    def ok(label):
        if at.exception or at.error:
            raise AssertionError(f"{label}: {[e.value for e in at.exception]} {[e.value for e in at.error]}")
        checks.append(label)
        print("OK - " + label, flush=True)

    def click(label):
        next(button for button in at.button if button.label == label).click().run()

    def example():
        at.button(key="load_prediction_example").click().run()

    def calculate():
        click("Calcular estimación")

    def rejected(label, message):
        assert not at.exception, [e.value for e in at.exception]
        assert any(message in e.value for e in at.error), [e.value for e in at.error]
        assert "prediction_result" not in at.session_state, "Quedó visible una estimación anterior"
        assert not at.get("download_button"), "Se puede descargar un resultado anterior al error"
        checks.append(label)
        print("OK - " + label, flush=True)

    assert [metric.value for metric in at.metric[:2]] == ["1372", "96"]
    assert len(at.dataframe[0].value) == 1372
    ok("Exploración completa: 1.372 partidos y 96 equipos")
    for season in ["2024-25", "2025-26"]:
        at.selectbox[0].set_value(season).run()
        assert at.metric[0].value == "189"
        response = requests.get(API + "/descargar", params={"temporada": season}, timeout=(3, 10))
        response.raise_for_status()
        csv = pd.read_csv(io.BytesIO(response.content))
        assert len(csv) == 189 and set(csv.temporada) == {season}
        ok("Temporada " + season + ": filtro y descarga CSV coinciden")

    at.radio[0].set_value("Comparar equipos").run()
    for cutoff, count in [(date(2024, 6, 2), 8), (date(2024, 4, 9), 6)]:
        at.date_input[0].set_value(cutoff)
        click("Comparar historial")
        result = at.session_state["comparison_result"]
        direct = result["enfrentamientos_directos"]
        assert direct["partidos"] == count
        assert all(row["fecha"] < cutoff.isoformat() for row in direct["encuentros"])
        if count == 8:
            assert [direct[k] for k in ["victorias_equipo_a", "empates", "victorias_equipo_b"]] == [1, 3, 4]
        ok(f"Cruces directos: {count} antes de {cutoff}")
    at.date_input[0].set_value(date(2016, 9, 14))
    click("Comparar historial")
    assert at.session_state["comparison_result"]["enfrentamientos_directos"]["partidos"] == 0
    assert any("No hay enfrentamientos" in item.value for item in at.info)
    ok("Historial vacío explicado sin fabricar cruces")

    at.radio[0].set_value("Predicción experimental").run()
    example()
    assert at.selectbox(key="predict_local").value == "Real Madrid"
    assert at.selectbox(key="predict_away").value == "Manchester City"
    assert at.date_input(key="predict_date").value == date(2025, 2, 19)
    assert not at.checkbox(key="predict_neutral").value
    assert "prediction_result" not in at.session_state
    calculate()
    result = at.session_state["prediction_result"]
    assert result["version_modelo"] == "evaluado"
    assert result["emitido_utc"].endswith("+00:00")
    assert len(result["dataset_sha256"]) == len(result["modelo_sha256"]) == 64
    assert result["entrenado_hasta"] < result["fecha_corte"]
    assert abs(sum(result["probabilidades"].values()) - 1) < 1e-10
    held_out = pd.read_csv(ROOT / "models/predicciones_prueba.csv", encoding="utf-8-sig")
    expected = held_out[(held_out.fecha == "2025-02-19") & (held_out.local == "Real Madrid")].iloc[0]
    for label, probability in result["probabilidades"].items():
        assert abs(probability - expected["probabilidad_" + label.lower()]) < 1e-10
    assert [item.value for item in at.metric[-3:]] == [f"{p:.1%}" for p in result["probabilidades"].values()]
    assert any(item.key == "download_prediction" for item in at.get("download_button"))
    ok("Ejemplo por HTTP: probabilidades coinciden con la prueba histórica guardada")
    history_table = at.dataframe[-1].value
    assert history_table["Partidos previos"].tolist() == [5, 5]
    assert all(day < result["fecha_corte"] for day in history_table["Último partido usado"])
    assert history_table["Puntos / partido"].tolist() == [2.4, 0.8]
    ok("Interfaz muestra las variables previas y permite descargar la estimación")

    at.selectbox(key="predict_away").set_value("Real Madrid")
    calculate()
    rejected("Equipos iguales: error y resultado anterior retirado", "equipos diferentes")
    example()
    at.checkbox(key="predict_neutral").check()
    calculate()
    rejected("Sede neutral: consulta bloqueada", "sede neutral")
    example()
    at.selectbox(key="predict_away").set_value("Paphos FC")
    calculate()
    rejected("Historial insuficiente: mensaje de la API", "se necesitan 5 partidos")

    # Fallos controlados: no se detiene ni altera el servidor real.
    example()
    calculate()
    with patch("requests.post", side_effect=requests.ReadTimeout("Prueba controlada")):
        calculate()
    rejected("Demora de la API: mensaje específico y sin resultado antiguo", "tardó demasiado")
    response = requests.Response()
    response.status_code = 503
    response._content = json.dumps({"detail": "Modelo no disponible: prueba controlada"}).encode()
    with patch("requests.post", return_value=response):
        calculate()
    rejected("Error 503: se conserva la explicación de la API", "Modelo no disponible")
    with patch("requests.post", side_effect=requests.ConnectionError("Prueba controlada")):
        calculate()
    rejected("API desconectada: instrucciones para iniciarla", "INICIAR.cmd")

    real_get = requests.get

    def unavailable(url, **kwargs):
        if url == API + "/modelo":
            response = requests.Response()
            response.status_code = 200
            response._content = json.dumps({"estado": "desactualizado", "mensaje": "Los datos cambiaron; vuelve a entrenar."}).encode()
            return response
        return real_get(url, **kwargs)

    with patch("requests.get", side_effect=unavailable):
        at.run()
    assert not any(button.label == "Calcular estimación" for button in at.button)
    assert any("no está disponible" in item.value for item in at.info)
    ok("Modelo desactualizado: formulario de predicción deshabilitado")
    for page in ["Calidad de los datos", "Avance del proyecto"]:
        at.radio[0].set_value(page).run()
        assert at.dataframe
        ok("Página " + page + " sin excepciones")
    at.radio[0].set_value("Evaluación de mejoras").run()
    response = real_get(API + "/experimentos/mejoras", timeout=(3, 10))
    response.raise_for_status()
    experiment = response.json()
    assert experiment["estado"] == "evaluado", experiment
    assert [item.value for item in at.metric] == [str(experiment["prueba"][key]) for key in ("total", "utilizables", "excluidos")]
    table = at.dataframe[0].value
    for index, role in enumerate(("elegido", "rf6", "referencia")):
        expected = experiment["prueba"]["metricas"][role]
        assert table.iloc[index]["Exactitud"] == f'{expected["accuracy"]:.1%}'
        assert table.iloc[index]["Empates acertados"] == expected["empates"]["aciertos"]
        assert table.iloc[index]["Empates reales"] == expected["empates"]["reales"]
    assert any(item.key == "download_experiment" for item in at.get("download_button"))
    ok("Evaluación ampliada: tabla y descarga con los resultados de la API")

    def changed_experiment(url, **kwargs):
        if url == API + "/experimentos/mejoras":
            response = requests.Response()
            response.status_code = 200
            response._content = json.dumps({"estado": "desactualizado", "mensaje": "Los datos cambiaron; repite la evaluación."}).encode()
            return response
        return real_get(url, **kwargs)

    with patch("requests.get", side_effect=changed_experiment):
        at.run()
    assert not at.dataframe and not at.get("download_button")
    assert any("Los datos cambiaron" in item.value for item in at.info)
    ok("Evaluación desactualizada: métricas retiradas y aviso")
    print(f"\n{len(checks)} comprobaciones de interfaz superadas con AppTest y la API por HTTP.")


if __name__ == "__main__":
    main()
