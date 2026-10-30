"""Read complete sensor and spring questions with explicit angle and time units."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition, count
from .physical_questions import VALUE, scalar
from .rational_formula import RationalFormulaParser, canonical_formula

P, T = sp.symbols("p x", real=True)
_SENSOR = re.compile(
    rf"Датчик сконструирован таким образом, что его антенна ловит радиосигнал, который затем преобразуется в электрический сигнал, изменяющийся со временем по закону U=(?P<formula>.+?), где t — время в секундах, амплитуда U_0=(?P<amplitude>{VALUE}) В, частота \\omega=(?P<frequency>{VALUE})\s*°\s*/[сc], фаза \\varphi=(?P<phase>{VALUE})°\. Датчик настроен так, что если напряжение в нем не ниже чем (?P<level>{VALUE}) В, (?:то )?загорается лампочка\. Какую часть времени\(в процентах\)на протяжении первой секунды после начала работы лампочка будет гореть\?"
)
_SPRING = re.compile(
    rf"Скорость колеблющегося на пружине груза меняется по закону v\(t\)=(?P<formula>.+?)\(см/с\), где t — время в секундах\. Какую долю времени из (?P<window>первой секунды|первых .+? секунд) скорость движения (?P<relation>была не менее|превышала) (?P<level>{VALUE}) см/с\? Ответ выразите десятичной дробью, если нужно, округлите до сотых\."
)


@dataclass(frozen=True)
class Question:
    kind: str
    amplitude: sp.Rational
    frequency: sp.Rational  # Degrees per second; the original law keeps its units.
    phase: sp.Rational
    window: sp.Rational
    level: sp.Rational
    function: str
    strict: bool
    formula: str


def sensor(match):
    formula = re.fullmatch(
        r"U_0\\(?P<function>sin|cos)\(\\omegat\+\\varphi\)",
        re.sub(r"\s+", "", match["formula"]),
    )
    if not formula:
        raise UnsupportedCondition(
            "the sensor law must match its declared frequency and phase"
        )
    return Question(
        "sensor",
        scalar(match["amplitude"]),
        scalar(match["frequency"]),
        scalar(match["phase"]),
        sp.Integer(1),
        scalar(match["level"]),
        formula["function"],
        False,
        match["formula"],
    )


def spring(match):
    formula = re.fullmatch(
        rf"(?P<amplitude>{VALUE})\\(?P<function>sin|cos)\s*(?P<argument>.+)",
        match["formula"],
    )
    if not formula:
        raise UnsupportedCondition("one spring trigonometric law is required")
    parser = RationalFormulaParser(
        canonical_formula(formula["argument"], {r"\pi": "p", "t": "x"}), "px"
    )
    argument = parser.parse()
    frequency = sp.cancel(argument / (P * T))
    if frequency.is_Rational is not True or any(
        d.free_symbols or d == 0 for d in parser.denominators
    ):
        raise UnsupportedCondition(
            "a linear rational-pi phase without variable denominators is required"
        )
    window = (
        sp.Integer(1)
        if match["window"] == "первой секунды"
        else sp.Integer(
            count(match["window"].removeprefix("первых ").removesuffix(" секунд"))
        )
    )
    return Question(
        "spring",
        scalar(formula["amplitude"]),
        180 * frequency,
        sp.Integer(0),
        window,
        scalar(match["level"]),
        formula["function"],
        match["relation"] == "превышала",
        match["formula"],
    )


def parse(text):
    text = text.replace("ω", r"\omega").replace("φ", r"\varphi")
    text = re.sub(r"\bU\s+0\b", "U_0", text)
    for pattern, reader in [(_SENSOR, sensor), (_SPRING, spring)]:
        match = pattern.fullmatch(text)
        if match:
            q = reader(match)
            if min(q.amplitude, q.frequency, q.window) <= 0:
                raise UnsupportedCondition(
                    "positive amplitude, frequency and observation time are required"
                )
            return q
    raise UnsupportedCondition(
        "the complete harmonic-window question must be recognized"
    )
