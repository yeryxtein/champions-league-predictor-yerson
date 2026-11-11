"""Convierte football.txt a CSV con fechas, cobertura y resultados a 90 minutos."""
import argparse
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
MATCH = re.compile(r"^\s*(?:\d{1,2}:\d{2}\s+)?(.+?)\s+\(([A-Z]{3})\)\s+v\s+(.+?)\s+\(([A-Z]{3})\)(?:\s+(.+))?$")
DATE = re.compile(r"^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w{3})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
FIELDS = ["id", "temporada", "fecha", "fase", "local", "visitante", "pais_local", "pais_visitante",
          "goles_local_90", "goles_visitante_90", "resultado", "hubo_prorroga", "hubo_penales",
          "local_original", "visitante_original", "marcador_original", "fuente"]
ALIASES = {
    "Club Atlético de Madrid": "Atlético Madrid", "FC Bayern München": "Bayern München",
    "FK Crvena Zvezda": "Crvena Zvezda", "Feyenoord Rotterdam": "Feyenoord",
    "Galatasaray SK": "Galatasaray", "FC Internazionale Milano": "Inter",
    "SS Lazio": "Lazio Roma", "Manchester City FC": "Manchester City",
    "Manchester United FC": "Manchester United", "Paris Saint-Germain FC": "Paris Saint-Germain",
    "PSV": "PSV Eindhoven", "FC Red Bull Salzburg": "RB Salzburg",
    "Real Madrid CF": "Real Madrid", "FK Shakhtar Donetsk": "Shakhtar Donetsk",
    "Sport Lisboa e Benfica": "SL Benfica", "Juventus FC": "Juventus",
    "Sporting Clube de Portugal": "Sporting CP", "GNK Dinamo Zagreb": "Dinamo Zagreb",
    "Bayer 04 Leverkusen": "Bayer Leverkusen", "AS Monaco FC": "AS Monaco",
    "Atalanta BC": "Atalanta", "Tottenham Hotspur FC": "Tottenham Hotspur",
    "Olympique de Marseille": "Olympique Marseille", "SK Slavia Praha": "Slavia Praha",
    "PAE Olympiakos SFP": "Olympiakos Piraeus", "Qarabağ Ağdam FK": "Qarabağ FK",
}


def score90(raw):
    extra = "a.e.t." in raw
    penalties = "pen." in raw
    if extra:
        # football.txt: marcador120 a.e.t. (marcador90, marcador45).
        m = re.fullmatch(r"(?:\d+-\d+ pen\.\s+)?\d+-\d+ a\.e\.t\.\s*\((\d+)-(\d+),\s*\d+-\d+\)", raw.strip())
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
    if text.startswith("League"):
        return "Liga"
    if text.startswith("Playoffs"):
        return "Playoffs"
    for term, label in [("Round of 16", "Octavos"), ("Quarterfinals", "Cuartos"), ("Semifinals", "Semifinal"), ("Final", "Final")]:
        if term in text:
            return label
    raise ValueError(f"Fase desconocida: {text}")


def infer_date(match, phase, start_year):
    month = MONTHS.get(match[2])
    if month is None:
        raise ValueError(f"Mes desconocido: {match[2]}")
    if match[4]:
        year = int(match[4])
    elif phase == "Grupos":
        year = start_year
    elif phase == "Liga":
        year = start_year + (month <= 6)
    else:
        # Conserva las eliminatorias de agosto de 2020.
        year = start_year + 1
    result = date(year, month, int(match[3]))
    if year not in (start_year, start_year + 1):
        raise ValueError(f"Fecha fuera de temporada: {result}")
    if WEEKDAYS[result.weekday()] != match[1]:
        raise ValueError(f"Día de semana inconsistente: {result}")
    return result


def parse_season(file, commit, corrections=None, reference_date=None):
    """Devuelve jugados, sin resultado, cobertura y auditoría sin omitir líneas."""
    season = file.stem
    start_year = int(season[:4])
    reference_date = reference_date or date.today()
    content = file.read_text(encoding="utf-8")
    header = re.search(r"# Matches\s+(\d+)", content)
    if not header:
        raise ValueError(f"{file.name}: falta el conteo declarado de partidos")
    expected = int(header[1])
    if corrections is None:
        corrections = json.loads((ROOT / "data/correcciones_90min.json").read_text(encoding="utf-8"))["correcciones"]
    correction_map = {(c["temporada"], c["fecha"], c["local"], c["visitante"]): c for c in corrections}
    phase = current_date = None
    played, pending, audits = [], [], []
    for number, line in enumerate(content.splitlines(), 1):
        value = line.strip()
        if not value or value.startswith(("#", "=")):
            continue
        if value.startswith("▪"):
            phase = phase_name(value[1:].strip())
            current_date = None
            continue
        dm = DATE.match(line)
        if dm:
            try:
                current_date = infer_date(dm, phase, start_year)
            except ValueError as exc:
                raise ValueError(f"{file.name}:{number}: {exc}") from exc
            continue
        m = MATCH.match(line)
        if not m or not current_date or not phase:
            raise ValueError(f"Línea no reconocida: {file.name}:{number}: {line}")
        home, home_country, away, away_country, raw_score = m.groups()
        raw_score = (raw_score or "").strip()
        home_clean, away_clean = ALIASES.get(home, home), ALIASES.get(away, away)
        if home_clean == away_clean:
            raise ValueError("Un equipo no puede jugar contra sí mismo")
        match_id = hashlib.sha256(f"{season}|{current_date}|{home_clean}|{away_clean}".encode()).hexdigest()[:16]
        row = {
            "id": match_id, "temporada": season, "fecha": current_date.isoformat(), "fase": phase,
            "local": home_clean, "visitante": away_clean, "pais_local": home_country, "pais_visitante": away_country,
            "goles_local_90": None, "goles_visitante_90": None, "resultado": None,
            "hubo_prorroga": None, "hubo_penales": None,
            "local_original": home, "visitante_original": away, "marcador_original": raw_score,
            "fuente": f"https://github.com/openfootball/champions-league/blob/{commit}/{season}/cl.txt#L{number}",
        }
        if raw_score in ("", "-", "-:-", "?-?", "TBD", "tbd", "ppd.", "postp."):
            row["estado"] = "Programado" if current_date >= reference_date else "Sin resultado"
            pending.append(row)
            continue
        if current_date > reference_date:
            raise ValueError(f"Resultado fechado en el futuro: {file.name}:{number}")
        hg, ag, extra, pen = score90(raw_score)
        correction = correction_map.get((season, current_date.isoformat(), home_clean, away_clean))
        if correction:
            corrected = (correction["goles_local_90"], correction["goles_visitante_90"], correction["hubo_prorroga"], correction["hubo_penales"])
            if raw_score == correction["marcador_fuente_esperado"]:
                hg, ag, extra, pen = corrected
                audits.append({"id": match_id, **correction, "fuente_original": row["fuente"]})
            elif (hg, ag, extra, pen) != corrected:
                raise ValueError(f"Cambió un marcador auditado; revisar {match_id}: {raw_score}")
        row.update(goles_local_90=hg, goles_visitante_90=ag, resultado="Local" if hg > ag else "Visitante" if ag > hg else "Empate",
                   hubo_prorroga=extra, hubo_penales=pen)
        played.append(row)
    extracted = len(played) + len(pending)
    if extracted > expected:
        raise ValueError(f"{season}: {extracted} partidos extraídos, más que los {expected} declarados")
    coverage = {
        "declarados_fuente": expected, "registros_fuente": extracted, "con_resultado": len(played),
        "sin_resultado": len(pending), "ausentes_en_fuente": expected - extracted,
        "cobertura_resultados_pct": round(len(played) / expected * 100, 2) if expected else 0,
        "estado": "Completa según conteo de la fuente" if len(played) == expected else "Parcial",
        "fecha_ultimo_resultado": max((r["fecha"] for r in played), default=None),
        "fases": dict(Counter(r["fase"] for r in played)),
    }
    return played, pending, coverage, audits


def parse_file(file, commit):
    """Compatibilidad para consumidores que necesitan sólo resultados terminados."""
    return parse_season(file, commit)[0]


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(reference_date=None):
    reference_date = reference_date or date.today()
    manifest = json.loads((ROOT / "data/fuentes.json").read_text(encoding="utf-8"))
    corrections_path = ROOT / "data/correcciones_90min.json"
    corrections = json.loads(corrections_path.read_text(encoding="utf-8"))["correcciones"]
    rows, pending, audits, coverage = [], [], [], {}
    for item in manifest["archivos"]:
        path = ROOT / item["archivo"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"El archivo {path.name} cambió respecto al manifiesto")
        played, scheduled, season_coverage, applied = parse_season(path, manifest["commit"], corrections, reference_date)
        rows.extend(played)
        pending.extend(scheduled)
        audits.extend(applied)
        coverage[item["temporada"]] = season_coverage
    license_info = manifest.get("archivo_licencia")
    if license_info and hashlib.sha256((ROOT / license_info["archivo"]).read_bytes()).hexdigest() != license_info["sha256"]:
        raise ValueError("La licencia original cambió respecto al manifiesto")
    for collection in (rows, pending):
        collection.sort(key=lambda r: (r["fecha"], r["local"], r["visitante"]))
    all_rows = rows + pending
    duplicate_count = len(all_rows) - len({r["id"] for r in all_rows})
    if duplicate_count:
        raise ValueError(f"Se encontraron {duplicate_count} duplicados")
    if not rows:
        raise ValueError("No hay resultados utilizables; no se reemplazará el dataset")
    output = ROOT / "data/processed"
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "partidos.csv", rows, FIELDS)
    write_csv(output / "programados.csv", pending, FIELDS + ["estado"])
    aliases = sorted({(r[key+"_original"], r[key]) for r in all_rows for key in ["local", "visitante"]})
    with (output / "equipos_normalizados.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
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
        "partidos_sin_resultado": len(pending), "archivo_sin_resultado": "data/processed/programados.csv",
        "cobertura_temporadas": coverage, "correcciones_90min": audits,
        "archivo_correcciones": {"archivo": "data/correcciones_90min.json", "sha256": hashlib.sha256(corrections_path.read_bytes()).hexdigest()},
        "fecha_referencia": reference_date.isoformat(),
        "alcance": "Fase de grupos o liga y eliminatorias de Champions, sin rondas clasificatorias",
        "objetivo": "Resultado tras 90 minutos más tiempo añadido, excluyendo prórroga y tanda de penales",
        "limitaciones": [
            "Fuente comunitaria. La cobertura compara con sus encabezados; no constituye una auditoría independiente de todos los resultados.",
            f"Último resultado disponible: {rows[-1]['fecha']}. No contiene la temporada 2026-27 ni se actualiza automáticamente.",
            "Los partidos sin resultado se conservan aparte, nunca se usan como ejemplos de entrenamiento ni como empates.",
            "Dos marcadores de 2024-25 se ajustaron a 90 minutos con fuentes oficiales documentadas en correcciones_90min.json.",
            "La fuente no proporciona una columna uniforme de sede neutral. Local y visitante son las designaciones del registro.",
            "No contiene lesiones, alineaciones ni el historial completo en otras competiciones.",
        ], "fuente": manifest,
    }
    (output / "calidad.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("fuente", "correcciones_90min")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fecha-referencia", type=date.fromisoformat, help="Fecha ISO para detectar resultados futuros")
    main(parser.parse_args().fecha_referencia)
