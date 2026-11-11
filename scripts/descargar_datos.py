"""Descarga diez temporadas de OpenFootball fijadas a un mismo commit."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SEASONS = [f"{year}-{str(year+1)[-2:]}" for year in range(2016, 2026)]
REPO = "https://github.com/openfootball/champions-league"


def read_url(url):
    with urlopen(Request(url, headers={"User-Agent": "ProyectoAcademicoUCL/0.1"}), timeout=40) as response:
        return response.read()


def main(commit=None):
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    commit = json.loads(read_url(f"https://api.github.com/repos/openfootball/champions-league/commits/{commit or 'master'}"))["sha"]
    # Ningún archivo vigente se reemplaza si falla alguna descarga.
    with TemporaryDirectory(prefix="descarga_", dir=raw) as folder:
        staging = Path(folder)

        def fetch(season):
            url = f"https://raw.githubusercontent.com/openfootball/champions-league/{commit}/{season}/cl.txt"
            content = read_url(url)
            (staging / f"{season}.txt").write_bytes(content)
            return {"temporada": season, "archivo": f"data/raw/{season}.txt", "url": url,
                    "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}

        with ThreadPoolExecutor(max_workers=4) as executor:
            files = list(executor.map(fetch, SEASONS))
        license_url = f"https://raw.githubusercontent.com/openfootball/champions-league/{commit}/LICENSE.md"
        license_content = read_url(license_url)
        (staging / "LICENSE_OpenFootball.md").write_bytes(license_content)
        manifest = {"repositorio": REPO, "commit": commit, "licencia": "CC0-1.0",
                    "descargado_utc": datetime.now(timezone.utc).isoformat(), "archivos": files,
                    "archivo_licencia": {"archivo": "data/raw/LICENSE_OpenFootball.md", "url": license_url,
                                        "sha256": hashlib.sha256(license_content).hexdigest()}}
        for file in staging.iterdir():
            file.replace(raw / file.name)
        manifest_path = ROOT / "data/fuentes.json"
        pending_manifest = manifest_path.with_suffix(".tmp")
        pending_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        pending_manifest.replace(manifest_path)
    print(json.dumps({"commit": commit, "archivos": files}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", help="Commit o referencia de OpenFootball; por defecto master")
    main(parser.parse_args().commit)
