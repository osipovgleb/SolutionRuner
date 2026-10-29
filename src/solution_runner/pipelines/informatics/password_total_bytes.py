"""Find total storage for one uniformly encoded field and optional extra bytes."""

from solution_runner.pipelines.word_problems.common import UnsupportedCondition, finalize

from .password_extra_bytes_condition import read_content
from .password_total_bytes_condition import parse_total_record
from .password_storage import formula, storage_steps


def build_context_repair_plan(context):
    _, condition, answer_section, solution_section, text = read_content(context)
    record = parse_total_record(text)
    password_bytes, intro = storage_steps(
        record.length, record.size, genitive=record.genitive, locative=record.locative,
        accusative=record.accusative, alphabet_formula=record.alphabet_formula,
        items=record.items, item=record.item,
    )
    per_user = password_bytes + record.extra
    total = per_user * record.users
    if record.unit == 'Кбайт' and total % 1024:
        raise UnsupportedCondition('total storage is not an integer number of Kbytes')
    if record.extra:
        explanation = (
            f'Кроме {record.genitive}, на дополнительные сведения об одном {record.entity} отведено {record.extra} байт. '
            'Найдём общий объём памяти на одного пользователя, '
            f'а затем — на всех {record.users} {record.entities}.'
        )
        if record.entity == 'объекте':
            explanation = explanation.replace('на одного пользователя', 'на один объект')
        per_record = formula(rf'{password_bytes}+{record.extra}={per_user}\;\text{{байт}}')
    else:
        explanation = f'Найдём общий объём памяти для всех {record.users} {record.entities}.'
        per_record = ''
    if record.unit == 'Кбайт':
        explanation += ' В одном Кбайте 1024 байта, поэтому полученный объём в байтах разделим на 1024.'
    solution = (
        intro + '<p>' + explanation + '</p>' + per_record
        + formula(rf'{per_user}\cdot {record.users}={total}\;\text{{байт}}')
    )
    answer = total
    if record.unit == 'Кбайт':
        answer = total // 1024
        solution += formula(rf'\frac{{{total}}}{{1024}}={answer}\;\text{{Кбайт}}')
    return finalize(
        condition, answer_section, solution_section, answer, solution,
        rewrite_existing_solution=str((solution_section or {}).get('html') or '') != solution,
    )
