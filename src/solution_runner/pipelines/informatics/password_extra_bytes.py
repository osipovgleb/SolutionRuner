"""Compute whole-byte password storage and per-user additional information."""

from solution_runner.pipelines.word_problems.common import (
    UnsupportedCondition, finalize,
)

from .password_extra_bytes_condition import parse_record, read_content

from .password_storage import formula as _formula, storage_steps


def build_context_repair_plan(context):
    _, condition, answer_section, solution_section, text = read_content(context)
    record = parse_record(text)
    length, size, users, total = record.length, record.size, record.users, record.total
    password_bytes, intro = storage_steps(
        length, size, genitive=record.genitive, locative=record.locative,
        accusative=record.accusative, alphabet_formula=record.alphabet_formula,
    )
    per_user, remainder = divmod(total, users)
    extra = per_user - password_bytes
    if remainder or extra < 0:
        raise UnsupportedCondition("memory allocation is inconsistent with whole bytes per user")
    solution = (
        intro
        + f'<p>Пусть количество памяти под дополнительные сведения об одном {record.entity} равно '
        '<span data-inline-latex="x"></span> байт. Составим уравнение для общего объёма памяти.</p>'
        + _formula(rf"{users}\cdot({password_bytes}+x)={total}")
        + _formula(rf"{password_bytes}+x=\frac{{{total}}}{{{users}}}={per_user}")
        + _formula(rf"x={per_user}-{password_bytes}={extra}")
    )
    current_solution = str((solution_section or {}).get("html") or "")
    return finalize(
        condition, answer_section, solution_section, extra, solution,
        rewrite_existing_solution=current_solution != solution,
    )
