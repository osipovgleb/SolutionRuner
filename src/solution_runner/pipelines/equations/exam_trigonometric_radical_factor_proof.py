"""A vanishing whole radical factor means R=a², while the first factor keeps R≥0."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_radical_product import admissible_factor, root_function


def proof(a, html, zero, first):
    from .exam_trigonometric_proof import families, formula, polynomial
    from .exam_trigonometric_radical_product_proof import positive_case

    data = a.radical_product
    factor, divisor = admissible_factor(a)
    root = root_function(data)
    normalized = sp.cancel(root / data.root_offset**2)
    html += "<p>Разложим первый множитель и вынесем ненулевую постоянную из скобки с корнем:</p>"
    html += line(
        r"\left("
        + formula(sp.factor(data.factor))
        + r"\right)\left(1-\sqrt{"
        + formula(normalized)
        + r"}\right)=0"
    )
    if divisor != 1:
        html += "<p>Выделенный множитель ненулевой по исходной области определения. Поэтому на него можно разделить, не теряя допустимых корней:</p>"
        html += line(formula(divisor) + r"\ne0")
    html += "<p>На исходной области определения получаем равносильное произведение:</p>"
    html += line(
        r"\left("
        + formula(factor)
        + r"\right)\left(1-\sqrt{"
        + formula(normalized)
        + r"}\right)=0"
    )
    html += "<p>Рассмотрим оба случая. Первый множитель равен нулю при сохранении нестрогого условия на подкоренное выражение:</p>"
    html += line(formula(factor) + "=0")
    html += line(formula(root) + r"\ge0")
    if not first:
        html += "<p>Первый множитель — ненулевая постоянная, поэтому этот случай корней не даёт.</p>"
    html += positive_case(a, first, None)
    html += "<p>Во втором случае равна нулю вся скобка с корнем. Корень равен положительному числу 1, поэтому возведение в квадрат равносильно:</p>"
    html += line(r"1-\sqrt{" + formula(normalized) + r"}=0")
    html += line(r"\sqrt{" + formula(normalized) + r"}=1")
    html += line(formula(normalized) + "=1")
    for branch in zero:
        html += polynomial(branch, allowed_residues=branch.residues)
    html += "<p>Объединим допустимые серии обоих случаев. Нулевой радикал сам по себе не обращает вторую скобку в нуль:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return (
        "<p>Решим произведение, сохраняя область определения обоих множителей:</p>",
        html,
    )
