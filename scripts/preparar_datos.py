"""Convierte los TXT a CSV, preservando procedencia y el marcador a 90 minutos."""
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONTHS = {name: i for i, name in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MATCH = re.compile(r"^\s*(?:\d{1,2}:\d{2}\s+)?(.+?)\s+\(([A-Z]{3})\)\s+v\s+(.+?)\s+\(([A-Z]{3})\)\s+(.+)$")
DATE = re.compile(r"^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w{3})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
ALIASES = {
    "Club Atlético de Madrid": "Atlético Madrid", "FC Bayern München": "Bayern München",
    "FK Crvena Zvezda": "Crvena Zvezda", "Feyenoord Rotterdam": "Feyenoord",
    "Galatasaray SK": "Galatasaray", "FC Internazionale Milano": "Inter",
    "SS Lazio": "Lazio Roma", "Manchester City FC": "Manchester City",
    "Manchester United FC": "Manchester United", "Paris Saint-Germain FC": "Paris Saint-Germain",
    "PSV": "PSV Eindhoven", "FC Red Bull Salzburg": "RB Salzburg",
    "Real Madrid CF": "Real Madrid", "FK Shakhtar Donetsk": "Shakhtar Donetsk",
    "Sport Lisboa e Benfica": "SL Benfica",
}


def score90(raw):
    extra = "a.e.t." in raw
    penalties = "pen." in raw
    if extra:
        # football.txt: marcador120 a.e.t. (marcador90, marcador45).
        m = re.search(r"a\.e\.t\.\s*\((\d+)-(\d+),\s*\d+-\d+\)", raw)
    else:
        if penalties:
            raise ValueError(f"Penales sin marcador90 explícito: {raw}")
        m = re.fullmatch(r"(\d+)-(\d+)(?:\s+\(\d+-\d+\))?", raw.strip())
    if not m:
        raise ValueError(f"Marcador no reconocido: {raw}")
    return int(m[1]), int(m[2]), extra, penalties


def phase_name(text):
    if text.startswith(("Group", "Gruppe")):
        return "Grupos"
    for term, label in [("Round of 16", "Octavos"), ("Quarterfinals", "Cuartos"), ("Semifinals", "Semifinal"), ("Final", "Final")]:
        if term in text:
            return label
    raise ValueError(f"Fase desconocida: {text}")


def parse_file(file, commit):
    season = file.stem
    start_year = int(season[:4])
    content = file.read_text(encoding="utf-8")
    expected = int(re.search(r"# Matches\s+(\d+)", content)[1])
    phase = current_date = None
    rows = []
    for number, line in enumerate(content.splitlines(), 1):
        value = line.strip()
        if not value or value.startswith(("#", "=")):
            continue
        if value.startswith("▪"):
            phase = phase_name(value[1:].strip())
            continue
        dm = DATE.match(line)
        if dm:
            year = int(dm[4]) if dm[4] else start_year + (phase != "Grupos")
            current_date = date(year, MONTHS[dm[2]], int(dm[3]))
            if WEEKDAYS[current_date.weekday()] != dm[1]:
                raise ValueError(f"Día de semana inconsistente: {file.name}:{number}")
            continue
        m = MATCH.match(line)
        if not m or not current_date or not phase:
            raise ValueError(f"Línea no reconocida: {file.name}:{number}: {line}")
        home, home_country, away, away_country, raw_score = m.groups()
        hg, ag, extra, pen = score90(raw_score)
        home_clean, away_clean = ALIASES.get(home, home), ALIASES.get(away, away)
        if home_clean == away_clean:
            raise ValueError("Un equipo no puede jugar contra sí mismo")
        match_id = hashlib.sha256(f"{season}|{current_date}|{home_clean}|{away_clean}".encode()).hexdigest()[:16]
        rows.append({
            "id": match_id, "temporada": season, "fecha": current_date.isoformat(), "fase": phase,
            "local": home_clean, "visitante": away_clean, "pais_local": home_country, "pais_visitante": away_country,
            "goles_local_90": hg, "goles_visitante_90": ag,
            "resultado": "Local" if hg > ag else "Visitante" if ag > hg else "Empate",
            "hubo_prorroga": extra, "hubo_penales": pen,
            "local_original": home, "visitante_original": away, "marcador_original": raw_score,
            "fuente": f"https://github.com/openfootball/champions-league/blob/{commit}/{season}/cl.txt#L{number}",
        })
    if len(rows) != expected:
        raise ValueError(f"{season}: {len(rows)} partidos extraídos, {expected} declarados por la fuente")
    return rows


def main():
    manifest = json.loads((ROOT / "data/fuentes.json").read_text(encoding="utf-8"))
    rows = []
    for item in manifest["archivos"]:
        path = ROOT / item["archivo"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"El archivo {path.name} cambió respecto al manifiesto")
        rows.extend(parse_file(path, manifest["commit"]))
    rows.sort(key=lambda r: (r["fecha"], r["local"], r["visitante"]))
    duplicate_count = len(rows) - len({r["id"] for r in rows})
    if duplicate_count:
        raise ValueError(f"Se encontraron {duplicate_count} duplicados")
    output = ROOT / "data/processed"
    output.mkdir(parents=True, exist_ok=True)
    with (output / "partidos.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    aliases = sorted({(r[key+"_original"], r[key]) for r in rows for key in ["local", "visitante"]})
    with (output / "equipos_normalizados.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["nombre_original", "nombre_unificado"])
        writer.writerows(aliases)
    report = {
        "partidos": len(rows), "temporadas": dict(sorted(Counter(r["temporada"] for r in rows).items())),
        "equipos": len({r[k] for r in rows for k in ["local", "visitante"]}),
        "fecha_desde": rows[0]["fecha"], "fecha_hasta": rows[-1]["fecha"],
        "resultados": dict(Counter(r["resultado"] for r in rows)),
        "duplicados": duplicate_count, "faltantes_campos_exportados": sum(v is None or v == "" for r in rows for v in r.values()),
        "prorrogas": sum(r["hubo_prorroga"] for r in rows), "penales": sum(r["hubo_penales"] for r in rows),
        "nombres_unificados": sum(a != b for a, b in aliases), "registros_descartados": 0,
        "alcance": "Fase de grupos y eliminatorias de Champions, sin rondas clasificatorias",
        "objetivo": "Resultado tras 90 minutos más tiempo añadido, excluyendo prórroga y tanda de penales",
        "limitaciones": [
            "Fuente comunitaria. Los conteos coinciden con los encabezados de sus archivos, sin auditoría independiente de todos los resultados.",
            "Los datos terminan el 1 de junio de 2024. No describen el estado actual de los equipos.",
            "La fuente no proporciona una columna uniforme de sede neutral. Local y visitante son las designaciones del registro.",
            "No contiene lesiones, alineaciones ni el historial completo en otras competiciones.",
            "Aún no se ha entrenado ni evaluado un modelo predictivo.",
        ], "fuente": manifest,
    }
    (output / "calidad.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "fuente"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
