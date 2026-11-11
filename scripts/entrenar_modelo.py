"""Ejecutar desde cualquier carpeta: python scripts/entrenar_modelo.py."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.training import train


if __name__ == "__main__":
    report = train(ROOT)
    print(json.dumps({"modelo": report["modelo"], "particiones": report["particiones"], "prueba": report["prueba"]}, ensure_ascii=False, indent=2))
