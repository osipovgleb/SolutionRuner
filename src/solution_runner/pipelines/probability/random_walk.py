"""Absorption of a nearest-neighbour walk, with a finite-barrier root proof."""

import re
from fractions import Fraction
from math import comb

from solution_runner.pipelines.core.numbers import parse_rational

from . import solution_diagrams as diagrams
from .bernoulli import RATIONAL, checked, fmt, result
from .common import UnsupportedCondition, line, normalize

_PATTERN = re.compile(
    rf"Первый член последовательности целых чисел равен 0\. Каждый следующий член последовательности с вероятностью p\s*=\s*(?P<p>{RATIONAL}) на единицу больше предыдущего и [сc] вероятностью 1\s*[−–-]\s*p на единицу меньше предыдущего\. Какова вероятность того, что какой-то член этой последовательности окажется равен [−–-]1\?"
)
_FIGURES = (
    ("688ca8b4-f6af-4af1-acd6-1204aa6e9cbd", "Поглощение в нуле при старте в единице"),
    (
        "15c9bd1a-b0f4-48c6-aa30-abea0d780952",
        "Вероятность поглощения в зависимости от p",
    ),
    ("5c507bfe-427e-4149-9a5a-4a4f81c6242e", "Иллюстрация блуждания на краю утёса"),
    (
        "a10afb06-743b-457e-b45a-f4d88447cfd3",
        "Первые пять шагов отдельного примера с p=2/3",
    ),
)


def absorption_probability(p, distance=1):
    checked(p)
    if not isinstance(distance, int) or not 0 <= distance <= 100:
        raise UnsupportedCondition(
            "the starting distance must be an integer from 0 to 100"
        )
    if distance == 0 or p <= Fraction(1, 2):
        return Fraction(1)
    return ((1 - p) / p) ** distance


def finite_absorption(p, start, upper):
    checked(p)
    if (
        not isinstance(start, int)
        or not isinstance(upper, int)
        or not 0 <= start <= upper <= 200
        or upper == 0
    ):
        raise UnsupportedCondition("invalid finite absorption interval")
    if start == 0:
        return Fraction(1)
    if start == upper:
        return Fraction(0)
    if p == 0:
        return Fraction(1)
    if p == 1:
        return Fraction(0)
    if p == Fraction(1, 2):
        return Fraction(upper - start, upper)
    ratio = (1 - p) / p
    return (ratio**start - ratio**upper) / (1 - ratio**upper)


def first_hit_mass(p, j):
    checked(p)
    if not isinstance(j, int) or not 0 <= j <= 100:
        raise UnsupportedCondition("the Catalan index must be an integer from 0 to 100")
    catalan = comb(2 * j, j) // (j + 1)
    return catalan * p**j * (1 - p) ** (j + 1)


def _input(context):
    content, condition, answer, solution, text = diagrams.read(context)
    match = _PATTERN.fullmatch(normalize(text))
    if match is None:
        raise UnsupportedCondition("unsupported complete random-walk condition")
    p = checked(parse_rational(match["p"]))
    allowed = {source for source, _ in _FIGURES}
    if any(a.get("asset_id") not in allowed for a in content.get("assets", [])):
        raise UnsupportedCondition(
            "only the audited universal walk illustrations are supported"
        )
    return content, condition, answer, solution, p


def required_assets(context):
    _input(context)
    return tuple(
        {"source_asset_id": source, "section_id": "solution:1", "alt_text": alt}
        for source, alt in _FIGURES
    )


def build_context_repair_plan(context):
    content, condition, answer_section, solution, p = _input(context)
    q = 1 - p
    value = absorption_probability(p)
    images = []
    keys = []
    for source, alt in _FIGURES:
        image, key, _changes = diagrams.image(
            content, "walk_illustration", alt, source_id=source
        )
        images.append(image)
        keys.append(key)
    html = "<p>Для наглядности представим частицу на числовой прямой. Обозначим через x вероятность попасть из 0 в −1. После первого шага частица либо сразу достигнет −1, либо попадёт в 1. Во втором случае нужно последовательно пройти два отрезка на единицу влево. Независимость будущих шагов и одинаковые правила движения дают вероятность x²:</p>"
    html += line(rf"x=(1-p)+px^2={fmt(q)}+{fmt(p)}x^2")
    html += line(rf"{fmt(p)}x^2-x+{fmt(q)}=0")
    if p:
        html += line(rf"x_1=1,\quad x_2=\frac{{1-p}}{{p}}={fmt(q / p)}")
    else:
        html += "<p>При p=0 частица сразу идёт влево, поэтому x=1.</p>"
    html += (
        "<p>Искомая вероятность — наименьший неотрицательный корень. Обоснование выбора приведено ниже через конечный барьер.</p>"
        + line(rf"x={fmt(value)}")
    )
    html += (
        "<p>Задача о случайном блуждании. Сдвинем начало координат: теперь стартуем в 1, а поглощение происходит в 0. Шаг вправо имеет вероятность p, влево — 1−p.</p>"
        + images[0]
    )
    html += "<p>Пусть P₁ и P₂ — вероятности поглощения при старте в 1 и 2. После первого шага P₁=1−p+pP₂. Чтобы из 2 достичь 0, надо сначала достичь 1, а затем 0. В силу одинаковых правил и независимости последующих шагов P₂=P₁²:</p>"
    html += line(r"P_1=1-p+pP_1^2")
    html += "<p>Проверим выбор корня без предположения о непрерывности. Временно добавим поглощающую границу L справа. Вероятность hᵢ дойти до 0 раньше L удовлетворяет:</p>"
    html += line(r"h_i=(1-p)h_{i-1}+ph_{i+1},\quad h_0=1,\quad h_L=0")
    html += line(
        r"h_i=\frac{r^i-r^L}{1-r^L},\quad r=\frac{1-p}{p}\quad(0<p<1,\ p\ne\tfrac12)"
    )
    html += line(r"h_i=1-\frac{i}{L}\quad(p=\tfrac12)")
    html += "<p>При L→∞ события «достичь нуля раньше L» возрастают до события «когда-либо достичь нуля»: всякий путь с конечным моментом поглощения имеет конечный максимум. Переходя к пределу, получаем:</p>"
    html += line(
        r"P_i=\begin{cases}1,&0\le p\le\tfrac12,\\((1-p)/p)^i,&\tfrac12<p\le1.\end{cases}\quad(i\ge1)"
    )
    html += (
        "<p>Крайние случаи согласуются с движением: при p=0 всегда идём влево, при p=1 — вправо. При p=1/2 вероятность поглощения равна 1. График общей зависимости P₁ от p:</p>"
        + images[1]
    )
    html += "<p>Обобщения. При начальном расстоянии m от поглощающей точки вероятность равна 1 для p≤1/2 и ((1−p)/p)ᵐ для p>1/2. В симметричном блуждании из 0 частица после первого шага оказывается в 1 или −1 и с вероятностью 1 возвращается в 0.</p>"
    html += "<p>Задача о разорении игрока. Расстояние до нуля можно понимать как капитал игрока, который в каждом туре выигрывает или теряет единицу. При начальном капитале 1 вероятность разорения меньше 1/2 тогда и только тогда, когда p>2/3. При честной игре p=1/2 разорение за неограниченное время происходит с вероятностью 1. Это не противоречит среднему капиталу 1 после любого фиксированного конечного числа партий: конечный срок и неограниченное время — разные условия.</p>"
    html += (
        "<p>Задача о пьянице на краю утёса. Сохраним отдельный иллюстративный пример родителя: вероятность шага от края равна 2/3, к краю — 1/3. Это пример общей модели, его p не заменяет вероятность из условия задачи.</p>"
        + images[2]
    )
    html += line(
        r"P(\text{падение})=\frac{1/3}{2/3}=\frac12,\qquad P(\text{избежать падения})=\frac12"
    )
    html += (
        "<p>При равновероятных шагах к краю и от края падение за неограниченное время имеет вероятность 1 при любом конечном начальном расстоянии. В примере с p=2/3 первые шаги изображены так:</p>"
        + images[3]
    )
    html += "<p>Упасть впервые можно лишь после нечётного числа шагов. Для одного, трёх и пяти шагов:</p>"
    for j in range(3):
        html += line(rf"p_{{{2 * j + 1}}}={fmt(first_hit_mass(Fraction(2, 3), j))}")
    html += line(r"P(T\le3)=\frac13+\frac2{27}=\frac{11}{27}")
    html += line(r"P(T\le5)=\frac{11}{27}+\frac8{243}=\frac{107}{243}")
    html += "<p>Общий подсчёт приводит к путям Дика и числам Каталана Cⱼ. До последнего шага путь не касается поглощающей границы:</p>"
    html += line(r"C_j=\frac1{j+1}\binom{2j}{j},\quad P(T=2j+1)=C_jp^j(1-p)^{j+1}")
    html += line(r"P_1=\sum_{j=0}^{\infty}C_jp^j(1-p)^{j+1}")
    html += '<p>В отдельном примере этот ряд равен 1/2. Подробнее о подсчёте путей — в статье <a href="https://habr.com/ru/articles/690242/" rel="noreferrer noopener" target="_blank">«Задача про пьяницу»</a>.</p>'
    html += "<p>Возвращаясь к вероятности из условия, получаем:</p>" + line(
        rf"P={fmt(value)}"
    )
    answer, html = result(value, html)
    return diagrams.repair(
        condition, answer_section, solution, answer, html, tuple(keys)
    )
