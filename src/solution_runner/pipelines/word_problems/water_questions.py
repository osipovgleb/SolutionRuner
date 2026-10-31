"""Complete water-motion conditions mapped to the shared time-balance input."""

import re

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .motion_questions import DURATION, Duration, Question, duration

_END = r" Ответ дайте в км/ч\."
_TRIP = rf"Моторная лодка прошла против течения реки (?P<distance>{VALUE}) км и вернулась в пункт отправления, затратив на обратный путь на (?P<delay>{DURATION}) меньше\. Найдите скорость "
_STAY = rf"Теплоход проходит по течению реки до пункта назначения (?P<distance>{VALUE}) км и после стоянки возвращается в пункт отправления\. Найдите скорость "
_STAY_END = (
    rf", стоянка длится (?P<stop>{DURATION}), а в пункт отправления теплоход возвращается через (?P<elapsed>{DURATION}) после отплытия из него\."
    + _END
)
_CLOCK = rf"(?P<vessel>Моторная лодка|Байдарка|Баржа|Катер) в (?P<start>\d{{1,2}}:\d{{2}}) выш(?:ла|ел) из пункта А в пункт В, расположенный в (?P<distance>{VALUE}) км от А\. Пробыв в пункте В (?P<stop>{DURATION}), (?P<name>лодка|байдарка|баржа|катер) отправил(?:ась|ся) назад и вернул(?:ась|ся) в пункт А в (?P<end>\d{{1,2}}:\d{{2}}) того же дня\. Определите\(в км/(?:ч|час)\)"
_RATIO = rf"(?:\d+\\frac\{{\d+\}}\{{\d+\}}|{VALUE})"
PATTERNS = {
    "water_current_difference": _TRIP
    + rf"течения, если скорость лодки в неподвижной воде равна (?P<known>{VALUE}) км/ч\."
    + _END,
    "water_boat_difference": _TRIP
    + rf"лодки в неподвижной воде, если скорость течения равна (?P<known>{VALUE}) км/ч\."
    + _END,
    "water_current_stay": _STAY
    + rf"течения, если скорость теплохода в неподвижной воде равна (?P<known>{VALUE}) км/ч"
    + _STAY_END,
    "water_boat_stay": _STAY
    + rf"теплохода в неподвижной воде, если скорость течения равна (?P<known>{VALUE}) км/ч"
    + _STAY_END,
    "water_boat_clock": _CLOCK
    + rf"собственную скорость (?P<actor>лодки|байдарки|баржи|катера), если известно, что скорость течения реки (?P<known>{VALUE}) км/ч\.",
    "water_current_clock": _CLOCK
    + rf"скорость течения реки, если известно, что собственная скорость (?P<actor>лодки|байдарки|баржи|катера) равна (?P<known>{VALUE}) км/ч\.",
    "water_follow": rf"От пристани А к пристани В, расстояние между которыми равно (?P<distance>{VALUE}) км, отправился с постоянной скоростью первый теплоход, а через (?P<delay>{DURATION}) после этого следом за ним,? со скоростью,? на (?P<gap>{VALUE}) км/ч большей,? отправился второй\. Найдите скорость (?P<role>первого|второго) теплохода, если в пункт В (?:оба теплохода прибыли одновременно|он прибыл одновременно с первым)\."
    + _END,
    "water_lake_return": rf"Пристани А и В расположены на озере, расстояние между ними (?:равно )?(?P<distance>{VALUE}) км\. Баржа отправилась с постоянной скоростью из А в В\. На следующий день после прибытия она отправилась обратно со скоростью на (?P<gap>{VALUE}) км/ч больше прежней, сделав по пути остановку на (?P<delay>{DURATION})\. В результате она затратила на обратный путь столько же времени, сколько на путь из А в В\. Найдите скорость баржи на пути из (?P<route>А в В|В в А)\."
    + _END,
    "water_distance": rf"Теплоход, скорость которого в неподвижной воде равна (?P<boat>{VALUE}) км/ч, проходит по течению реки и после стоянки возвращается в исходный пункт\. Скорость течения равна (?P<current>{VALUE}) км/ч, стоянка длится (?P<stop>{DURATION}), а в исходный пункт теплоход возвращается через (?P<elapsed>{DURATION}) после отплытия из него\. Сколько километров про(?:шел|ходит) теплоход за весь рейс\?",
    "water_raft": rf"Расстояние между пристанями А и В равно (?P<distance>{VALUE}) км\. Из А в В по течению реки отправился плот, а через (?P<delay>{DURATION}) вслед за ним отправилась яхта, которая, прибыв в пункт В, тотчас повернула обратно и возвратилась в А\. К этому времени плот про(?:шел|плыл) (?P<raft_distance>{VALUE}) км\. Найдите скорость яхты в неподвижной воде, если скорость течения реки равна (?P<known>{VALUE}) км/ч\."
    + _END,
    "water_upgrade": rf"Между пристанями А и Б по озеру курсировал старый катер\. Потом его заменили катером на подводных крыльях, скорость которого на (?P<gap>{VALUE}) км/ч больше\. Поэтому время в пути от А до Б сократилось на (?P<delay>{DURATION})\. Найдите скорость старого катера, если расстояние между пристанями равно (?P<distance>{VALUE}) км\."
    + _END,
    "water_season_current": rf"Весной катер идет против течения реки в (?P<spring_ratio>{_RATIO}) раза медленнее, чем по течению\. Летом течение становится на (?P<gap>{VALUE}) км/(?:;)?ч медленнее\. Поэтому летом катер идет против течения в (?P<summer_ratio>{_RATIO}) раза медленнее, чем по течению\. Найдите (?P<target>скорость течения весной|собственную скорость катера)\(в км/ч\)\.",
}


def ratio(text):
    match = re.fullmatch(r"(\d+)\\frac\{(\d+)\}\{(\d+)\}", text)
    if not match:
        return scalar(text)
    whole, numerator, denominator = map(int, match.groups())
    if not 0 < numerator < denominator:
        raise UnsupportedCondition(
            "a proper nonzero fractional part of a mixed ratio is required"
        )
    return sp.Integer(whole) + sp.Rational(numerator, denominator)


def clock_minutes(text):
    hours, minutes = map(int, text.split(":"))
    if not 0 <= hours < 24 or not 0 <= minutes < 60:
        raise UnsupportedCondition("a valid departure or arrival time is required")
    return sp.Integer(60 * hours + minutes)


def prepare(kind, data):
    time_keys = {"delay", "stop", "elapsed"}
    words = {"vessel", "name", "actor", "start", "end", "role", "route", "target"}
    times = {key: duration(value) for key, value in data.items() if key in time_keys}
    values = {
        key: ratio(value) if key.endswith("_ratio") else scalar(value)
        for key, value in data.items()
        if key not in time_keys | words
    }
    if any(v <= 0 for v in values.values()):
        raise UnsupportedCondition("positive water distances and speeds are required")
    actor = data.get("actor", "теплохода")
    if "vessel" in data:
        name, expected = {
            "Моторная лодка": ("лодка", "лодки"),
            "Байдарка": ("байдарка", "байдарки"),
            "Баржа": ("баржа", "баржи"),
            "Катер": ("катер", "катера"),
        }[data["vessel"]]
        if (data["name"], actor) != (name, expected):
            raise UnsupportedCondition(
                "one consistent vessel in the complete clock trip is required"
            )
        start, end = clock_minutes(data["start"]), clock_minutes(data["end"])
        if end <= start:
            raise UnsupportedCondition("same-day arrival must follow departure")
        values.update(start_minute=start, end_minute=end)
        times["elapsed"] = Duration((end - start) / 60, sp.Integer(0))
    if "stop" in times:
        moving = times["elapsed"].total - times["stop"].total
        if moving <= 0:
            raise UnsupportedCondition("the stop must leave positive sailing time")
        times["moving"] = Duration(moving, sp.Integer(0))
    if kind == "water_raft":
        actor = "яхты"
    if kind in {"water_current_difference", "water_boat_difference"}:
        actor = "лодки"
    if (
        kind == "water_season_current"
        and data["target"] == "собственную скорость катера"
    ):
        kind = "water_season_boat"
    return Question(
        kind,
        values,
        times,
        data.get("role") == "второго" or data.get("route") == "В в А",
        actor,
    )


def parse_water(text):
    for kind, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            return prepare(kind, match.groupdict())
    raise UnsupportedCondition("the complete road-motion question must be recognized")
