"""Relative displacements, train lengths and short travel durations."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition

_MIN = r"минут(?:а|у|ы|е|ам)?"
_SEC = r"секунд(?:а|у|ы|е|ам)?"
TIME = rf"(?:{VALUE} {_MIN}(?: {VALUE} {_SEC})?|{VALUE} {_SEC})"
_PATTERNS = {
    "pole": rf"Поезд, двигаясь равномерно со скоростью (?P<speed>{VALUE}) км/ч, проезжает мимо придорожного столба за (?P<time>{TIME})\. Найдите длину поезда в метрах\.",
    "forest": rf"Поезд, двигаясь равномерно со скоростью (?P<speed>{VALUE}) км/ч, проезжает мимо лесополосы, длина которой равна (?P<obstacle>{VALUE}) метр(?:ам|ов), за (?P<time>{TIME})\. Найдите длину поезда в метрах\.",
    "same_trains": rf"По двум параллельным железнодорожным путям в одном направлении следуют пассажирский и товарный поезда, скорости которых равны соответственно (?P<first>{VALUE}) км/ч и (?P<second>{VALUE}) км/ч\. Длина товарного поезда равна (?P<obstacle>{VALUE}) метрам\. Найдите длину пассажирского поезда, если время, за которое он прошел мимо товарного поезда, равно (?P<time>{TIME})\. Ответ дайте в метрах\.",
    "opposite_trains": rf"По двум параллельным железнодорожным путям друг навстречу другу следуют скорый и пассажирский поезда, скорости которых равны соответственно (?P<first>{VALUE}) км/ч и (?P<second>{VALUE}) км/ч\. Длина пассажирского поезда равна (?P<obstacle>{VALUE}) метрам\. Найдите длину скорого поезда, если время, за которое он прошел мимо пассажирского поезда, равно (?P<time>{TIME})\. Ответ дайте в метрах\.",
    "walk_gap": rf"Два пешехода отправляются одновременно в одном направлении из одного и того же места на прогулку по аллее парка\. Скорость первого на (?P<gap>{VALUE}) км/ч больше скорости второго\. Через сколько минут расстояние между пешеходами станет равным (?P<distance>{VALUE}) метрам\?",
    "car_gap": rf"Автомобиль, движущийся с постоянной скоростью (?P<first>{VALUE}) км/ч по прямому шоссе, обгоняет другой автомобиль, движущийся в ту же сторону с постоянной скоростью (?P<second>{VALUE}) км/ч\. Каким будет расстояние ?\(в километрах\) ?между этими автомобилями через (?P<time>{TIME}) после обгона\?",
    "opposite_points": rf"Два мотоциклиста стартуют одновременно в одном направлении из двух диаметрально противоположных точек круговой трассы, длина которой равна (?P<distance>{VALUE}) км\. Через сколько минут мотоциклисты поравняются в первый раз, если скорость одного из них на (?P<gap>{VALUE}) км/ч больше скорости другого\?",
    "lap_speed": rf"Из одной точки круговой трассы, длина которой равна (?P<distance>{VALUE}) км, одновременно в одном направлении стартовали два автомобиля\. Скорость первого автомобиля равна (?P<first>{VALUE}) км/ч, и через (?P<time>{TIME}) после старта он опережал второй автомобиль на один круг\. Найдите скорость второго автомобиля\. Ответ дайте в км/ч\.",
    "lap_chase": rf"Из пункта [AА] круговой трассы выехал велосипедист\. Через (?P<lag_minutes>{VALUE}) минут(?:ы|а)? он еще не вернулся в пункт [AА] и из пункта [AА] следом за ним отправился мотоциклист\. Через (?P<catch_minutes>{VALUE}) минут(?:ы|а)? после отправления он догнал велосипедиста в первый раз, а еще через (?P<lap_minutes>{VALUE}) минут(?:ы|а)? после этого догнал его во второй раз\. Найдите скорость мотоциклиста, если длина трассы равна (?P<distance>{VALUE}) км\. Ответ дайте в км/ч\.",
}


@dataclass(frozen=True)
class ShortDuration:
    minutes: sp.Rational
    seconds: sp.Rational

    @property
    def total_seconds(self):
        return 60 * self.minutes + self.seconds


def duration(text):
    match = re.fullmatch(
        rf"(?:(?P<m>{VALUE}) {_MIN}(?: (?P<s>{VALUE}) {_SEC})?|(?P<only>{VALUE}) {_SEC})",
        text,
    )
    if not match:
        raise UnsupportedCondition(
            "a complete duration in minutes and seconds is required"
        )
    minutes, seconds = (
        scalar(match["m"] or "0"),
        scalar(match["s"] or match["only"] or "0"),
    )
    result = ShortDuration(minutes, seconds)
    if minutes < 0 or seconds < 0 or result.total_seconds <= 0:
        raise UnsupportedCondition("positive short duration is required")
    return result


@dataclass(frozen=True)
class Question:
    kind: str
    values: dict
    time: ShortDuration | None


def parse(text):
    for kind, pattern in _PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            values = {
                key: scalar(value)
                for key, value in match.groupdict().items()
                if key != "time"
            }
            if any(value <= 0 for value in values.values()):
                raise UnsupportedCondition("positive speeds and lengths are required")
            time = duration(match["time"]) if "time" in match.groupdict() else None
            return Question(kind, values, time)
    raise UnsupportedCondition(
        "the complete relative-motion question must be recognized"
    )
