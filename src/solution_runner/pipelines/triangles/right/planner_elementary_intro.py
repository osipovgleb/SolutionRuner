"""Build the introductory reasoning for elementary triangle rules."""

from __future__ import annotations

from .planner_conditions import _integer_match, _math_aware_html, _plain_html


def _area_leg_difference_intro(condition_html: str) -> str:
    """Build the rule-specific introduction from its condition."""
    difference = _integer_match(
        r"катетов\s+на\s+(\d+)\s+больше",
        _plain_html(condition_html),
        "condition must give an integer leg difference",
    )
    return (
        '<p>Пусть <span data-inline-latex="x"></span> — меньший катет, '
        'тогда второй <span data-inline-latex="x+' + str(difference) + '"></span>:</p>'
    )


def _altitude_line_angle_intro(condition_html: str) -> str:
    """Build the rule-specific introduction from its condition."""
    visible = _math_aware_html(condition_html).lower()
    if "медиан" in visible and "биссектрис" not in visible:
        return (
            "<p>Медиана к гипотенузе равна её половине. Поэтому "
            '<span data-inline-latex="CM=BM"></span>, и треугольник '
            '<span data-inline-latex="CMB"></span> равнобедренный.</p>'
            "<p>Его углы при основании равны: "
            '<span data-inline-latex="\\angle BCM=\\angle CBM=\\angle B"></span>.</p>'
            '<p>Так как <span data-inline-latex="CH\\perp AB"></span>, '
            'треугольник <span data-inline-latex="BCH"></span> прямоугольный. '
            'Поэтому <span data-inline-latex="\\angle BCH=90^{\\circ}-\\angle B"></span>. '
            'Но <span data-inline-latex="\\angle A=90^{\\circ}-\\angle B"></span>, '
            'следовательно, <span data-inline-latex="\\angle BCH=\\angle A"></span>.</p>'
            "<p>Угол между высотой и медианой равен разности "
            '<span data-inline-latex="\\angle BCM"></span> и '
            '<span data-inline-latex="\\angle BCH"></span>:</p>'
        )
    return (
        "<p>Биссектриса прямого угла образует угол "
        '<span data-inline-latex="45^{\\circ}"></span>. Высота, проведённая '
        "из вершины прямого угла, делит исходный треугольник на два "
        "подобных ему прямоугольных треугольника.</p>"
        "<p>Поэтому угол между высотой и биссектрисой равен разности "
        "соответствующего острого угла и половины прямого угла:</p>"
    )


_STATIC_INTROS = {
    "right-triangle-leg-hypotenuse-area": (
        "<p>По теореме Пифагора найдём второй катет:</p>"
    ),
    "right-triangle-acute-angle-difference": (
        "<p>Сумма острых углов прямоугольного треугольника равна 90°:</p>"
    ),
    "right-triangle-acute-angle-ratio": (
        "<p>Пусть углы пропорциональны данным числам:</p>"
    ),
    "right-triangle-median-angle": (
        '<p>Так как <span data-inline-latex="CD"></span> — медиана, точка '
        '<span data-inline-latex="D"></span> — середина гипотенузы '
        '<span data-inline-latex="AB"></span>, поэтому '
        '<span data-inline-latex="AD=BD"></span>.</p>'
        "<p>Медиана, проведённая из вершины прямого угла к гипотенузе, "
        "равна половине гипотенузы:</p>"
    ),
}
_STATIC_INTROS.update(
    {
        "right-triangle-bisector-intersection-angle": (
            "<p>Пусть данный острый угол равен "
            '<span data-inline-latex="\\alpha"></span>. Тогда второй острый угол '
            'равен <span data-inline-latex="90^{\\circ}-\\alpha"></span>.</p>'
            "<p>Обозначим точку пересечения биссектрис через "
            '<span data-inline-latex="O"></span>. Биссектриса данного острого '
            "угла делит его пополам, поэтому "
            '<span data-inline-latex="\\angle OAC=\\frac{\\alpha}{2}"></span>.</p>'
            "<p>Биссектриса прямого угла также делит его пополам, следовательно, "
            '<span data-inline-latex="\\angle ACO=45^{\\circ}"></span>. Тогда по '
            'сумме углов треугольника <span data-inline-latex="AOC"></span> '
            '<span data-inline-latex="\\angle AOC=135^{\\circ}-\\frac{\\alpha}{2}"></span>.</p>'
            "<p>Полученный угол тупой; смежный с ним острый угол является "
            "искомым и равен "
            '<span data-inline-latex="45^{\\circ}+\\frac{\\alpha}{2}"></span>:</p>'
        ),
        "right-triangle-altitude-bisector-angle": (
            '<p>Пусть <span data-inline-latex="\\angle B=\\alpha"></span>. '
            'Так как <span data-inline-latex="CH\\perp AB"></span>, треугольник '
            '<span data-inline-latex="BCH"></span> прямоугольный, поэтому '
            '<span data-inline-latex="\\angle BCH=90^{\\circ}-\\alpha"></span>.</p>'
            '<p>Отрезок <span data-inline-latex="CD"></span> — биссектриса '
            "прямого угла, следовательно, "
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span>.</p>'
            "<p>Искомый угол равен модулю разности полученных углов: "
            '<span data-inline-latex="\\varphi=|\\angle BCH-\\angle ACD|"></span>. '
            "Подставим данное значение:</p>"
        ),
        "right-triangle-altitude-bisector-inverse": (
            '<p>Пусть <span data-inline-latex="\\varphi"></span> — данный угол '
            "между высотой и биссектрисой. Так как "
            '<span data-inline-latex="CD"></span> — биссектриса прямого угла, '
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span>.</p>'
            '<p>Поэтому <span data-inline-latex="\\angle ACH=45^{\\circ}+\\varphi"></span>. '
            'Треугольник <span data-inline-latex="ACH"></span> прямоугольный при '
            '<span data-inline-latex="H"></span>, поэтому сумма его острых углов '
            'равна <span data-inline-latex="90^{\\circ}"></span>.</p>'
            "<p>Следовательно, "
            '<span data-inline-latex="\\angle A=90^{\\circ}-\\angle ACH"></span>, '
            "откуда найдём меньший острый угол:</p>"
        ),
        "right-triangle-altitude-median-inverse": (
            '<p>Пусть <span data-inline-latex="\\varphi"></span> — угол между '
            'высотой <span data-inline-latex="CH"></span> и медианой '
            '<span data-inline-latex="CM"></span>. В прямоугольном треугольнике '
            '<span data-inline-latex="CHM"></span> получаем '
            '<span data-inline-latex="\\angle CMB=90^{\\circ}-\\varphi"></span>.</p>'
            "<p>Медиана к гипотенузе равна её половине, поэтому "
            '<span data-inline-latex="CM=MB"></span> и треугольник '
            '<span data-inline-latex="CMB"></span> равнобедренный.</p>'
            "<p>Его углы при основании равны, а их сумма равна разности между "
            '<span data-inline-latex="180^{\\circ}"></span> и углом при вершине: '
            '<span data-inline-latex="\\angle CBM=\\angle BCM=\\frac{180^{\\circ}-\\angle CMB}{2}"></span>.</p>'
            '<p>Угол <span data-inline-latex="\\angle CBM"></span> совпадает с '
            "большим острым углом исходного треугольника, поэтому:</p>"
        ),
        "right-triangle-bisector-median-angle": (
            "<p>Медиана к гипотенузе равна её половине, поэтому "
            '<span data-inline-latex="CM=BM"></span>. Значит, треугольник '
            '<span data-inline-latex="CMB"></span> равнобедренный и '
            '<span data-inline-latex="\\angle BCM=\\angle B"></span>.</p>'
            '<p>Биссектриса <span data-inline-latex="CD"></span> делит прямой '
            "угол пополам, поэтому "
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span> и '
            '<span data-inline-latex="\\angle DCB=45^{\\circ}"></span>.</p>'
            "<p>Искомый угол равен модулю разности углов "
            '<span data-inline-latex="\\angle BCM"></span> и '
            '<span data-inline-latex="\\angle DCB"></span>:</p>'
        ),
        "right-triangle-bisector-median-inverse": (
            '<p>Так как <span data-inline-latex="CM"></span> — медиана к '
            'гипотенузе, <span data-inline-latex="AM=CM"></span>. Поэтому '
            'треугольник <span data-inline-latex="AMC"></span> равнобедренный и '
            '<span data-inline-latex="\\angle ACM=\\angle A"></span>.</p>'
            '<p>Биссектриса <span data-inline-latex="CD"></span> делит прямой '
            "угол пополам, поэтому "
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span>.</p>'
            "<p>Поскольку данный угол между биссектрисой и медианой равен "
            '<span data-inline-latex="\\varphi=45^{\\circ}-\\angle A"></span>, '
            "меньший острый угол получаем вычитанием:</p>"
        ),
        "right-triangle-altitude-length": (
            '<p>Так как <span data-inline-latex="CH"></span> — высота, '
            '<span data-inline-latex="CH\\perp AB"></span>, и треугольник '
            '<span data-inline-latex="ACH"></span> прямоугольный.</p>'
            '<p>В треугольнике <span data-inline-latex="ABC"></span> по '
            "определению косинуса "
            '<span data-inline-latex="\\cos A=\\frac{AC}{AB}"></span>, откуда '
            '<span data-inline-latex="AC=AB\\cos A"></span>.</p>'
            '<p>В треугольнике <span data-inline-latex="ACH"></span> по '
            "определению синуса "
            '<span data-inline-latex="\\sin A=\\frac{CH}{AC}"></span>, откуда '
            '<span data-inline-latex="CH=AC\\sin A"></span>.</p>'
            "<p>Подставим первое равенство во второе и вычислим высоту:</p>"
        ),
        "right-triangle-hypotenuse-projection-ah": (
            '<p>Так как <span data-inline-latex="CH\\perp AB"></span>, '
            'треугольник <span data-inline-latex="ACH"></span> прямоугольный, '
            'причём <span data-inline-latex="\\angle CAH=\\angle A"></span>.</p>'
            '<p>В треугольнике <span data-inline-latex="ABC"></span> '
            '<span data-inline-latex="\\cos A=\\frac{AC}{AB}"></span>, поэтому '
            '<span data-inline-latex="AC=AB\\cos A"></span>.</p>'
            '<p>В треугольнике <span data-inline-latex="ACH"></span> '
            '<span data-inline-latex="\\cos A=\\frac{AH}{AC}"></span>, поэтому '
            '<span data-inline-latex="AH=AC\\cos A"></span>.</p>'
            "<p>Последовательно подставим найденные выражения:</p>"
        ),
        "right-triangle-hypotenuse-projection-bh": (
            '<p>В треугольнике <span data-inline-latex="ABC"></span> по '
            "определению синуса "
            '<span data-inline-latex="\\sin A=\\frac{BC}{AB}"></span>, откуда '
            '<span data-inline-latex="BC=AB\\sin A"></span>.</p>'
            '<p>Так как <span data-inline-latex="CH\\perp AB"></span>, '
            'треугольник <span data-inline-latex="BCH"></span> прямоугольный. '
            'Его угол <span data-inline-latex="\\angle BCH=90^{\\circ}-\\angle B"></span>. '
            'Так как <span data-inline-latex="\\angle A=90^{\\circ}-\\angle B"></span>, '
            '<span data-inline-latex="\\angle BCH=\\angle A"></span>.</p>'
            "<p>По определению синуса в треугольнике "
            '<span data-inline-latex="BCH"></span> '
            '<span data-inline-latex="\\sin A=\\frac{BH}{BC}"></span>, поэтому '
            '<span data-inline-latex="BH=BC\\sin A"></span>.</p>'
            "<p>Подставим первое равенство во второе:</p>"
        ),
    }
)

_DYNAMIC_INTROS = {
    "right-triangle-area-leg-difference": _area_leg_difference_intro,
    "right-triangle-altitude-line-angle": _altitude_line_angle_intro,
}


def _elementary_intro(content_rule_key: str, condition_html: str) -> str:
    """Return the concise prose that introduces one elementary derivation."""
    builder = _DYNAMIC_INTROS.get(content_rule_key)
    return builder(condition_html) if builder else _STATIC_INTROS[content_rule_key]
