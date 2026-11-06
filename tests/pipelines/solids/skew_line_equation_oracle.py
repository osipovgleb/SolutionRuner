"""Check scalar, vector and coordinate equations using independent geometry."""

import re

import sympy as sp
from altitude_geometry_oracle import substitute
from bs4 import BeautifulSoup
from projection_plane_equation_oracle import ScalarParser, equal, values_for
from skew_line_geometry import geometry

from solution_runner.pipelines.equations.logarithm_parser import Node
from solution_runner.pipelines.equations.power_arithmetic import balanced


class VectorParser(ScalarParser):
    implicit_prefixes = ScalarParser.implicit_prefixes + (r"\mathbf", r"\arcsin")

    def __init__(self, text, vectors):
        super().__init__(text)
        self.vectors = vectors

    def _nested(self, text):
        return VectorParser(text, self.vectors).parse()

    def _primary(self):
        for name, vector in self.vectors.items():
            if self.text.startswith(name, self.index):
                self.index += len(name)
                return Node(vector, "", "vector")
        if self.text.startswith(r"\arcsin", self.index):
            self.index += len(r"\arcsin")
            if self.text[self.index : self.index + 1] == "{":
                argument, self.index = balanced(self.text, self.index)
                result = self._nested(argument).value
            else:
                result = self._primary().value
            return Node(sp.asin(result), "", "inverse")
        return super()._primary()


def evaluate(raw, values, vectors):
    raw = re.sub(r"\\frac\s*([A-Za-z0-9])\s*([A-Za-z0-9])", r"\\frac{\1}{\2}", raw)
    raw = re.sub(r"\\frac\s*([A-Za-z0-9])\s*\{", r"\\frac{\1}{", raw)
    commands = {k: v for k, v in values.items() if k.startswith(("\\", "|"))}
    for name, value in sorted(commands.items(), key=lambda item: -len(item[0])):
        raw = raw.replace(name, "(" + sp.latex(value) + ")")
    protected = {}
    for name, vector in sorted(vectors.items(), key=lambda item: -len(item[0])):
        if name in raw:
            key = r"\mathbf{V" + str(len(protected)) + "}"
            raw = raw.replace(name, key)
            protected[key] = vector
    raw = substitute(raw, {k: v for k, v in values.items() if k not in commands})
    raw = re.sub(
        r"\|([^|]+)\|", lambda m: "(" + sp.latex(abs(evaluate(m[1], {}, {}))) + ")", raw
    )
    raw = re.sub(r"\\sqrt([23])", r"\\sqrt{\1}", raw)
    for name in ("acos", "atan", "asin"):
        raw = raw.replace(r"\operatorname{" + name + "}", r"\arc" + name[1:])
    return sp.simplify(VectorParser(raw, protected).parse().value)


def scalar_values(p, m, answer):
    values = values_for(p, {})
    for name in (
        "HKM",
        "ABC",
        "BSM",
        "BSC",
        "BMN",
        "CBE",
        "DB_1F",
        "CA_1F",
        "EOM",
        "EOK",
    ):
        names = re.findall(r"[A-Z](?:_1)?", name)
        if not all(n in p for n in names):
            continue
        A, B, C = (p[n] for n in names)
        u, v = A - B, C - B
        if u.norm() == 0 or v.norm() == 0:
            continue
        cosine = sp.simplify(u.dot(v) / (u.norm() * v.norm()))
        values[r"\cos\angle " + name] = cosine
        values[r"\sin\angle " + name] = sp.simplify(
            u.cross(v).norm() / (u.norm() * v.norm())
        )
        if u.dot(v) != 0:
            values[r"\tan\angle " + name] = sp.simplify(u.cross(v).norm() / u.dot(v))
    alpha = (
        sp.acos(answer) if m.mode == "triangle_pyramid_midpoint_skew_cosine" else answer
    )
    values.update(
        {
            r"\alpha": alpha,
            r"\cos\alpha": sp.cos(alpha),
            r"\sin\alpha": sp.sin(alpha),
            r"\tan\frac{\alpha}{2}": sp.simplify(
                sp.sqrt((1 - sp.cos(alpha)) / (1 + sp.cos(alpha)))
            ),
        }
    )
    if m.mode == "cube_midpoint_skew_angle":
        values["a"] = dict(m.given).get("a", sp.S.One)
    if m.mode == "tetra_parallel_midpoint_diagonal_angle":
        values["S"] = (p["K"] - p["E"]).cross(p["M"] - p["E"]).norm()
    return values


def frames(p, m):
    if m.mode == "cube_midpoint_skew_angle":
        a = dict(m.given).get("a", sp.S.One)
        origin = p["B"]
        basis = sp.Matrix.hstack(
            (p["C"] - origin) / a, (p["A"] - origin) / a, (p["B_1"] - origin) / a
        )
        frame = {n: basis.T * (v - origin) / a for n, v in p.items()}
    else:
        frame = p
    vectors = {
        r"\overrightarrow{" + a + b + "}": B - A
        for a, A in frame.items()
        for b, B in frame.items()
        if a != b
    }
    if m.mode == "triangle_prism_split_edge_projection_angle":
        u, v, w = p["A"] - p["B"], p["C"] - p["B"], p["B_1"] - p["B"]
        normal = sp.Matrix([p["B"][1], -p["B"][0], 0])
        vectors.update(
            {
                r"\vec{a}": u,
                r"\vec{b}": v,
                r"\vec{c}": w,
                r"\vec{n}": normal,
                r"\vec{n}_0": u.cross(w),
                r"\vec{a}\times\vec{c}": u.cross(w),
                r"\overrightarrow{AB}\times\overrightarrow{BB_1}": (
                    p["B"] - p["A"]
                ).cross(w),
            }
        )
    return frame, vectors


def vector_values(vectors, html):
    values = {
        "|" + name + "|": vector.norm()
        for name, vector in vectors.items()
        if "|" + name + "|" in html
    }
    atom = r"(?:\\overrightarrow\{[A-Z_1]+\}|\\vec\{[abcn]\}(?:_0)?)"
    for first, second in re.findall("(" + atom + r")\\cdot(" + atom + ")", html):
        values[first + r"\cdot" + second] = sp.simplify(
            vectors[first].dot(vectors[second])
        )
    if r"\vec{a}" in vectors:
        a, b, c = (vectors[r"\vec{" + n + "}"] for n in "abc")
        values[r"|\vec{b}\cdot(\vec{a}\times\vec{c})|"] = abs(b.dot(a.cross(c)))
        values[r"|\vec{b}\times\vec{a}|"] = b.cross(a).norm()
    return values


def verify(html, m):
    p, answer = geometry(m)
    if m.mode == "cube_midpoint_skew_angle" and m.names[0] == "side":
        edge = dict(m.given).get("a", sp.S.One)
        p = {n: v / edge for n, v in p.items()}
    values = scalar_values(p, m, answer)
    frame, vectors = frames(p, m)
    values.update(vector_values(vectors, html))
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"].replace("{,}", ".")
        if re.match(r"[A-Z](?:_1)?\(", formula):
            for component in formula.split(r",\quad "):
                name, coordinates = component.split("(", 1)
                actual = sp.Matrix(
                    [evaluate(c, values, {}) for c in coordinates[:-1].split(";")]
                )
                assert sp.simplify(actual - frame[name]).is_zero_matrix, formula
            continue
        for equation in formula.split(r",\qquad "):
            results = []
            for raw in equation.split("="):
                if ";" in raw:
                    results.append(
                        sp.Matrix(
                            [evaluate(c, values, {}) for c in raw[1:-1].split(";")]
                        )
                    )
                else:
                    try:
                        results.append(evaluate(raw, values, vectors))
                    except Exception as exc:
                        raise AssertionError((formula, raw)) from exc
            assert len(results) > 1, formula
            for actual in results[1:]:
                expected = results[0]
                assert (
                    sp.simplify(actual - expected).is_zero_matrix
                    if isinstance(actual, sp.MatrixBase)
                    else equal(actual, expected)
                ), (formula, results)
    assert equal(m.answer, answer)
