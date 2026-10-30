"""Complete applied polynomial statements and their units, without ID dispatch."""

import re
from dataclasses import dataclass, field

import sympy as sp

from ..calculus.common import T, X, polynomial
from ..probability.common import UnsupportedCondition

VALUE = r"-?(?:\\frac\{\d+\}\{\d+\}|\d+(?:\{,\}|[,.])\d+|\d+)"
_TANK = r"В боковой стенке высокого цилиндрического бака у самого дна закреплен кран\. После его открытия вода начинает вытекать из бака, при этом высота столба воды в нем, выраженная в метрах, меняется по закону H\(t\)=(?P<formula>.+?), где "
_PATTERNS = (
    (
        "bridge",
        re.compile(
            rf"На рисунке изображена схема вантового моста\. Вертикальные пилоны связаны провисающей цепью\. Тросы, которые свисают с цепи и поддерживают полотно моста, называются вантами\. Введем систему координат: ось Oy направим вертикально вдоль одного из пилонов, а ось Ox направим вдоль полотна моста, как показано на рисунке\. В этой системе координат линия, по которой провисает цепь моста, имеет уравнение y=(?P<formula>.+?), где x и y измеряются в метрах\. Найдите длину ванты, расположенной в (?P<distance>{VALUE}) метрах от пилона\. Ответ дайте в метрах\."
        ),
    ),
    (
        "well",
        re.compile(
            rf"После дождя уровень воды в колодце может повыситься\. Мальчик измеряет время t падения небольших камешков в колодец и рассчитывает расстояние до воды по формуле h=(?P<formula>.+?), где h — расстояние в метрах, t — время падения в секундах\. До дождя время падения камешков составляло (?P<before>{VALUE}) с\. На сколько должен подняться уровень воды после дождя, чтобы измеряемое время изменилось на (?P<change>{VALUE}) с\? Ответ выразите в метрах\."
        ),
    ),
    (
        "duration",
        re.compile(
            rf"(?:Высота над землей подброшенного вверх мяча меняется по закону|Камень брошен вертикально вверх\. Пока камень не упал, высота, на которой он находится, описывается формулой) h\(t\)=(?P<formula>.+?), где h — высота в метрах, t — время в секундах, прошедшее с момента броска\. Сколько секунд (?:мяч будет находиться|камень находился) на высоте не менее (?P<target>{VALUE}|трех) метров\?"
        ),
    ),
    (
        "thermal_duration",
        re.compile(
            rf"Электрический прибор после включения в сеть нагревается и через некоторое время автоматически выключается и начинает остывать\. Температура прибора в градусах Цельсия вычисляется по формуле: T=(?P<formula>.+?), где t — время в минутах, прошедшее после включения прибора в сеть, T_0=(?P<initial>{VALUE}) °C — начальная температура прибора\. На протяжении какого времени в минутах температура прибора будет не менее (?P<target>{VALUE}) °C\?"
        ),
    ),
    (
        "tank_fraction",
        re.compile(
            _TANK
            + rf"t — время в секундах, прошедшее с момента открытия крана, H_0=(?P<initial>{VALUE})(?: м)? — начальная высота столба воды, k=(?P<ratio>{VALUE}) — отношение площадей поперечных сечений крана и бака, а g — ускорение свободного падения\(считайте g=(?P<gravity>{VALUE}) м/с\^\{{2\}}\)\. Через сколько секунд после открытия крана в баке останется четверть первоначального объема воды\?"
        ),
    ),
    (
        "tank_empty",
        re.compile(
            _TANK
            + rf"H_0=(?P<initial>{VALUE})(?: м)? — начальный уровень воды, a=(?P<a>{VALUE}) м/мин\^\{{2\}},? и b=(?P<b>{VALUE}) м/мин — постоянные, t — время в минутах, прошедшее с момента открытия крана\. В течение какого времени вода будет вытекать из бака\? Ответ приведите в минутах\."
        ),
    ),
    (
        "barrier",
        re.compile(
            rf"Камнеметательная машина выстреливает камни под некоторым острым углом к горизонту\. Траектория полета камня описывается формулой y=(?P<formula>.+?), где a=(?P<a>{VALUE}) м\^\{{\(-1\)\}}, b=(?P<b>{VALUE}) — постоянные параметры, x\(м\)— смещение камня по горизонтали, y\(м\)— высота камня над землей\. На каком наибольшем расстоянии\(в метрах\)от крепостной стены высотой (?P<wall>{VALUE}) м нужно расположить машину, чтобы камни пролетали над стеной на высоте не менее (?P<clearance>{VALUE}) метра\?"
        ),
    ),
    (
        "heater",
        re.compile(
            rf"Для нагревательного элемента некоторого прибора экспериментально была получена зависимость температуры\(в кельвинах\)от времени работы: T\(t\)=(?P<formula>.+?), где t — время в минутах, T_0=(?P<initial>{VALUE}) К, a=(?P<a>{VALUE}) К/мин\^\{{2\}}, b=(?P<b>{VALUE}) К/мин\. Известно, что при температуре нагревателя свыше (?P<target>{VALUE}) К прибор может испортиться, поэтому его нужно отключить\. Определите, через какое наибольшее время после начала работы нужно отключить прибор\. Ответ выразите в минутах\."
        ),
    ),
    (
        "winding",
        re.compile(
            rf"Для сматывания кабеля на заводе используют лебедку, которая равноускоренно наматывает кабель на катушку\. Угол, на который поворачивается катушка, изменяется со временем по закону \\varphi=(?P<formula>.+?), где t — время в минутах, \\omega=(?P<omega>{VALUE})°(?: мин|/мин) — начальная угловая скорость вращения катушки, а \\beta=(?P<beta>{VALUE})°(?: мин|/мин)\^\{{2\}} — угловое ускорение, с которым наматывается кабель\. Рабочий должен проверить ход его намотки не позже того момента, когда угол намотки \\varphi достигнет (?P<target>{VALUE})°\. Определите время после начала работы лебедки, не позже которого рабочий должен проверить ее работу\. Ответ выразите в минутах\."
        ),
    ),
    (
        "coverage",
        re.compile(
            rf"Мотоциклист, движущийся по городу со скоростью v_0=(?P<speed>{VALUE}) км/ч, выезжает из него и сразу после выезда начинает разгоняться с постоянным ускорением a=(?P<a>{VALUE}) км/ч\^\{{2\}}\. Расстояние от мотоциклиста до города, измеряемое в километрах, определяется выражением S=(?P<formula>.+?), где t — время в часах\. Определите наибольшее время, в течение которого мотоциклист будет находиться в зоне функционирования сотовой связи, если оператор гарантирует покрытие на расстоянии не далее чем в (?P<target>{VALUE}) км от города\. Ответ (?:дайте|выразите) в минутах\."
        ),
    ),
    (
        "braking",
        re.compile(
            rf"Автомобиль, движущийся в начальный момент времени со скоростью v_0=(?P<speed>{VALUE}) м/с, начал торможение с постоянным ускорением a=(?P<a>{VALUE}) м/с\^\{{2\}}\. За t(?: —)? секунд после начала торможения он прошел путь S=(?P<formula>.+?)\(м\)\. Определите время, прошедшее от момента начала торможения, если известно, что за это время автомобиль проехал (?P<target>{VALUE}) метров\. Ответ выразите в секундах\."
        ),
    ),
)


@dataclass(frozen=True)
class Question:
    kind: str
    expression: sp.Expr
    target: sp.Rational
    variable: sp.Symbol = T
    quantity: str = "h"
    unit: str = "с"
    scale: int = 1
    values: dict = field(default_factory=dict)


def scalar(text):
    if text == "трех":
        return sp.Integer(3)
    value = polynomial(text, T)
    if value.free_symbols or value.is_Rational is not True:
        raise UnsupportedCondition("an exact rational physical parameter is required")
    return value


def bound_formula(formula, variable, values):
    renamed = (
        formula.replace("H_0", "q")
        .replace("T_0", "q")
        .replace("v_0", "v")
        .replace(r"\omega", "w")
        .replace(r"\beta", "b")
    )
    expression = polynomial(renamed, variable, tuple(values))
    return sp.expand(
        expression.subs({sp.Symbol(k, real=True): v for k, v in values.items()})
    )


def make_question(kind, m):
    values = {
        k: scalar(v)
        for k, v in m.groupdict().items()
        if k != "formula" and v is not None
    }
    formula = m["formula"]
    variable = X if kind in ["barrier", "bridge"] else T
    if kind == "tank_fraction":
        expected = r"H_0-\sqrt{2gH_0}kt+\frac{g}{2}k^{2}t^{2}"
        if formula.replace(" ", "") != expected:
            raise UnsupportedCondition(
                "the complete tank-drain formula must match its physical law"
            )
        h, g, k = values["initial"], values["gravity"], values["ratio"]
        if min(h, g, k) <= 0 or k >= 1:
            raise UnsupportedCondition(
                "positive height, gravity and aperture ratio below one are required"
            )
        expression = sp.expand(h - sp.sqrt(2 * g * h) * k * T + g * k * k * T * T / 2)
    else:
        names = {
            "initial": "q",
            "a": "a",
            "b": "b",
            "speed": "v",
            "omega": "w",
            "beta": "b",
        }
        bindings = {names[k]: v for k, v in values.items() if k in names}
        expression = bound_formula(formula, variable, bindings)
    target = values.get("target", sp.Integer(0))
    if kind == "tank_fraction":
        target = values["initial"] / 4
    if kind == "barrier":
        target = values["wall"] + values["clearance"]
    quantity = {
        "thermal_duration": "T",
        "tank_empty": "H",
        "tank_fraction": "H",
        "heater": "T",
        "winding": r"\varphi",
        "coverage": "S",
        "braking": "S",
        "barrier": "y",
        "bridge": "y",
    }.get(kind, "h")
    unit = (
        "м"
        if kind in ["well", "barrier", "bridge"]
        else "мин"
        if kind in ["thermal_duration", "tank_empty", "heater", "winding", "coverage"]
        else "с"
    )
    return Question(
        kind,
        expression,
        target,
        variable,
        quantity,
        unit,
        60 if kind == "coverage" else 1,
        values,
    )


def parse(text):
    for kind, pattern in _PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            return make_question(kind, match)
    raise UnsupportedCondition(
        "the complete applied polynomial statement must be recognized"
    )
