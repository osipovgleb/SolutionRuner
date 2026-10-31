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
        return {"meeting": "t", "delayed_point": "S", "trip_time": "x"}.get(
            self.kind, "v"
        )


def parse(text):
    text = re.sub(r"\b[AB]\b", lambda m: {"A": "А", "B": "В"}[m[0]], text)
    for kind, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            data = match.groupdict()
            times = {
                key: duration(data[key]) for key in ("delay", "meeting") if key in data
            }
            values = {
                key: scalar(value)
                for key, value in data.items()
                if key not in {"delay", "meeting", "route", "place"}
            }
            if any(value <= 0 for value in values.values()):
                raise UnsupportedCondition(
                    "positive distances, speeds and bounds are required"
                )
            return Question(
                kind,
                values,
                times,
                data.get("route") == "В в А" or data.get("place") == "первым",
                "автомобиля" if "автомобиля отправляются" in text else "велосипедиста",
            )
    raise UnsupportedCondition("the complete road-motion question must be recognized")
