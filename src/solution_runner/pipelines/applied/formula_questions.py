"""Complete scalar formula questions and equivalent source unit notation."""

import re
from dataclasses import dataclass, field

import sympy as sp

from ..calculus.common import T, polynomial
from ..equations.laurent_arithmetic import names, symbolic
from ..equations.laurent_parser import LaurentParser
from ..probability.common import UnsupportedCondition
from .inverse_patterns import KINDS as INVERSE_KINDS
from .inverse_patterns import PATTERNS as INVERSE_PATTERNS
from .physical_questions import scalar

P, Q, V, L, R, H, D, S = sp.symbols("p q v l r h d s", real=True)
_KGCM = r"кг\s*\\cdot\s*см\^\{2\}"
_SHIP = r"На верфи инженеры проектируют новый аппарат для погружения на небольшие глубины\. "
_CUBE = (
    _SHIP
    + r"Конструкция имеет кубическую форму, а значит, действующая на аппарат выталкивающая\(архимедова\)сила, выражаемая в ньютонах, будет определяться по формуле:? F_A=(?P<formula>.+?), где l — длина ребра куба в метрах, \\rho=(?P<density>.+?)\s*кг/м\^\{3\} — плотность воды, а g — ускорение свободного падения\(считайте(?:, что)? g=(?P<gravity>.+?)\s*Н/кг\)\. Какой может быть максимальная длина ребра куба, чтобы обеспечить его эксплуатацию в условиях, когда выталкивающая сила при погружении будет не больше,? чем (?P<target>.+?) Н\? Ответ (?:выразите|дайте) в метрах\."
)
_SPHERE = (
    _SHIP
    + r"Конструкция имеет форму сферы, а значит, действующая на аппарат выталкивающая\(архимедова\)сила, выражаемая в ньютонах, будет определяться по формуле: F_A=(?P<formula>.+?), где \\alpha=(?P<alpha>.+?) — постоянная, r — радиус аппарата в метрах, \\rho=(?P<density>.+?)\s*кг/м\^\{3\} — плотность воды, а g — ускорение свободного падения\(считайте g=(?P<gravity>.+?) Н/кг\)\. Каков может быть максимальный радиус аппарата, чтобы выталкивающая сила при погружении была не больше, чем (?P<target>.+?) Н\? Ответ выразите в метрах\."
)
_SPHERE_VARIANT = (
    _SHIP
    + r"Конструкция имеет форму сферы, действующая на нее выталкивающая\(архимедова\)сила, выражаемая в ньютонах, определяется по формуле F_A=(?P<formula>.+?), где \\alpha=(?P<alpha>.+?) — постоянная, r — радиус сферы в метрах, \\rho=(?P<density>.+?)\s*кг/м\^\{3\} — плотность воды, а g=(?P<gravity>.+?) Н/кг — ускорение свободного падения\. Найдите наибольшую длину радиуса сферы\(в метрах\), при которой выталкивающая сила при погружении не превосходит (?P<target>.+?) Н\."
)
_PATTERNS = (
    (
        "thermal",
        re.compile(
            r"При температуре 0°C рельс имеет длину l_0=(?P<length>.+?) м\. При возрастании температуры происходит тепловое расширение рельса, и его длина, выраженная в метрах, меняется по закону l\(t°\)=(?P<formula>.+?), где \\alpha=(?P<alpha>.+?)\(°C\)\^\{-1\} — коэффициент теплового расширения, t° — температура\(в градусах Цельсия\)\. При какой температуре рельс удлинится на (?P<increase>.+?) мм\? Ответ выразите в градусах Цельсия\."
        ),
    ),
    (
        "profit",
        re.compile(
            r"Некоторая компания продает свою продукцию по цене p=(?P<price>.+?) руб\. за единицу, переменные затраты на производство одной единицы продукции составляют v=(?P<cost>.+?) руб\., постоянные расходы предприятия f=(?P<overhead>.+?) руб\. в месяц\. Месячная операционная прибыль предприятия\(в рублях\)вычисляется по формуле \\pi\(q\)=(?P<formula>.+?)\. Определите месячный объем производства q\(единиц продукции\), при котором месячная операционная прибыль предприятия будет равна (?P<target>.+?) руб\."
        ),
    ),
    (
        "market",
        re.compile(
            r"Зависимость объема спроса q\(единиц в месяц\)на продукцию предприятия(?: — |-| )монополиста от цены p\(тыс\. руб\.\)задается формулой q=(?P<demand>.+?)\. Выручка предприятия за месяц r\((?:в )?тыс\. руб\.\)вычисляется по формуле r\(p\)=(?P<formula>.+?)\. Определите наибольшую цену p, при которой месячная выручка(?: r\(p\))?\s*составит (?P<relation>не менее )?(?P<target>.+?) тыс\. руб\. Ответ приведите в тыс\. руб\."
        ),
    ),
    (
        "bucket",
        re.compile(
            r"Если достаточно быстро вращать ведерко с водой на веревке в вертикальной плоскости, то вода не будет выливаться\. При вращении ведерка сила давления воды на дно не остается постоянной: она максимальна в нижней точке и минимальна в верхней\. Вода не будет выливаться, если сила ее давления на дно будет положительной во всех точках траектории,? кроме верхней, где она может быть равной нулю\. В верхней точке сила давления, выраженная в ньютонах, равна P=(?P<formula>.+?), где m — масса воды в килограммах, v(?: —)? скорость движения ведерка в м/с, L — длина веревки в метрах, g — ускорение свободного падения\(считайте g=(?P<gravity>.+?) м/с\^\{2\}\)\. С какой наименьшей скоростью надо вращать ведерко, чтобы вода не выливалась, если длина веревки равна (?P<length>.+?) см\? Ответ выразите в м/с\."
        ),
    ),
    (
        "inertia",
        re.compile(
            r"Деталью некоторого прибора является вращающаяся катушка\. Она состоит из трех однородных соосных цилиндров: центрального массой m=(?P<mass>.+?) кг и радиуса R=(?P<radius>.+?) см, и двух боковых с массами M=(?P<side>.+?) кг и с радиусами R\+h\. При этом момент инерции катушки относительно оси вращения, выражаемый в "
            + _KGCM
            + r",? дается формулой I=(?P<formula>.+?)\. При каком максимальном значении h момент инерции катушки не превышает предельного значения (?P<target>.+?)\s*"
            + _KGCM
            + r"\? Ответ выразите в сантиметрах\."
        ),
    ),
    ("cube", re.compile(_CUBE)),
    ("sphere", re.compile(_SPHERE)),
    ("sphere", re.compile(_SPHERE_VARIANT)),
    (
        "stars",
        re.compile(
            r"Для определения эффективной температуры звезд используют закон Стефана-Больцмана, согласно которому P=(?P<formula>.+?), где P — мощность излучения звезды\(в ваттах\), \\sigma=(?P<sigma>.+?)\\frac\{Вт\}\{м\^\{2\}\\cdot\s*К\^\{4\}\} — постоянная, S — площадь поверхности звезды\(в квадратных метрах\), а T — температура\(в кельвинах\)\. Известно, что площадь поверхности некоторой звезды равна (?P<surface>.+?) м\^\{2\}, а мощность ее излучения равна (?P<target>.+?)\s*Вт\. Найдите температуру этой звезды в кельвинах\."
        ),
    ),
)


@dataclass(frozen=True)
class Question:
    kind: str
    expression: sp.Expr
    variable: sp.Symbol
    label: str
    target: sp.Rational
    relation: str
    unit: str
    values: dict = field(default_factory=dict)
    demand: sp.Expr | None = None
    source_values: dict = field(default_factory=dict)


def normalize(text):
    for unit in ["C", "кг", "см", "Н", "Вт", "К", "Дж"]:
        text = text.replace(r"\mathrm{" + unit + "}", unit)
    text = text.replace(r"\,", "").replace("не-которой", "некоторой")
    text = (
        text.replace(r"F_{А}", "F_A")
        .replace(r"F_{A}", "F_A")
        .replace("ρ", r"\rho")
        .replace("α", r"\alpha")
    )
    text = text.replace(r"F_{\mathrm{А}}", "F_A")
    text = text.replace("CM^2", "см^{2}")
    text = re.sub(r"l\s+_0", "l_0", text)
    text = re.sub(r"t\s+°", "t°", text)
    text = re.sub(r"([cmtq])\s+_(в|др|[12])", r"\1_\2", text)
    for name, suffix, alias in [
        ("c", "в", "c_w"),
        ("m", "в", "m_w"),
        ("q", "др", "q_d"),
        ("m", "др", "m_d"),
    ]:
        text = text.replace(name + r"_{\mathrm{" + suffix + "}}", alias).replace(
            name + "_" + suffix, alias
        )
    return text.replace("π", r"\pi")


def bind(formula, variable, values, *, positive_variable=False):
    for alias, name in [
        ("c_w", "a"),
        ("m_w", "n"),
        ("q_d", "q"),
        ("m_d", "m"),
        ("t_1", "b"),
        ("t_2", "h"),
        (r"\alpha", "a"),
        (r"\sigma", "a"),
        (r"\rho", "d"),
        (r"\pi", "a"),
        ("D", "d"),
        ("U", "u"),
        ("l_0", "q"),
        ("M", "n"),
        ("R", "r"),
        ("L", "l"),
        ("S", "s"),
        ("T", "t"),
    ]:
        formula = formula.replace(alias, name)
    formula = formula.replace("°", "")
    declared = "".join(sorted({variable.name, *values}))
    formula = re.sub(r"([" + declared + r"])\s*\(", r"\1*(", formula)
    parser = LaurentParser(formula)
    parsed = parser.parse()
    if names(parsed) - {variable.name, *values}:
        raise UnsupportedCondition("an undeclared formula variable remains")
    for name in parser.nonzero:
        if positive_variable and name == variable.name:
            continue
        value = values.get(name)
        if value is None or value.free_symbols or value.is_zero is not False:
            raise UnsupportedCondition(
                "every original denominator must be an assigned nonzero constant"
            )
    expression = symbolic(parsed).subs(
        {sp.Symbol(k, real=True): v for k, v in values.items()}
    )
    return sp.expand(expression)


def make_question(kind, match):
    values = {
        k: scalar(v.replace(" ", ""))
        for k, v in match.groupdict().items()
        if k not in ["formula", "demand", "relation", "maximum"] and v is not None
    }
    variable, label, unit = {
        "thermal": (T, "t", r"{}^{\circ}\mathrm{C}"),
        "profit": (Q, "q", "ед."),
        "market": (P, "p", "тыс. руб."),
        "bucket": (V, "v", "м/с"),
        "inertia": (H, "h", "см"),
        "cube": (L, "l", "м"),
        "sphere": (R, "r", "м"),
        "stars": (T, "T", "К"),
        "fuse": (R, "R", "Ом"),
        "excavator": (S, "s", "м"),
        "column": (D, "D", "м"),
        "traction": (T, "t", "с"),
        "boiler": (sp.Symbol("m", real=True), r"m_{\mathrm{др}}", "кг"),
    }[kind]
    names = {
        "thermal": {"length": "q", "alpha": "a"},
        "profit": {"price": "p", "cost": "v", "overhead": "f"},
        "market": {},
        "bucket": {"length": "l", "gravity": "g"},
        "inertia": {"mass": "m", "side": "n", "radius": "r"},
        "cube": {"density": "d", "gravity": "g"},
        "sphere": {"alpha": "a", "density": "d", "gravity": "g"},
        "stars": {"sigma": "a", "surface": "s"},
        "fuse": {"voltage": "u"},
        "excavator": {"mass": "m", "length": "l", "gravity": "g"},
        "column": {"mass": "m", "gravity": "g", "pi": "a"},
        "traction": {"mass": "m", "distance": "s"},
        "boiler": {"heat": "a", "water": "n", "fuel": "q", "start": "b", "end": "h"},
    }[kind]
    bindings = {name: values[key] for key, name in names.items()}
    if kind == "bucket":
        bindings["l"] /= 100
    demand = polynomial(match["demand"], P) if kind == "market" else None
    if kind == "market":
        bindings["q"] = demand
    if kind == "bucket":
        bindings["m"] = sp.Symbol("m", real=True)
    expression = bind(
        match["formula"],
        variable,
        bindings,
        positive_variable=kind in INVERSE_KINDS,
    )
    target = values.get("target", sp.Integer(0))
    relation = (
        "eq"
        if kind in ["thermal", "profit", "stars"]
        or kind == "market"
        and not match["relation"]
        else "ge"
        if kind in ["market", "bucket"]
        else "le"
    )
    if kind == "thermal":
        target = values["increase"] / 1000
        expression -= values["length"]
    if kind == "traction":
        relation = "eq" if match["relation"] == "равна" else "ge"
        if bool(match["maximum"]) != (relation == "ge"):
            raise UnsupportedCondition(
                "the time request must agree with the force relation"
            )
    return Question(
        kind,
        sp.expand(expression),
        variable,
        label,
        target,
        relation,
        unit,
        values,
        demand,
        {k: v for k, v in match.groupdict().items() if k in values},
    )


def parse(text):
    text = normalize(text)
    for kind, pattern in _PATTERNS + INVERSE_PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            return make_question(kind, match)
    raise UnsupportedCondition(
        "the complete scalar formula question must be recognized"
    )
