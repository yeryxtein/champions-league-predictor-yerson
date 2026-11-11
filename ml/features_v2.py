"""Forma reciente, fuerza Elo y cruces previos de Champions a 90 minutos."""
from collections import defaultdict, deque
from itertools import groupby
from typing import NamedTuple

import pandas as pd

from ml.features import FEATURES, WINDOW, exclusion_reason

FEATURES_V2 = [
    *FEATURES, "local_empates_5", "visitante_empates_5", "elo_diferencia",
    "directos_partidos_5", "directos_local_suavizado", "directos_empate_suavizado",
    "directos_visitante_suavizado",
]
METADATA = ["id", "temporada", "fecha", "local", "visitante", "resultado"]


class TeamGame(NamedTuple):
    date: str
    scored: int
    conceded: int


class History:
    def __init__(self):
        self.form = defaultdict(lambda: deque(maxlen=WINDOW))
        self.direct = defaultdict(lambda: deque(maxlen=WINDOW))
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, home, away):
        values = {}
        for side, team in (("local", home), ("visitante", away)):
            games = self.form[team]
            wins = sum(game.scored > game.conceded for game in games)
            draws = sum(game.scored == game.conceded for game in games)
            values[f"{side}_puntos_5"] = (3 * wins + draws) / WINDOW
            values[f"{side}_goles_favor_5"] = sum(game.scored for game in games) / WINDOW
            values[f"{side}_goles_contra_5"] = sum(game.conceded for game in games) / WINDOW
            values[f"{side}_empates_5"] = draws / WINDOW
            values[f"{side}_ultimo_previo"] = games[-1].date

        values["elo_diferencia"] = self.elo[home] - self.elo[away]
        winners = self.direct[tuple(sorted((home, away)))]
        values["directos_partidos_5"] = len(winners)
        # Un voto inicial por clase impide sobreinterpretar una muestra pequeña.
        for label, winner in (("local", home), ("empate", None), ("visitante", away)):
            values[f"directos_{label}_suavizado"] = (1 + winners.count(winner)) / (3 + len(winners))
        return values

    def advance_day(self, matches):
        """Todos los cambios de Elo parten de los valores al inicio del día."""
        changes = defaultdict(float)
        # La v1 elige primero el id menor en empates de fecha. Al recorrer el
        # día al revés, esos identificadores permanecen al final de la deque.
        for match in reversed(matches):
            home, away = match["local"], match["visitante"]
            gf, ga = int(match["goles_local_90"]), int(match["goles_visitante_90"])
            self.form[home].append(TeamGame(match["fecha"], gf, ga))
            self.form[away].append(TeamGame(match["fecha"], ga, gf))
            winner = home if gf > ga else away if ga > gf else None
            self.direct[tuple(sorted((home, away)))].append(winner)
            expected = 1 / (1 + 10 ** ((self.elo[away] - self.elo[home]) / 400))
            actual = float(gf > ga) + 0.5 * (gf == ga)
            change = 20 * (actual - expected)
            changes[home] += change
            changes[away] -= change
        for team, delta in changes.items():
            self.elo[team] += delta


def build_training_table_v2(data):
    """Calcula primero todos los ejemplos del día y después incorpora los resultados."""
    history = History()
    rows = []
    records = data.sort_values(["fecha", "id"]).to_dict(orient="records")
    for _, records_day in groupby(records, key=lambda record: record["fecha"]):
        matches = list(records_day)
        for record in matches:
            row = {key: record[key] for key in METADATA}
            home, away = record["local"], record["visitante"]
            reason = exclusion_reason(record)
            if not reason and min(len(history.form[home]), len(history.form[away])) < WINDOW:
                reason = "menos_de_5_partidos_previos_por_equipo"
            row["exclusion"] = reason
            if not reason:
                row.update(history.features(home, away))
            rows.append(row)
        # Las sedes excluidas como objetivos sí cuentan como historial futbolístico.
        history.advance_day(matches)
    columns = [*METADATA, "exclusion", *FEATURES_V2, "local_ultimo_previo", "visitante_ultimo_previo"]
    return pd.DataFrame.from_records(rows, columns=columns)
