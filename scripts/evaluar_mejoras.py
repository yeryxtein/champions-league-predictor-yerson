"""Ejecuta el protocolo fijo de mejoras con artefactos en models/experimento_v2."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.experiment import run_experiment


if __name__ == "__main__":
    report = run_experiment(ROOT)
    print(json.dumps({"elegido": report["elegido"], "prueba": report["prueba"]}, ensure_ascii=False, indent=2))
