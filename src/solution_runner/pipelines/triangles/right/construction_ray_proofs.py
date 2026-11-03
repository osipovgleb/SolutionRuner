"""Retain the six reviewed angle arguments, including reversed and coincident rays."""

import hashlib

from ...core.errors import ContentPlanError
from ...core.numbers import format_answer
from ...probability.common import line
from .altitude_methods import solution_section
from .construction_angles import (
    BISECTOR_MEDIAN,
    BISECTOR_MEDIAN_INVERSE,
    HEIGHT_BISECTOR,
    HEIGHT_BISECTOR_INVERSE,
    HEIGHT_MEDIAN,
    HEIGHT_MEDIAN_INVERSE,
)

# Exact reviewed parent HTML: a changed method requires a new source review.
_PARENTS = {
    HEIGHT_BISECTOR: "9f3ddd1004ec3fe08d5c227eac689d1a6a25b1339b5c8f1e7bb52608bf6df344",
    HEIGHT_BISECTOR_INVERSE: "9e5a4ada79110ca73a8bd5aa6ab74f363069bb3cdfc19a22b21caf11de775869",
    HEIGHT_MEDIAN: "2973a4737312363a94db65a7a03d6cdef80f77a7b535d21b4fa2a271b6ab9794",
    HEIGHT_MEDIAN_INVERSE: "237cea35670bdd15265710a2191c0093f749e77ecbb771508b430a6ddfe6aee0",
    BISECTOR_MEDIAN: "d52506f098ac9b845713449a19153cb05ed637c71393d9627cd05fef29bd85f1",
    BISECTOR_MEDIAN_INVERSE: "dd6831ba9713c3107c3b72c86247258c24cea351940e3241d4c2055c21349505",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError("the complete two-ray parent method must be reviewed")


def degree(value):
    return format_answer(value).replace(",", "{,}") + r"^{\circ}"


def _setup(model):
    if model.given_kind == "named_b":
        return (
            "<p>Острые углы прямоугольного треугольника в сумме дают 90°. Найдем угол A:</p>"
            + line(
                r"\angle A=90^{\circ}-\angle B=90^{\circ}-"
                + degree(model.b)
                + "="
                + degree(model.a)
            )
        )
    if model.given_kind == "separation":
        return "<p>Обозначим меньший острый угол через A, больший — через B, а прямой угол — через C. При равных острых углах выбор A и B произволен.</p>"
    return (
        "<p>Обозначим меньший острый угол через A, больший — через B, а прямой угол — через C. При равных острых углах выбор A и B произволен. По условию и сумме острых углов:</p>"
        + line(r"\angle A=" + degree(model.a))
        + line(r"\angle B=" + degree(model.b))
    )


def _height_bisector(model):
    body = "<p>CH — высота, CD — биссектриса прямого угла. Поэтому:</p>" + line(
        r"\angle ACD=\frac{\angle C}{2}=45^{\circ}"
    )
    if model.request == "smaller":
        body += "<p>Угол ACH не меньше HCB, поскольку угол A не больше B. Рассмотрим прямоугольный треугольник ACH:</p>"
        body += line(
            r"\angle ACH=\angle ACD+\angle DCH=45^{\circ}+"
            + degree(model.separation)
            + "="
            + degree(model.b)
        )
        body += line(r"\angle A=90^{\circ}-\angle ACH")
        body += line(
            r"\angle A=90^{\circ}-(45^{\circ}+"
            + degree(model.separation)
            + ")="
            + degree(model.a)
        )
    else:
        body += line(r"\angle BCH=90^{\circ}-\angle B=" + degree(model.a))
        body += "<p>Имеем:</p>"
        if model.topology >= 0:
            body += line(r"\angle DCH=\angle C-\angle ACD-\angle BCH")
            body += line(
                r"\angle DCH=90^{\circ}-45^{\circ}-"
                + degree(model.a)
                + "="
                + degree(model.separation)
            )
        else:
            body += "<p>Угол ACH равен B и меньше 45°, поэтому луч CH лежит между CA и CD:</p>"
            body += line(r"\angle ACH=\angle B=" + degree(model.b))
            body += line(
                r"\angle DCH=\angle ACD-\angle ACH=45^{\circ}-"
                + degree(model.b)
                + "="
                + degree(model.separation)
            )
    if model.topology == 0:
        body += "<p>Острые углы равны 45°. Высота и биссектриса совпадают: H = D, угол между ними равен нулю.</p>"
    return body


def _median_fact():
    return (
        "<p>Медиана CM, проведенная к гипотенузе прямоугольного треугольника, равна ее половине:</p>"
        + line("AM=MC=MB")
        + "<p>Следовательно, углы A и ACM равны как углы при основании равнобедренного треугольника AMC:</p>"
        + line(r"\angle ACM=\angle A")
    )


def _height_median(model):
    if model.request == "larger":
        if model.topology == 0:
            return (
                _median_fact()
                + "<p>При нулевом угле между высотой CH и медианой CM их лучи совпадают. По свойству высоты угол ACH равен B, поэтому:</p>"
                + line(r"\angle A=\angle ACM=\angle ACH=\angle B")
                + line(r"\angle B=\frac{90^{\circ}}{2}=45^{\circ}")
                + "<p>Оба острых угла равны, их максимальное значение — 45°.</p>"
            )
        return (
            "<p>В прямоугольном треугольнике CHM угол при C дан в условии. Найдем угол при M:</p>"
            + line(
                r"\angle CMB=90^{\circ}-\angle MCH=90^{\circ}-"
                + degree(model.separation)
                + "="
                + degree(90 - model.separation)
            )
            + "<p>Треугольник ACB прямоугольный, CM — медиана, проведенная из вершины прямого угла. Она равна половине гипотенузы:</p>"
            + line("CM=MB")
            + "<p>Углы B и MCB равны как углы при основании равнобедренного треугольника CMB. Тогда:</p>"
            + line(r"\angle B=\frac{180^{\circ}-\angle CMB}{2}")
            + line(
                r"\angle B=\frac{180^{\circ}-(90^{\circ}-"
                + degree(model.separation)
                + r")}{2}"
            )
            + line(
                r"\angle B=\frac{180^{\circ}-"
                + degree(90 - model.separation)
                + r"}{2}="
                + degree(model.b)
            )
            + "<p>Этот угол не меньше 45°, поэтому он является большим из двух острых углов.</p>"
        )
    body = (
        _median_fact()
        + "<p>По свойству высоты прямоугольного треугольника:</p>"
        + line(r"\angle BCH=90^{\circ}-\angle B=" + degree(model.a))
    )
    if model.topology >= 0:
        body += (
            "<p>Основание высоты ближе к вершине большего острого угла. Имеем:</p>"
            if model.topology > 0
            else "<p>При равных острых углах высота и медиана совпадают. Имеем:</p>"
        )
        body += line(r"\angle MCH=\angle C-\angle ACM-\angle BCH")
        body += line(
            r"\angle MCH=90^{\circ}-"
            + degree(model.a)
            + "-"
            + degree(model.a)
            + "="
            + degree(model.separation)
        )
    else:
        body += "<p>Угол A больше B, поэтому луч CH лежит между CA и CM:</p>"
        body += line(r"\angle ACH=\angle B=" + degree(model.b))
        body += line(
            r"\angle MCH=\angle ACM-\angle ACH="
            + degree(model.a)
            + "-"
            + degree(model.b)
            + "="
            + degree(model.separation)
        )
    if model.topology == 0:
        body += "<p>Высота и медиана совпадают: H = M, угол между ними равен нулю.</p>"
    return body


def _bisector_median(model):
    body = (
        _median_fact()
        + "<p>Биссектриса CD делит прямой угол пополам:</p>"
        + line(r"\angle ACD=\angle BCD=45^{\circ}")
    )
    if model.request == "smaller":
        body += "<p>Искомый угол A не больше 45°. Тогда:</p>"
        body += line(r"\angle A=\angle ACM=\angle C-\angle BCD-\angle MCD")
        body += line(
            r"\angle A=90^{\circ}-45^{\circ}-"
            + degree(model.separation)
            + "="
            + degree(model.a)
        )
    elif model.topology >= 0:
        body += "<p>Имеем:</p>" + line(
            r"\angle MCD=\angle C-\frac{\angle C}{2}-\angle ACM"
        )
        body += line(
            r"\angle MCD=45^{\circ}-" + degree(model.a) + "=" + degree(model.separation)
        )
    else:
        body += "<p>Угол ACM равен A и больше 45°, поэтому луч CD лежит между CA и CM. Порядок вычитания меняется:</p>"
        body += line(
            r"\angle MCD=\angle ACM-\angle ACD="
            + degree(model.a)
            + r"-45^{\circ}="
            + degree(model.separation)
        )
    if model.topology == 0:
        body += (
            "<p>Медиана и биссектриса совпадают: M = D, угол между ними равен нулю.</p>"
        )
    return body


def render(model):
    proof = {"HD": _height_bisector, "HM": _height_median, "DM": _bisector_median}[
        model.pair
    ]
    return solution_section("Решение", _setup(model) + proof(model))
