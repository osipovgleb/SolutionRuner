"""Fail-closed planner for elementary exponential equations."""
from __future__ import annotations
from fractions import Fraction
import re
from typing import Any
from bs4 import BeautifulSoup
from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, format_latex_fraction, parse_rational
from solution_runner.pipelines.equations.group_26656 import RepairPlan

RULE = "exponential-26650-common-base-affine-exponent"
_NUMBER = r"(?:[1-9]\d*(?:\{,\}\d+)?|0\{,\}[1-9]\d*|\\frac\{[1-9]\d*\}\{[1-9]\d*\}|\(\\frac\{[1-9]\d*\}\{[1-9]\d*\}\)|\\left\(\\frac\{[1-9]\d*\}\{[1-9]\d*\}\\right\))"
_FORMULA = re.compile(rf"(?P<base>{_NUMBER})\^\{{(?P<exponent>[^{{}}]+)\}}=(?P<right>{_NUMBER})")
_TWO_BASES = re.compile(rf"(?P<left_base>{_NUMBER})\^\{{(?P<left_exponent>[^{{}}]+)\}}=(?P<right_base>{_NUMBER})\^\{{(?P<right_exponent>[^{{}}]+)\}}")
_DIVIDED_SAME_BASE = re.compile(rf"(?P<base>{_NUMBER})\^\{{(?P<left_exponent>[^{{}}]+)\}}\\colon (?P=base)\^\{{(?P<right_exponent>[^{{}}]+)\}}=(?P<right>{_NUMBER})")
_MULTIPLIED_SAME_BASE = re.compile(rf"(?P<base>{_NUMBER})\^\{{(?P<left_exponent>[^{{}}]+)\}}\\cdot (?P=base)\^\{{(?P<right_exponent>[^{{}}]+)\}}=(?P<right>{_NUMBER})")
_CONSTANT_FIRST = re.compile(r"(?P<constant>-?\d+)(?P<sign>[+-])(?P<coefficient>\d*)x")
_VARIABLE_FIRST = re.compile(r"(?P<coefficient>-?\d*)x(?P<sign>[+-])(?P<constant>\d+)")

class UnsupportedCondition(ValueError): pass

def _parse_base(token: str) -> Fraction:
    """Parse a supported base, including TeX sizing delimiters around a fraction."""
    return parse_rational(token.replace(r"\left(", "").replace(r"\right)", "").strip("()"))

def _exponent(value: Fraction, base: Fraction) -> int:
    if base <= 0 or base == 1: raise UnsupportedCondition("base must be positive and different from one")
    if value <= 0: raise UnsupportedCondition("right side must be positive")
    exponent = 0; current = Fraction(1)
    if (base > 1 and value > 1) or (base < 1 and value < 1):
        while (base > 1 and current < value) or (base < 1 and current > value):
            current *= base; exponent += 1
    elif value != 1:
        while (base > 1 and current > value) or (base < 1 and current < value):
            current /= base; exponent -= 1
    if current != value: raise UnsupportedCondition("right side is not an exact power of the base")
    return exponent

def _parse_linear(value: str) -> tuple[int, int]:
    if value == "x": return 0, 1
    if value == "-x": return 0, -1
    if re.fullmatch(r"-?\d+x", value):
        return 0, int(value[:-1])
    m = _CONSTANT_FIRST.fullmatch(value)
    if m:
        coefficient=int(m.group("coefficient") or "1") * (-1 if m.group("sign")=="-" else 1)
        return int(m.group("constant")), coefficient
    m = _VARIABLE_FIRST.fullmatch(value)
    if m:
        constant=int(m.group("constant")) * (-1 if m.group("sign")=="-" else 1)
        coefficient = -1 if m.group("coefficient")=="-" else int(m.group("coefficient") or "1")
        return constant, coefficient
    raise UnsupportedCondition("exponent is not an accepted affine expression")

def _linear_latex(constant: int, coefficient: int) -> str:
    x = "x" if coefficient == 1 else "-x" if coefficient == -1 else f"{coefficient}x"
    if constant == 0: return x
    return f"{constant}{'+' if coefficient > 0 else ''}{x}" if constant else x

def _variable_first_latex(constant: int, coefficient: int) -> str:
    """Render a nonzero affine exponent in the familiar ``mx ± n`` order."""
    x = "x" if coefficient == 1 else "-x" if coefficient == -1 else f"{coefficient}x"
    return x if constant == 0 else f"{x}{constant:+d}"

def _base_latex(value: Fraction) -> str:
    latex=format_latex_fraction(value)
    return latex if value.denominator == 1 else f"({latex})"

def _answer_steps(value: Fraction) -> str:
    """Render the terminal answer in exact and, when needed, decimal form."""
    exact = format_latex_fraction(value)
    if value.denominator == 1:
        return f"x={exact}"
    try:
        decimal = format_answer(value)
    except NumberFormatError as e:
        raise UnsupportedCondition("answer does not terminate") from e
    return f"x={exact}\\iff x={decimal.replace(',', '{,}')}"

def _primitive_integer_base(base: Fraction) -> tuple[Fraction, int]:
    if base.numerator == 1 and base.denominator > 1:
        value=base.denominator
        for candidate in range(2, value):
            power=1; degree=0
            while power < value:
                power *= candidate; degree += 1
            if power == value:
                return Fraction(candidate), -degree
        return base, 1
    if base.denominator != 1: return base, 1
    value=base.numerator
    for candidate in range(2, value):
        power=1; degree=0
        while power < value:
            power *= candidate; degree += 1
        if power == value: return Fraction(candidate), degree
    return base, 1

def _common_base_for_two_sides(base: Fraction) -> tuple[Fraction, int]:
    """Express a unit fraction through its positive reciprocal base."""
    if base.numerator == 1 and base.denominator > 1:
        common, degree = _primitive_integer_base(Fraction(base.denominator))
        return common, -degree
    return _primitive_integer_base(base)

def _fractional_common_base(base: Fraction) -> tuple[Fraction, int]:
    """Reduce a unit fraction while keeping the common base fractional."""
    if base.numerator != 1 or base.denominator <= 1:
        return base, 1
    denominator_base, degree = _primitive_integer_base(Fraction(base.denominator))
    if denominator_base.denominator != 1:
        return base, 1
    return Fraction(1, denominator_base.numerator), degree

def _scaled_exponent(source: str, factor: int) -> str:
    constant, coefficient=_parse_linear(source)
    m=_VARIABLE_FIRST.fullmatch(source)
    if m:
        coefficient *= factor; constant *= factor
        if factor == -1 and coefficient < 0 and constant > 0:
            term = "x" if coefficient == -1 else f"{-coefficient}x"
            return f"{constant}-{term}"
        x="x" if coefficient==1 else "-x" if coefficient==-1 else f"{coefficient}x"
        return x if constant==0 else f"{x}{constant:+d}"
    return _linear_latex(constant*factor, coefficient*factor)

def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    found=[s for s in content.get("sections",[]) if s.get("key")==key]
    if len(found)>1: raise UnsupportedCondition(f"multiple {key} sections")
    return found[0] if found else None

def _rewrite(section: dict[str, Any] | None,key:str,title:str,html:str)->dict[str,Any]:
    return {"transformation_target_id":str((section or {}).get("transformation_target_id") or f"section:{key}"),"operation":"rewrite" if section else "add","value":{"title":title,"html":html,"asset_keys":[]}}

def _solution_signature(html: str) -> tuple[str, str] | None:
    soup = BeautifulSoup(html, "html.parser")
    formulas = [str(span.get("data-inline-latex") or "") for span in soup.find_all("span") if span.has_attr("data-inline-latex")]
    if len(formulas) != 1 or not formulas[0]:
        return None
    prose = re.sub(r"\s+", " ", soup.get_text(" ", strip=True).replace("\u00ad", "").replace("ё", "е")).strip()
    return formulas[0], prose

def build_repair_plan(formula: str) -> RepairPlan:
    combined_match = _DIVIDED_SAME_BASE.fullmatch(formula) or _MULTIPLIED_SAME_BASE.fullmatch(formula)
    if combined_match:
        left_constant, left_coefficient = _parse_linear(combined_match.group("left_exponent"))
        right_constant, right_coefficient = _parse_linear(combined_match.group("right_exponent"))
        is_division = "\\colon" in formula
        exponent = _variable_first_latex(
            left_constant - right_constant if is_division else left_constant + right_constant,
            left_coefficient - right_coefficient if is_division else left_coefficient + right_coefficient,
        )
        combined = f"{combined_match.group('base')}^{{{exponent}}}={combined_match.group('right')}"
        collapsed = build_repair_plan(combined)
        marker = f"{combined}\\iff "
        if marker not in collapsed.solution_html:
            raise UnsupportedCondition("collapsed division solution is malformed")
        solution_html = collapsed.solution_html.replace(
            marker,
            f"{formula}\\iff {combined}\\iff ",
            1,
        )
        return RepairPlan(
            answer=collapsed.answer,
            condition_html="",
            solution_html=solution_html,
        )
    two=_TWO_BASES.fullmatch(formula)
    if two:
        try:
            left_base=_parse_base(two.group("left_base")); right_base=_parse_base(two.group("right_base"))
        except ValueError as e: raise UnsupportedCondition("bases are unsupported") from e
        common,left_factor=_common_base_for_two_sides(left_base); common_right,right_factor=_common_base_for_two_sides(right_base)
        if common != common_right: raise UnsupportedCondition("bases do not reduce to one common base")
        left_constant,left_coefficient=_parse_linear(two.group("left_exponent")); right_constant,right_coefficient=_parse_linear(two.group("right_exponent"))
        coefficient=left_factor*left_coefficient-right_factor*right_coefficient; constant=left_factor*left_constant-right_factor*right_constant
        if coefficient==0: raise UnsupportedCondition("equation has no unique root")
        result=Fraction(-constant,coefficient)
        try: answer=format_answer(result)
        except NumberFormatError as e: raise UnsupportedCondition("answer does not terminate") from e
        left=_scaled_exponent(two.group("left_exponent"),left_factor); right=_scaled_exponent(two.group("right_exponent"),right_factor)
        base_latex=_base_latex(common)
        moved_coefficient = right_factor * right_coefficient - left_factor * left_coefficient
        moved_constant = left_factor * left_constant - right_factor * right_constant
        moved_x = "x" if moved_coefficient == 1 else "-x" if moved_coefficient == -1 else f"{moved_coefficient}x"
        common_base_step = "" if left_base == right_base and left_factor == right_factor == 1 else f"{base_latex}^{{{left}}}={base_latex}^{{{right}}}\\iff "
        solution=("<p>Перейдём к одному основанию степени:</p>"
            f'<center><p><span data-inline-latex="{formula}\\iff {common_base_step}{left}={right}\\iff {moved_constant}={moved_x}\\iff {_answer_steps(result)}"></span>.</p></center>')
        return RepairPlan(answer=answer,condition_html="",solution_html=solution)
    m=_FORMULA.fullmatch(formula)
    if not m: raise UnsupportedCondition("unsupported exponential equation")
    base_token = m.group("base")
    try: base=_parse_base(base_token); right=_parse_base(m.group("right"))
    except ValueError as e: raise UnsupportedCondition("base or right side is unsupported") from e
    if "{,}" in base_token:
        common_base, base_factor, power = base, 1, _exponent(right, base)
    elif base.numerator == 1 and base.denominator > 1 and right.denominator > 1:
        common_base, base_factor = _fractional_common_base(base)
        power = _exponent(right, common_base)
    elif base.numerator == 1 and base.denominator > 1:
        reciprocal = Fraction(base.denominator)
        try:
            common_base, base_factor, power = reciprocal, -1, _exponent(right, reciprocal)
        except UnsupportedCondition:
            common_base, base_factor = _primitive_integer_base(base)
            power = _exponent(right, common_base)
    else:
        try:
            # Prefer the condition's own base whenever the right side is already
            # an exact power of it; this preserves the parent's presentation.
            common_base, base_factor, power = base, 1, _exponent(right, base)
        except UnsupportedCondition:
            common_base, base_factor = _primitive_integer_base(base)
            power=_exponent(right,common_base)
    constant,coefficient=_parse_linear(m.group("exponent")); result=Fraction(power-base_factor*constant,base_factor*coefficient)
    try: answer=format_answer(result)
    except NumberFormatError as e: raise UnsupportedCondition("answer does not terminate") from e
    exponent=_scaled_exponent(m.group("exponent"),base_factor)
    base_latex=_base_latex(common_base); right_power=f"{base_latex}^{{{power}}}"
    solution=("<p>Перейдём к одному основанию степени:</p>"
              f'<center><p><span data-inline-latex="{formula}\\iff {base_latex}^{{{exponent}}}={right_power}\\iff {exponent}={power}\\iff {_answer_steps(result)}"></span>.</p></center>')
    return RepairPlan(answer=answer,condition_html="",solution_html=solution)

def build_context_repair_plan(context:dict[str,Any])->RepairPlan:
    content=context.get("normalized_content")
    if not isinstance(content,dict) or content.get("format")!="teacherhelper-normalized" or content.get("schema_version")!=3 or content.get("assets") not in (None,[]): raise UnsupportedCondition("normalized assetless content is required")
    condition,answer,solution=(_section(content,k) for k in ("condition","answer","solution"))
    if condition is None or tuple(condition.get("asset_keys") or ()): raise UnsupportedCondition("canonical condition is required")
    raw=str(condition.get("html") or ""); soup=BeautifulSoup(raw,"html.parser"); spans=soup.find_all("span")
    normalize_condition = False
    if len(spans)==1 and not spans[0].get_text("",strip=True) and set(spans[0].attrs)=={"data-inline-latex"}:
        formula_span=spans[0]
        normalize_condition = formula_span.parent.name != "p"
        formula=str(formula_span.get("data-inline-latex") or ""); formula_span.replace_with(formula)
    else:
        match=re.search(r"(?P<a>\d+)<sup>(?P<ae>.*?)</sup>\s*=\s*(?P<b>\d+)<sup>(?P<be>.*?)</sup>",raw)
        if not match: raise UnsupportedCondition("condition equation is ambiguous")
        clean=lambda value: re.sub(r"\s+","",BeautifulSoup(value,"html.parser").get_text()).replace("−","-")
        formula=f"{match.group('a')}^{{{clean(match.group('ae'))}}}={match.group('b')}^{{{clean(match.group('be'))}}}"
        soup=BeautifulSoup(f"<p>Найдите корень уравнения {formula}.</p>","html.parser")
    visible=re.sub(r"\s+([.])",r"\1"," ".join(soup.get_text(" ",strip=True).replace("\u00ad","").split()))
    matched = next((
        (intro, end)
        for intro in ("Найдите корень уравнения", "Найдите корень уравнения:", "Найдите решение уравнения", "Найдите решение уравнения:", "Решите уравнение", "Решите уравнение:")
        for end in ("", ".")
        if visible == f"{intro} {formula}{end}"
    ), None)
    if matched is None: raise UnsupportedCondition("condition wording is unsupported")
    planned=build_repair_plan(formula); changes=[]
    if normalize_condition:
        intro, end = matched
        changes.append(_rewrite(condition, "condition", "Условие", f'<p>{intro} <span data-inline-latex="{formula}"></span>{end}</p>'))
    if solution is None or _solution_signature(str(solution.get("html") or "")) != _solution_signature(planned.solution_html):
        changes.append(_rewrite(solution,"solution","Решение",planned.solution_html))
    current=BeautifulSoup(str(answer.get("html") or "") if answer else "","html.parser").get_text("",strip=True).replace(" ","")
    if current!=planned.answer: changes.append(_rewrite(answer,"answer","Ответ",f'<p><span data-effect="spaced">{planned.answer}</span></p>'))
    return RepairPlan(answer=planned.answer,condition_html=str(condition.get("html") or ""),solution_html=planned.solution_html,transformations=tuple(changes))
