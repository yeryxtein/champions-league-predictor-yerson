"""Descarga una copia reproducible de ocho temporadas públicas de OpenFootball."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SEASONS = [f"{year}-{str(year+1)[-2:]}" for year in range(2016, 2024)]
REPO = "https://github.com/openfootball/champions-league"


def read_url(url):
    with urlopen(Request(url, headers={"User-Agent": "ProyectoAcademicoUCL/0.1"}), timeout=40) as response:
        return response.read()


def main():
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    commit = json.loads(read_url("https://api.github.com/repos/openfootball/champions-league/commits/master"))["sha"]

    def fetch(season):
        url = f"https://raw.githubusercontent.com/openfootball/champions-league/{commit}/{season}/cl.txt"
        content = read_url(url)
        (raw / f"{season}.txt").write_bytes(content)
        return {"temporada": season, "archivo": f"data/raw/{season}.txt", "url": url,
                "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}

    with ThreadPoolExecutor(max_workers=4) as executor:
        files = list(executor.map(fetch, SEASONS))
    license_url = f"https://raw.githubusercontent.com/openfootball/champions-league/{commit}/LICENSE.md"
    (raw / "LICENSE_OpenFootball.md").write_bytes(read_url(license_url))
    manifest = {"repositorio": REPO, "commit": commit, "licencia": "CC0-1.0",
                "descargado_utc": datetime.now(timezone.utc).isoformat(), "archivos": files}
    (ROOT / "data/fuentes.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"commit": commit, "archivos": files}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
