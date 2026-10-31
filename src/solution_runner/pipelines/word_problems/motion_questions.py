"""Complete road-motion statements with exact durations and requested roles."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition

HOUR = rf"(?:(?:{VALUE}|один|два|три|четыре) )?час(?:а|ов)?"
DURATION = rf"(?:{HOUR}(?: {VALUE} минут(?:а|ы)?)?|{VALUE} минут(?:а|ы)?)"
SPEED_ANSWER = r" Ответ (?:дайте в км/ч|запишите в километрах в час)\."
HALF_START = r"Из (?:пункта )?А в (?:пункт )?В одновременно выехали два (?:автомобиля|автомобилиста)\. Первый проехал с постоянной скоростью весь путь\. Второй проехал первую половину пути со скоростью"
HALF_END = r", в результате чего прибыл в (?:пункт )?В одновременно с первым (?:автомобилем|автомобилистом)\. Найдите скорость первого (?:автомобиля|автомобилиста)"
DELAY_START = (
    r"Расстояние между городами А и В равно (?P<distance>"
    + VALUE
    + r") км\. Из города А в город В"
)
PATTERNS = {
    "half_gain": HALF_START
    + rf" (?P<known>{VALUE}) км/ч, а вторую половину пути — со скоростью, на (?P<gap>{VALUE}) км/ч большей скорости первого"
    + HALF_END
    + r"\."
    + SPEED_ANSWER,
    "half_loss": HALF_START
    + rf", меньшей скорости первого на (?P<gap>{VALUE}) км/ч, а вторую половину пути — со скоростью (?P<known>{VALUE}) км/ч"
    + HALF_END
    + rf", если известно, что она больше (?P<minimum>{VALUE}) км/ч\."
    + SPEED_ANSWER,
    "later": rf"Из пункта А в пункт В, расстояние между которыми (?P<distance>{VALUE}) км, одновременно выехали автомобилист и велосипедист\. Известно, что (?:за|в) час автомобилист проезжает на (?P<gap>{VALUE}) км больше, чем велосипедист\. Определите скорость велосипедиста, если известно, что он прибыл в пункт В на (?P<delay>{DURATION}) позже автомобилиста\."
    + SPEED_ANSWER,
    "return": rf"Велосипедист выехал с постоянной скоростью из города А в город В, расстояние между которыми равно (?P<distance>{VALUE}) км\. На следующий день он отправился обратно(?: в А)? со скоростью на (?P<gap>{VALUE}) км/ч больше прежней\. По дороге он сделал остановку на (?P<delay>{DURATION})\. В результате (?:велосипедист|он) затратил на обратный путь столько же времени, сколько на путь из А в В\. Найдите скорость велосипедиста на пути из (?P<route>В в А|А в В)\."
    + SPEED_ANSWER,
    "race": rf"Два (?:велосипедиста одновременно отправились|автомобиля отправляются) в (?P<distance>{VALUE})-километровый пробег\. Первый (?:ехал|едет) со скоростью,? на (?P<gap>{VALUE}) км/ч большей, чем (?:скорость второго|второй), и (?:прибыл|прибывает) к финишу на (?P<delay>{DURATION}) раньше второго\. Най(?:ти|дите) скорость (?:велосипедиста|автомобиля), пришедшего к финишу (?P<place>первым|вторым)\.(?:"
    + SPEED_ANSWER
    + r")?",
    "meeting": rf"Из двух городов, расстояние между которыми равно (?P<distance>{VALUE}) км, навстречу друг другу одновременно выехали два автомобиля\. Через сколько часов автомобили встретятся, если их скорости равны (?P<first>{VALUE}) км/ч и (?P<second>{VALUE}) км/ч\?",
    "meeting_point": rf"Из городов А и В, расстояние между которыми равно (?P<distance>{VALUE}) км, навстречу друг другу одновременно выехали два автомобиля и встретились через (?P<delay>{DURATION}) на расстоянии (?P<point>{VALUE}) км от города В\. Найдите скорость автомобиля, выехавшего из города А\."
    + SPEED_ANSWER,
    "delayed_point": DELAY_START
    + rf" со скоростью (?P<first>{VALUE}) км/ч выехал первый автомобиль, а через (?P<delay>{DURATION}) после этого навстречу ему из города В выехал со скоростью (?P<second>{VALUE}) км/ч второй автомобиль\. На каком расстоянии от города А автомобили встретятся\? Ответ дайте в километрах\.",
    "delayed_speed": DELAY_START
    + rf" выехал первый автомобиль, а через (?P<delay>{DURATION}) после этого навстречу ему из города В выехал со скоростью (?P<second>{VALUE}) км/ч второй автомобиль\. Найдите скорость первого автомобиля, если автомобили встретились на расстоянии (?P<point>{VALUE}) км от города А\."
    + SPEED_ANSWER,
    "trip_time": rf"Из городов А и В навстречу друг другу (?:одновременно )?выехали мотоциклист и велосипедист\. Мотоциклист приехал в В на (?P<delay>{DURATION}) раньше, чем велосипедист приехал в А, а встретились они через (?P<meeting>{DURATION}) после выезда\. Сколько часов затратил на путь из В в А велосипедист\?",
    "freight": rf"Товарный поезд каждую минуту проезжает на (?P<metres_per_minute>{VALUE}) метров меньше, чем скорый, и на путь в (?P<distance>{VALUE}) км тратит времени на (?P<delay>{DURATION}) больше, чем скорый\. Найдите скорость товарного поезда\."
    + SPEED_ANSWER,
    "catch_return": DELAY_START
    + rf" выехал автомобиль, а через (?P<delay>{DURATION}) следом за ним со скоростью (?P<known>{VALUE}) км/ч выехал (?:мотоциклист|мотоцикл), догнал автомобиль в городе С и повернул обратно\. Когда (?:он|мотоцикл) вернулся в А, автомобиль прибыл в В\. Найдите расстояние от А до С\. Ответ дайте в километрах\.",
    "third_cyclist": rf"Первый велосипедист выехал из поселка по шоссе со скоростью (?P<first>{VALUE}) км/ч\. Через час после него со скоростью (?P<second>{VALUE}) км/ч из того же поселка в том же направлении выехал второй велосипедист, а еще через час после этого — третий\. Найдите скорость третьего велосипедиста, если сначала он догнал второго, а через (?P<delay>{DURATION}) после этого догнал первого\."
    + SPEED_ANSWER,
    "walk_return": rf"Два человека отправляются (?:одновременно )?из одного дома на прогулку до опушки леса, находящейся в (?P<distance>{VALUE}) км от дома\. (?:Один|Первый) идет со скоростью (?P<slow>{VALUE}) км/ч, а (?:другой|второй) — со скоростью (?P<fast>{VALUE}) км/ч\. Дойдя до опушки, второй (?:разворачивается и )?с той же скоростью возвращается обратно\. На каком расстоянии от (?:дома|точки отправления) произойдет их встреча\? Ответ дайте в километрах\.",
    "downhill": rf"Дорога между пунктами А и В состоит из подъема и спуска, а ее длина равна (?P<distance>{VALUE}) км\. Путь из А в В занял у туриста (?P<total>{DURATION}), из которых (?P<down>{DURATION}) уш(?:ел|ло) на спуск\. Найдите скорость туриста на спуске, если она больше скорости на подъеме на (?P<gap>{VALUE}) км/ч\."
    + SPEED_ANSWER,
    "stopped": rf"Автомобиль выехал с постоянной скоростью (?P<known>{VALUE}) км/ч из города А в город В, расстояние между которыми равно (?P<reference_distance>{VALUE}) км\. Одновременно с ним из города С в город В, расстояние между которыми равно (?P<distance>{VALUE}) км, с постоянной скоростью выехал мотоциклист\. По дороге он сделал остановку на (?P<delay>{DURATION})\. В результате автомобиль и мотоцикл прибыли в город В одновременно\. Найдите скорость мотоциклиста\."
    + SPEED_ANSWER,
    "named_stop": rf"Иван и Алексей договорились встретиться в Н-ске\. Они едут к Н-ску разными дорогами\. Иван звонит Алексею и узнает, что тот находится в (?P<reference_distance>{VALUE}) км от Н-ска и едет с постоянной скоростью (?P<known>{VALUE}) км/ч\. Иван в момент звонка находится в (?P<distance>{VALUE}) км от Н-ска и еще должен по дороге сделать (?P<stop_minutes>{VALUE})-минутную остановку\. С какой скоростью должен ехать Иван, чтобы прибыть в Н-ск одновременно с Алексеем\?",
    "midpoint": rf"Из двух городов, расстояние между которыми (?P<distance>{VALUE}) км, по параллельным путям отправляются навстречу друг другу два поезда и встречаются на середине пути\. Второй поезд вышел на (?P<lag_hours>{VALUE}) ч позже первого со скоростью, на (?P<gap>{VALUE}) км/ч большей, чем скорость первого поезда\. Найдите скорость второго поезда\."
    + SPEED_ANSWER,
    "lap_race": rf"Два гонщика участвуют в гонках\. Им предстоит проехать (?P<laps>{VALUE}) кругов по кольцевой трассе протяженностью (?P<circumference>{VALUE}) км\. Оба гонщика стартовали одновременно, а на финиш первый пришел раньше второго на (?P<delay>{DURATION})\. Чему равнялась средняя скорость второго гонщика, если известно, что первый гонщик в первый раз обогнал второго на круг через (?P<lap_time>{DURATION})\? Ответ дайте в км/ч\.",
}


@dataclass(frozen=True)
class Duration:
    hours: sp.Rational
    minutes: sp.Rational

    @property
    def total(self):
        return self.hours + self.minutes / 60


def duration(text):
    match = re.fullmatch(
        rf"(?:(?P<h>{VALUE}|один|два|три|четыре)? ?час(?:а|ов)?(?: (?P<m>{VALUE}) минут(?:а|ы)?)?|(?P<only>{VALUE}) минут(?:а|ы)?)",
        text,
    )
    if not match:
        raise UnsupportedCondition(
            "a complete duration in hours and minutes is required"
        )
    words = {
        None: sp.Integer(1),
        "один": sp.Integer(1),
        "два": sp.Integer(2),
        "три": sp.Integer(3),
        "четыре": sp.Integer(4),
    }
    hours = 0 if match["only"] is not None else words.get(match["h"])
    if hours is None:
        hours = scalar(match["h"])
    minutes = scalar(match["m"] or match["only"] or "0")
    result = Duration(sp.Rational(hours), minutes)
    if hours < 0 or minutes < 0 or result.total <= 0:
        raise UnsupportedCondition("positive duration is required")
    return result


@dataclass(frozen=True)
class Question:
    kind: str
    values: dict
    durations: dict
    target_fast: bool = False
    actor: str = "велосипедиста"

    @property
    def symbol(self):
        return {
            "meeting": "t",
            "delayed_point": "S",
            "trip_time": "x",
            "catch_return": "t",
            "third_cyclist": "t",
            "third_cyclist_speed": "x",
            "midpoint": "x",
            "walk_return": "x",
            "downhill": "x",
        }.get(self.kind, "v")


def parse(text):
    text = re.sub(r"\b[ABC]\b", lambda m: {"A": "А", "B": "В", "C": "С"}[m[0]], text)
    for kind, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            data = match.groupdict()
            times = {
                key: duration(data[key])
                for key in ("delay", "meeting", "total", "down", "lap_time")
                if key in data
            }
            values = {
                key: scalar(value)
                for key, value in data.items()
                if key
                not in {
                    "delay",
                    "meeting",
                    "total",
                    "down",
                    "lap_time",
                    "route",
                    "place",
                }
            }
            if any(value <= 0 for value in values.values()):
                raise UnsupportedCondition(
                    "positive distances, speeds and bounds are required"
                )
            if "stop_minutes" in values:
                times["delay"] = Duration(sp.Integer(0), values["stop_minutes"])
            if "lag_hours" in values:
                times["delay"] = Duration(values["lag_hours"], sp.Integer(0))
            if "metres_per_minute" in values:
                values["gap"] = values["metres_per_minute"] * sp.Rational(3, 50)
            if kind == "lap_race":
                if values["laps"].is_Integer is not True:
                    raise UnsupportedCondition(
                        "an integral number of complete race laps is required"
                    )
                values["distance"] = values["laps"] * values["circumference"]
                values["gap"] = values["circumference"] / times["lap_time"].total
            return Question(
                kind,
                values,
                times,
                data.get("route") == "В в А" or data.get("place") == "первым",
                "автомобиля" if "автомобиля отправляются" in text else "велосипедиста",
            )
    raise UnsupportedCondition("the complete road-motion question must be recognized")
