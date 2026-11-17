"""Render independent three-point and asymptote proofs for a hyperbola."""

from fractions import Fraction

from .hyperbola_format import formula, latex, row


def signed(v):
    return ("+" if v >= 0 else "-") + latex(abs(v))


def coefficient(v, name):
    if not name:
        return latex(v)
    return name if v == 1 else "-" + name if v == -1 else latex(v) + name if v else ""


def expression(terms):
    out = ""
    for v, name in terms:
        if not v:
            continue
        text = coefficient(v, name)
        out += ("+" if out and v > 0 else "") + text
    return out or "0"


def subtract_number(v):
    return "-" + (latex(v) if v >= 0 else "(" + latex(v) + ")")


def system(*eq):
    return r"\begin{cases}" + r"\\".join(eq) + r"\end{cases}"


def product(v, w):
    return latex(v) + r"\cdot " + (latex(w) if w >= 0 else "(" + latex(w) + ")")


def _system_rows(pts, linear):
    return (
        ""
        + row(
            system(
                *(
                    latex(py)
                    + rf"=\frac{{{expression(((px, 'k'), (Fraction(1), 'a')))}}}{{{latex(px)}+b}}"
                    for px, py in pts
                )
            )
        )
        + "<p>Убираем знаменатели:</p>"
        + row(
            r"\iff "
            + system(
                *(
                    rf"{latex(py)}({latex(px)}+b)={expression(((px, 'k'), (Fraction(1), 'a')))}"
                    for px, py in pts
                )
            )
        )
        + "<p>Раскрываем скобки:</p>"
        + row(
            r"\iff "
            + system(
                *(
                    expression(((px * py, ""), (py, "b")))
                    + "="
                    + expression(((px, "k"), (Fraction(1), "a")))
                    for px, py in pts
                )
            )
        )
        + "<p>Переносим слагаемые с неизвестными влево, числа — вправо:</p>"
        + row(
            r"\iff "
            + system(
                *(lhs + "=" + latex(px * py) for lhs, (px, py) in zip(linear, pts))
            )
        )
    )


def _eliminate_a(pts):
    x, y = pts[0]
    reduced = []
    linear = [expression(((px, "k"), (Fraction(1), "a"), (-py, "b"))) for px, py in pts]
    from math import gcd

    elimination = ""
    for index, (px, py) in enumerate(pts[1:], 2):
        ck, cb, rhs = x - px, py - y, x * y - px * py
        divisor = gcd(gcd(abs(ck.numerator), abs(cb.numerator)), abs(rhs.numerator))
        if ck < 0:
            divisor = -divisor
        reduced.append((ck / divisor, cb / divisor, rhs / divisor))
        elimination += (
            f"<p>Вычтем {'второе' if index == 2 else 'третье'} уравнение из первого: "
            f"{formula('a')} сократится.</p>"
            + row(
                rf"({linear[0]})-({linear[index - 1]})={latex(x * y)}"
                + subtract_number(px * py)
            )
            + row(
                expression(((ck, "k"), (cb, "b")))
                + "="
                + latex(rhs)
                + r"\iff "
                + expression(((ck / divisor, "k"), (cb / divisor, "b")))
                + "="
                + latex(rhs / divisor)
            )
        )
    return linear, reduced, elimination


def first_proof(facts, sought, result, image):
    k, a, b = (facts[key] for key in ("k", "a", "b"))
    x, y = facts["point"]
    x2, y2 = facts["second"]
    x3, y3 = facts["third"]
    pts = (facts["point"], facts["second"], facts["third"])
    linear, reduced, elimination = _eliminate_a(pts)
    u1, v1, t1 = reduced[0]
    u2, v2, t2 = reduced[1]
    equations = [
        expression(((u, "k"), (v, "b"))) + "=" + latex(t) for u, v, t in reduced
    ]
    db, rb = v1 * u2 - v2 * u1, t1 * u2 - t2 * u1

    if u1 == u2:
        db, rb = v1 - v2, t1 - t2
        cancel = (
            "<p>Вычтем второе из полученных уравнений: "
            + formula("k")
            + " сократится.</p>"
        )
        cancel_row = (
            rf"({expression(((u1, 'k'), (v1, 'b')))})-({expression(((u2, 'k'), (v2, 'b')))})={latex(t1)}"
            + subtract_number(t2)
        )
    else:
        cancel = (
            f"<p>Чтобы исключить {formula('k')}, умножим первое уравнение на {formula(latex(u2))}, "
            f"второе — на {formula(latex(u1))} и вычтем второе из первого.</p>"
        )
        cancel_row = rf"{latex(u2)}({expression(((u1, 'k'), (v1, 'b')))})-({latex(u1)})({expression(((u2, 'k'), (v2, 'b')))})={product(u2, t1)}-({product(u1, t2)})"
    k_sub = expression(((u2, "k"), (v2 * b, ""))) + "=" + latex(t2)
    a_sub = (
        expression(((x * k, ""), (Fraction(1), "a"), (-y * b, ""))) + "=" + latex(x * y)
    )
    first = (
        image + f"<p>Подставим три точки {formula(rf'A({latex(x)};{latex(y)})')}, "
        f"{formula(rf'B({latex(x2)};{latex(y2)})')} и {formula(rf'C({latex(x3)};{latex(y3)})')} "
        "в формулу функции.</p>"
        + _system_rows(pts, linear)
        + elimination
        + "<p>Получили систему с двумя неизвестными:</p>"
        + row(system(*equations))
        + cancel
        + row(cancel_row)
        + row(coefficient(db, "b") + "=" + latex(rb) + r"\iff b=" + latex(b))
        + f"<p>Подставим {formula('b=' + latex(b))} во второе уравнение:</p>"
        + row(
            k_sub
            + r"\iff "
            + coefficient(u2, "k")
            + "="
            + latex(t2 - v2 * b)
            + (r"\iff k=" + latex(k) if u2 != 1 else "")
        )
        + f"<p>Подставим {formula('k=' + latex(k))} и {formula('b=' + latex(b))} в первое уравнение исходной системы:</p>"
        + row(
            a_sub
            + r"\iff a="
            + expression(((x * y, ""), (-x * k, ""), (y * b, "")))
            + "="
            + latex(a)
        )
        + row(r"\Rightarrow " + sought + "=" + latex(result))
    )
    return first


def alternative_proof(facts, sought, result, image):
    k, a, b, c0 = (facts[key] for key in ("k", "a", "b", "c"))
    ux, uy = facts["offset"]
    alternative = (
        image
        + f"<p>Выделим целую часть, чтобы формула была канонической для гиперболы. "
        f"Для этого прибавим и вычтем {formula('kb')}.</p>"
        + row(r"f(x)=\frac{kx+a}{x+b}=\frac{kx+kb+a-kb}{x+b}=\frac{k(x+b)+(a-kb)}{x+b}")
        + "<p>Разделим сумму на знаменатель и сократим первую дробь:</p>"
        + row(r"f(x)=\frac{k(x+b)}{x+b}+\frac{a-kb}{x+b}=k+\frac{a-kb}{x+b}")
        + "<p><br/></p>"
        + "<p>Каноническое уравнение гиперболы — "
        + formula(r"f(x)=\frac{A}{x+B}+C")
        + ". А значит, в нашем случае:</p>"
        + f"<p>{formula('B=b')} — сдвиг по горизонтали. "
        + (
            f"Асимптота {formula('x=' + latex(-b))}: на {formula(latex(abs(b)))} "
            + ("влево" if b > 0 else "вправо")
            if b
            else f"Асимптота {formula('x=0')}: сдвига нет"
        )
        + f" {formula(r'\Rightarrow B=' + latex(b))}.</p>"
        + f"<p>{formula('C=k')} — сдвиг по вертикали. "
        + (
            f"Асимптота {formula('y=' + latex(k))}: на {formula(latex(abs(k)))} "
            + ("вверх" if k > 0 else "вниз")
            if k
            else f"Асимптота {formula('y=0')}: сдвига нет"
        )
        + f" {formula(r'\Rightarrow C=' + latex(k))}.</p>"
        + f"<p>{formula('A=a-kb')} — масштаб и знак ветвей. "
        f"Ветви в {'I и III' if c0 > 0 else 'II и IV'} четвертях относительно асимптот, поэтому {formula('A>0' if c0 > 0 else 'A<0')}.</p>"
        + f"<p>На {formula(latex(abs(uy - k)))} "
        + ("выше" if uy - k > 0 else "ниже")
        + " горизонтальной асимптоты отступ от вертикальной асимптоты равен "
        + formula(latex(abs(ux + b)))
        + " "
        + ("вправо" if ux + b > 0 else "влево")
        + " (красный отрезок) "
        + formula(r"\Rightarrow A=" + latex(c0))
        + ".</p>"
        + row(rf"f(x)=\frac{{{latex(c0)}}}{{x{signed(b)}}}" + signed(k))
        + (
            "<p><br/></p>"
            + row(r"A=a-kb\Rightarrow a=A+kb")
            + row("k=C=" + latex(k) + r",\qquad b=B=" + latex(b))
            + row(
                "a="
                + latex(c0)
                + "+"
                + (latex(k) if k >= 0 else "(" + latex(k) + ")")
                + r"\cdot "
                + (latex(b) if b >= 0 else "(" + latex(b) + ")")
                + "="
                + latex(c0)
                + signed(k * b)
                + "="
                + latex(a)
            )
            if sought == "a"
            else row(
                sought + "=" + ("C" if sought == "k" else "B") + "=" + latex(result)
            )
        )
    )
    return alternative
