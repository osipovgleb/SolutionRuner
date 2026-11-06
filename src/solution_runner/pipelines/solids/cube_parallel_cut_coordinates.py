"""Retain both parent coordinate frames with a consistent normal system."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _system(m, pictures):
    q = m.q
    a, k = q["a"], q["k"]
    y = a - q["B1P"]
    return (
        pictures.get("image_2", "")
        + "<p><b>Другой способ. Метод координат.</b></p>"
        + "<p>Начало координат выберем в D, оси направим вдоль DA, DC и DD₁. Координаты точек сечения:</p>"
        + line(
            r"C_1(0;"
            + value(a)
            + ";"
            + value(a)
            + r"),\quad K("
            + value(a)
            + ";"
            + value(a)
            + ";"
            + value(k)
            + r"),\quad P("
            + value(a)
            + ";"
            + value(y)
            + ";"
            + value(a)
            + ")"
        )
        + "<p>Подставим эти точки в уравнение Nₓx + Nᵧy + N𝓏z + c = 0:</p>"
        + line(
            r"\begin{cases}"
            + value(a)
            + "N_y+"
            + value(a)
            + r"N_z+c=0\\"
            + value(a)
            + "N_x+"
            + value(a)
            + "N_y+"
            + value(k)
            + r"N_z+c=0\\"
            + value(a)
            + "N_x+"
            + value(y)
            + "N_y+"
            + value(a)
            + r"N_z+c=0\end{cases}"
        )
    )


def _normal(m):
    q = m.q
    a, k, d = q["a"], q["k"], q["d"]
    return (
        "<p>Вычтем первое уравнение из второго и третьего. Получим зависимости между компонентами нормали:</p>"
        + line(
            value(a)
            + r"N_x="
            + value(d)
            + r"N_z,\qquad "
            + value(q["B1P"])
            + r"N_y="
            + value(a)
            + r"N_x"
        )
        + "<p>Выбирая ненулевой множитель так, чтобы N𝓏 равнялась длине ребра куба, получаем:</p>"
        + line(r"\vec n_{\alpha}=(" + value(d) + ";" + value(k) + ";" + value(a) + ")")
        + line(
            value(d)
            + "x+"
            + value(k)
            + "y+"
            + value(a)
            + "z-"
            + value(a * (a + k))
            + "=0"
        )
        + "<p>Грань BB₁C₁C лежит в плоскости y = AB. Её нормаль — (0; 1; 0). Косинус острого угла между плоскостями равен модулю косинуса между нормалями:</p>"
        + line(
            r"\cos\varphi=\frac{"
            + value(k)
            + r"}{\sqrt{"
            + bracket(d)
            + "^2+"
            + bracket(k)
            + "^2+"
            + bracket(a)
            + "^2}}="
            + value(q["cos"])
        )
        + line(
            r"\tan\varphi=\frac{\sqrt{1-\cos^2\varphi}}{\cos\varphi}=" + value(q["tan"])
        )
    )


def _intercepts(m):
    q = m.q
    a, k, d = q["a"], q["k"], q["d"]
    return (
        "<p><b>Способ с уравнением плоскости в отрезках.</b> Начало координат выберем в B₁, оси направим вдоль B₁A₁, B₁C₁ и B₁B. Пересечения плоскости с осями — P, C₁ и K:</p>"
        + line(
            r"P("
            + value(q["B1P"])
            + r";0;0),\quad C_1(0;"
            + value(a)
            + r";0),\quad K(0;0;"
            + value(d)
            + ")"
        )
        + line(
            r"\frac{x}{"
            + bracket(q["B1P"])
            + r"}+\frac{y}{"
            + value(a)
            + r"}+\frac{z}{"
            + value(d)
            + "}=1"
        )
        + line(value(k) + "x+" + value(d) + "y+" + value(a) + "z=" + value(a * d))
        + "<p>Теперь нормаль α имеет компоненты в другом порядке. Грань BB₁C₁C задаётся x = 0:</p>"
        + line(
            r"\vec n_{\alpha}=("
            + value(k)
            + ";"
            + value(d)
            + ";"
            + value(a)
            + r"),\qquad\vec n_{BB_1C_1C}=(1;0;0)"
        )
        + line(
            r"\cos\varphi=\frac{"
            + value(k)
            + r"}{\sqrt{"
            + bracket(k)
            + "^2+"
            + bracket(d)
            + "^2+"
            + bracket(a)
            + "^2}}="
            + value(q["cos"])
        )
    )


def render(m, pictures):
    return _system(m, pictures) + _normal(m) + _intercepts(m)
