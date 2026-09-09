import pytest

from solution_runner.pipelines.word_problems.common import UnsupportedCondition
from solution_runner.pipelines.word_problems.group_26626 import build_context_repair_plan as promotion_plan
from solution_runner.pipelines.word_problems.group_26637 import build_context_repair_plan as bouquet_plan
from solution_runner.pipelines.word_problems.group_26641 import build_context_repair_plan as bookcase_plan
from solution_runner.pipelines.word_problems.group_26624 import build_context_repair_plan as medicine_plan
from solution_runner.pipelines.word_problems.group_506389 import build_context_repair_plan as purchase_plan
from solution_runner.pipelines.word_problems.group_99565 import build_context_repair_plan as population_plan
from solution_runner.pipelines.word_problems.group_99566 import build_context_repair_plan as stock_plan
from solution_runner.pipelines.word_problems.group_99567 import build_context_repair_plan as shirt_plan
from solution_runner.pipelines.word_problems.group_99568 import build_context_repair_plan as family_plan
from solution_runner.pipelines.word_problems.group_99569 import build_context_repair_plan as refrigerator_plan
from solution_runner.pipelines.word_problems.group_99570 import build_context_repair_plan as capital_plan


def _context(condition: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [{"key": "condition", "asset_keys": [], "html": f"<p>{condition}</p>"}]}}


def _context_with_existing_solution(condition: str) -> dict:
    context = _context(condition)
    context["normalized_content"]["sections"].append(
        {"key": "solution", "asset_keys": [], "html": "<p>Исходное решение автора.</p>"}
    )
    return context


@pytest.mark.parametrize(
    ("planner", "condition", "answer"),
    [
        (purchase_plan, "Сырок стоит 17 рублей 60 копеек. Какое наибольшее число сырков можно купить на 130 рублей?", "7"),
        (purchase_plan, "Сырок стоит 18 рублей. Какое наибольшее число сырков можно купить на 190 рублей?", "10"),
        (promotion_plan, "Шоколадка стоит 35 рублей. В воскресенье в супермаркете действует специальное предложение: заплатив за две шоколадки, покупатель получает три (одну в подарок). Какое наибольшее количество шоколадок можно получить, потратив не более 200 рублей в воскресенье?", "7"),
        (promotion_plan, "Шоколадка стоит 40 рублей. В воскресенье в супермаркете действует специальное предложение: заплатив за три шоколадки, покупатель получает четыре (одну в подарок). Сколько шоколадок можно получить на 200 рублей в воскресенье?", "6"),
        (bouquet_plan, "На день рождения полагается дарить букет из нечётного числа цветов. Хризантемы стоят 50 рублей за штуку. У Вани есть 500 рублей. Из какого наибольшего числа хризантем он может купить букет Маше на день рождения?", "9"),
        (bouquet_plan, "На день рождения полагается дарить букет из нечётного числа цветов. Тюльпаны стоят 55 рублей за штуку. У Вани есть 400 рублей. Из какого наибольшего числа тюльпанов он может купить букет Маше на день рождения?", "7"),
        (bookcase_plan, "В университетскую библиотеку привезли новые учебники по геометрии для 3 курсов, по 360 штук для каждого курса. Все книги одинаковы по размеру. В книжном шкафу 9 полок, на каждой полке помещается 25 учебников. Сколько шкафов можно полностью заполнить новыми учебниками?", "4"),
        (bookcase_plan, "В университетскую библиотеку привезли новые учебники по общей медицине для 4-5 курсов, по 130 штук для каждого курса. Все книги одинаковы по размеру. В книжном шкафу 8 полок, на каждой полке помещается 20 учебников. Сколько шкафов можно полностью заполнить новыми учебниками?", "1"),
        (medicine_plan, "Больному прописано лекарство, которое нужно пить по 0,5 г 3 раза в день в течение 21 дня. В одной упаковке 10 таблеток лекарства по 0,5 г. Какого наименьшего количества упаковок хватит на весь курс лечения?", "7"),
        (medicine_plan, "Больному прописано лекарство, которое нужно принимать по 0,5 г 2 раза в день в течение 7 дней. В одной упаковке 10 таблеток по 0,25г. Какого наименьшего количества упаковок хватит на весь курс лечения?", "3"),
    ],
)
def test_audited_parent_forms_are_solved(planner, condition: str, answer: str) -> None:
    plan = planner(_context(condition))
    assert plan.answer == answer
    assert len(plan.transformations) == 2


def test_rejects_a_condition_outside_the_group_template() -> None:
    with pytest.raises(UnsupportedCondition):
        purchase_plan(_context("Сырок стоит 17 рублей. Сколько сырков можно купить на 130 рублей?"))


def test_preserves_an_existing_solution_instead_of_rewriting_it() -> None:
    plan = bookcase_plan(_context_with_existing_solution(
        "В университетскую библиотеку привезли новые учебники по геометрии для 3 курсов, по 360 штук для каждого курса. Все книги одинаковы по размеру. В книжном шкафу 9 полок, на каждой полке помещается 25 учебников. Сколько шкафов можно полностью заполнить новыми учебниками?"
    ))

    assert not any(item["transformation_target_id"] == "section:solution" for item in plan.transformations)


def test_population_growth_replaces_only_its_old_source_template() -> None:
    condition = (
        "В 2008 году в городском квартале проживало 40000 человек. В 2009 году, в результате строительства новых домов, "
        "число жителей выросло на 8%, а в 2010 году — на 9% по сравнению с 2009 годом. "
        "Сколько человек стало проживать в квартале в 2010 году?"
    )
    context = _context_with_existing_solution(condition)
    context["normalized_content"]["sections"][-1]["html"] = (
        '<p>В 2009 году число жи\u00adте\u00adлей стало <span data-inline-latex="40000+0{,}08\\cdot 40000=43200"></span>  '
        'че\u00adло\u00adвек, а в 2010 году число жи\u00adте\u00adлей стало <span data-inline-latex="43200+0{,}09\\cdot 43200=47088"></span> че\u00adло\u00adвек.</p>'
    )

    plan = population_plan(context)

    assert any(item["transformation_target_id"] == "section:solution" for item in plan.transformations)


def test_population_growth_replaces_its_first_table_version() -> None:
    condition = (
        "В 2008 году в городском квартале проживало 40000 человек. В 2009 году, в результате строительства новых домов, "
        "число жителей выросло на 8%, а в 2010 году — на 9% по сравнению с 2009 годом. "
        "Сколько человек стало проживать в квартале в 2010 году?"
    )
    context = _context_with_existing_solution(condition)
    context["normalized_content"]["sections"][-1]["html"] = (
        '<p>Если величина изменяется на <span data-inline-latex="r\\%"></span> каждый год в течение '
        '<span data-inline-latex="n"></span> лет, её можно найти по формуле '
        '<span data-inline-latex="S\\left(1\\pm\\frac{r}{100}\\right)^n"></span>: знак «+» используют '
        'при увеличении, знак «−» — при уменьшении.</p><p>Здесь проценты за годы различаются, поэтому считаем последовательно.</p>'
        '<table><tbody><tr><th data-align="center">Год</th><th data-align="center">Число жителей</th></tr>'
        '<tr><td data-align="center">2008</td><td data-align="center">40000</td></tr>'
        '<tr><td data-align="center">2009</td><td data-align="center"><span data-inline-latex="40000\\cdot\\left(1+\\frac{8}{100}\\right)=43200"></span></td></tr>'
        '<tr><td data-align="center">2010</td><td data-align="center"><span data-inline-latex="43200\\cdot\\left(1+\\frac{9}{100}\\right)=47088"></span></td></tr>'
        '</tbody></table>'
    )

    plan = population_plan(context)

    assert any(item["transformation_target_id"] == "section:solution" for item in plan.transformations)


@pytest.mark.parametrize(("condition", "answer"), [
    ("В понедельник акции компании подорожали на некоторое количество процентов, а во вторник подешевели на то же самое количество процентов. В результате они стали стоить на 4% дешевле, чем при открытии торгов в понедельник. На сколько процентов подорожали акции компании в понедельник?", "20"),
    ("В среду акции компании подорожали на некоторое количество процентов, а в четверг подешевели на то же самое количество процентов. В результате они стали стоить на 64% дешевле, чем при открытии торгов в среду. На сколько процентов подорожали акции компании в среду?", "80"),
    ("В понедельник акции компании подорожали на некоторое число процентов, а во вторник подешевели на то же самое число процентов. В результате они стали стоить на 49% дешевле, чем при открытии торгов в понедельник. На сколько процентов подорожали акции компании в понедельник?", "70"),
    ("В четверг акции компании подорожали на некоторое количество процентов, а в пятницу подешевели на то же самое количество процентов. В результате они стали стоить на 36% дешевле, чем при открытии торгов в четверг. На сколько процентов подорожали акции компании в четверг?", "60"),
])
def test_equal_rise_and_fall_uses_equation_and_lifehack(condition: str, answer: str) -> None:
    plan = stock_plan(_context(condition))

    assert plan.answer == answer
    assert 'data-inline-latex="S\\left(1+\\frac{x}{100}\\right)' in plan.solution_html
    assert 'data-solution-title="ЛАЙФХАК"' in plan.solution_html
    assert "берём единственное число" in plan.solution_html
    assert "<p><b>ЛАЙФХАК</b></p>" not in plan.solution_html
    assert f'={answer}' in plan.solution_html


def test_equal_rise_and_fall_rejects_a_non_square_loss() -> None:
    with pytest.raises(UnsupportedCondition):
        stock_plan(_context(
            "В понедельник акции компании подорожали на некоторое количество процентов, а во вторник подешевели на то же самое количество процентов. В результате они стали стоить на 2% дешевле, чем при открытии торгов в понедельник. На сколько процентов подорожали акции компании в понедельник?"
        ))


def test_equal_rise_and_fall_rewrites_existing_solution_by_explicit_group_policy() -> None:
    condition = (
        "В понедельник акции компании подорожали на некоторое количество процентов, а во вторник подешевели на то же самое количество процентов. "
        "В результате они стали стоить на 4% дешевле, чем при открытии торгов в понедельник. "
        "На сколько процентов подорожали акции компании в понедельник?"
    )
    plan = stock_plan(_context_with_existing_solution(condition))

    assert any(item["transformation_target_id"] == "section:solution" for item in plan.transformations)


@pytest.mark.parametrize(("condition", "answer"), [
    ("Четыре одинаковые рубашки дешевле куртки на 8%. На сколько процентов пять таких же рубашек дороже куртки?", "15"),
    ("Семь одинаковых рубашек дешевле куртки на 2%. На сколько процентов десять таких же рубашек дороже куртки?", "40"),
    ("Одиннадцать одинаковых рубашек дешевле куртки на 1%. На сколько процентов тринадцать таких же рубашек дороже куртки?", "17"),
    ("Три одинаковые рубашки дешевле куртки на 10%. На сколько процентов четыре такие же рубашки дороже куртки?", "20"),
    ("Десятьодинаковых рубашек дешевле куртки на 4%. На сколько процентов пятнадцать таких же рубашек дороже куртки?", "44"),
    ("Шесть одинаковых рубашек дешевле куртки на 2%. На сколько процентов девять таких же рубашек дороже куртки?", "47"),
])
def test_shirt_jacket_keeps_parent_method_and_adds_hundred_ruble_alternative(condition: str, answer: str) -> None:
    plan = shirt_plan(_context(condition))

    assert plan.answer == answer
    assert 'data-solution-title="Приведем другое решение."' in plan.solution_html
    assert "Примем стоимость куртки за" in plan.solution_html
    assert 'data-inline-latex="100"' in plan.solution_html
    assert f'={answer}\\%' in plan.solution_html


def test_shirt_jacket_declines_count_words_in_solution_text() -> None:
    plan = shirt_plan(_context(
        "Четыре одинаковые рубашки дешевле куртки на 8%. На сколько процентов пять таких же рубашек дороже куртки?"
    ))

    assert "Стоимость четырёх рубашек" in plan.solution_html
    assert "Стоимость пяти рубашек" in plan.solution_html


def test_family_income_has_requested_system_method() -> None:
    plan = family_plan(_context("Семья состоит из мужа, жены и их дочери студентки. Если бы зарплата мужа увеличилась вдвое, общий доход семьи вырос бы на 67%. Если бы стипендия дочери уменьшилась втрое, общий доход семьи сократился бы на 4%. Сколько процентов от общего дохода семьи составляет зарплата жены?"))
    assert plan.answer == "27"
    assert 'М+Ж+Д=100' in plan.solution_html
    assert 'Поочередно вычтем из первого уравнения два других' in plan.solution_html
    assert 'Ж=100-67-6=27' in plan.solution_html


@pytest.mark.parametrize(("condition", "answer", "factor"), [
    ("Цена холодильника в магазине ежегодно уменьшается на одно и то же число процентов от предыдущей цены. Определите, на сколько процентов каждый год уменьшалась цена холодильника, если, выставленный на продажу за 20 000 рублей, через два года был продан за 15 842 рублей.", "11", r"\frac{7921}{10000}=\frac{89^2}{100^2}"),
    ("Цена холодильника в магазине ежегодно уменьшается на одно и то же число процентов от предыдущей цены. Определите, на сколько процентов каждый год уменьшалась цена холодильника, если, выставленный на продажу за 20 000 рублей, через четыре года был продан за 13 122 рубля.", "10", r"\frac{6561}{10000}=\frac{9^4}{10^4}"),
])
def test_refrigerator_price_decline_simplifies_the_fraction_before_subtracting_from_one(
    condition: str, answer: str, factor: str,
) -> None:
    plan = refrigerator_plan(_context(condition))

    assert plan.answer == answer
    assert factor in plan.solution_html
    assert r"\frac{p}{100}=1-" in plan.solution_html


def test_company_capital_profit_uses_two_requested_tables() -> None:
    plan = capital_plan(_context(
        "Митя, Антон, Гоша и Борис учредили компанию с уставным капиталом 200 000 рублей. Митя внес 14% уставного капитала, Антон — 42 000 рублей, Гоша — 0,12 уставного капитала, а оставшуюся часть капитала внес Борис. Учредители договорились делить ежегодную прибыль пропорционально внесенному в уставной капитал вкладу. Какая сумма от прибыли 1 000 000 рублей причитается Борису? Ответ дайте в рублях."
    ))

    assert plan.answer == "530000"
    assert plan.solution_html.count("<table>") == 2
    assert "Митя" in plan.solution_html and "Антон" in plan.solution_html
    assert r"\frac{42000}{200000}\cdot100\%=21\%" in plan.solution_html
    assert r"53\%\cdot1000000=530000" in plan.solution_html
    assert r"\frac{7}{50}\cdot200000" not in plan.solution_html
    assert plan.solution_html.index(r"\frac{42000}{200000}\cdot100\%=21\%") < plan.solution_html.rindex("<table>")
    assert plan.solution_html.index(r"53\%\cdot1000000=530000") < plan.solution_html.rindex("<table>")
    assert 'data-inline-latex="200000"' in plan.solution_html
    assert "<b>Антон:</b>" in plan.solution_html
    assert "<b>Гоша:</b>" in plan.solution_html
    assert "<b>Борис:</b>" in plan.solution_html
    assert "<b>Митя:</b>" in plan.solution_html and "— дано по условию. Следовательно," in plan.solution_html
    assert "<center>" not in plan.solution_html
    assert plan.solution_html.index("<b>Дроби</b>") < plan.solution_html.index("<b>Проценты</b>")


def test_company_capital_profit_keeps_a_repeating_percentage_as_a_fraction() -> None:
    plan = capital_plan(_context(
        "Дима, Артем, Гриша и Вова учредили компанию с уставным капиталом 150000 рублей. Дима внес 17% уставного капитала, Артем — 50000 рублей, Гриша — 0,24 уставного капитала, а оставшуюся часть капитала внес Вова. Учредители договорились делить ежегодную прибыль пропорционально внесенному в уставной капитал вкладу. Какая сумма от прибыли 900000 рублей причитается Вове? Ответ дайте в рублях."
    ))

    assert plan.answer == "231000"
    assert r"\frac{100}{3}\%" in plan.solution_html


def test_generated_bookcase_solution_uses_latex_spans_not_visible_tex_commands() -> None:
    plan = bookcase_plan(_context(
        "В университетскую библиотеку привезли новые учебники по геометрии для 3 курсов, по 360 штук для каждого курса. Все книги одинаковы по размеру. В книжном шкафу 9 полок, на каждой полке помещается 25 учебников. Сколько шкафов можно полностью заполнить новыми учебниками?"
    ))

    assert 'data-inline-latex="360\\cdot 3=1080"' in plan.solution_html
    assert "учебников 360\\cdot" not in plan.solution_html


def test_replaces_only_the_exact_legacy_bookcase_html_emitted_by_this_runner() -> None:
    condition = "В университетскую библиотеку привезли новые учебники по геометрии для 3 курсов, по 360 штук для каждого курса. Все книги одинаковы по размеру. В книжном шкафу 9 полок, на каждой полке помещается 25 учебников. Сколько шкафов можно полностью заполнить новыми учебниками?"
    context = _context_with_existing_solution(condition)
    context["normalized_content"]["sections"][-1]["html"] = (
        "<p>Всего привезли 360\\cdot 3=1080 учебников.</p>"
        "<p>В одном книжном шкафу помещается 25\\cdot 9=225 учебников.</p>"
        "<p>Разделим 1080 на 225: полностью можно заполнить 4 шкафов.</p>"
    )

    plan = bookcase_plan(context)

    assert any(item["transformation_target_id"] == "section:solution" for item in plan.transformations)


def test_medicine_solution_keeps_the_parent_division_layout() -> None:
    plan = medicine_plan(_context(
        "Больному прописано лекарство, которое нужно пить по 0,5 г 3 раза в день в течение 21 дня. В одной упаковке 10 таблеток лекарства по 0,5 г. Какого наименьшего количества упаковок хватит на весь курс лечения?"
    ))

    assert plan.answer == "7"
    assert 'data-inline-latex="\\frac{31{,}5}{5}=\\frac{315}{50}=\\frac{315\\cdot 2}{50\\cdot 2}=\\frac{630}{100}=6{,}3"' in plan.solution_html
    assert "Разделим 31,5 на 5:" in plan.solution_html
    assert "Разделим 31{,}5" not in plan.solution_html
    assert "7 упаковок" in plan.solution_html


def test_medicine_accepts_an_empty_condition_tag_and_missing_period() -> None:
    context = _context(
        "Больному прописано лекарство, которое нужно пить по 0.25 г 3 раза в день в течение 7 дней. В одной упаковке 10 таблеток лекарства по 0.25 г Какого наименьшего количества упаковок хватит на весь курс лечения?"
    )
    context["normalized_content"]["sections"][0]["html"] = (
        "<p><b></b>Больному прописано лекарство, которое нужно пить по 0.25 г 3 раза в день в течение 7 дней. В одной упаковке 10 таблеток лекарства по 0.25 г Какого наименьшего количества упаковок хватит на весь курс лечения?</p>"
    )

    assert medicine_plan(context).answer == "3"


def test_medicine_keeps_a_nonterminating_quotient_as_a_fraction() -> None:
    plan = medicine_plan(_context(
        "Больному прописано лекарство, которое нужно пить по 0,25 г 2 раза в день в течение 20 дней. В одной упаковке 12 таблеток лекарства по 0,25 г. Какого наименьшего количества упаковок хватит на весь курс лечения?"
    ))

    assert plan.answer == "4"
    assert 'data-inline-latex="\\frac{10}{3}=3{,}(3)"' in plan.solution_html


def test_medicine_replaces_only_its_exact_legacy_visible_latex_output() -> None:
    condition = (
        "Больному прописано лекарство, которое нужно пить по 0,5 г 3 раза в день в течение 21 дня. "
        "В одной упаковке 8 таблеток лекарства по 0,5 г. "
        "Какого наименьшего количества упаковок хватит на весь курс лечения?"
    )
    context = _context_with_existing_solution(condition)
    context["normalized_content"]["sections"][-1]["html"] = (
        '<p>Больному нужно принять <span data-inline-latex="0{,}5\\cdot 3\\cdot 21=31{,}5"></span> г лекарства. '
        'В одной упаковке содержится <span data-inline-latex="0{,}5\\cdot 8=4"></span> г лекарства. Разделим 31{,}5 на 4:</p>'
        '<center><p><span data-inline-latex="\\frac{31{,}5}{4}=\\frac{315}{40}=\\frac{280+35}{40}=\\frac{280}{40}+\\frac{7}{8}=7{,}875"></span>.</p></center>'
        "<p>Значит, на курс лечения необходимо 8 упаковок.</p>"
    )

    plan = medicine_plan(context)

    assert any(item["transformation_target_id"] == "section:solution" for item in plan.transformations)
    assert "Разделим 31,5 на 4:" in plan.solution_html
    assert '\\frac{315}{40}=\\frac{315\\cdot 25}{40\\cdot 25}=\\frac{7875}{1000}=7{,}875' in plan.solution_html


def test_population_growth_uses_formula_preface_and_year_table() -> None:
    condition = (
        "В 2008 году в городском квартале проживало 40000 человек. В 2009 году, в результате строительства новых домов, "
        "число жителей выросло на 8%, а в 2010 году — на 9% по сравнению с 2009 годом. "
        "Сколько человек стало проживать в квартале в 2010 году?"
    )
    context = _context(condition)
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В 2008 году в городском квартале проживало 40000 человек. В 2009 году, в результате строительства новых домов, '
        'число жителей выросло на 8%, а в 2010 году — на 9% по сравнению с 2009 годом. '
        'Сколько человек стало проживать в квартале в 2010 году?</p>'
    )

    plan = population_plan(context)

    assert plan.answer == "47088"
    assert 'data-inline-latex="S\\left(1\\pm\\frac{r}{100}\\right)^n"' in plan.solution_html
    assert "Здесь проценты за годы различаются, поэтому считаем последовательно." in plan.solution_html
    assert "<table>" in plan.solution_html
    assert "2008" in plan.solution_html
    assert 'data-inline-latex="40000"' in plan.solution_html
    assert 'data-cell-tone="source-header"' in plan.solution_html
    assert 'data-valign="middle"' in plan.solution_html
    assert 'data-inline-latex="40000\\cdot\\left(1+\\frac{8}{100}\\right)=43200"' in plan.solution_html
    assert 'data-inline-latex="43200\\cdot\\left(1+\\frac{9}{100}\\right)=47088"' in plan.solution_html


def test_population_growth_accepts_inline_formula_markup_and_preserves_editorial_solution() -> None:
    condition = (
        "В 2008 году в городском квартале проживало 40000 человек. В 2009 году, в результате строительства новых домов, "
        "число жителей выросло на 8%, а в 2010 году — на 9% по сравнению с 2009 годом. "
        "Сколько человек стало проживать в квартале в 2010 году?"
    )
    context = _context_with_existing_solution(condition)
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В 2008 году в городском квартале проживало <span data-inline-latex="40000"></span> человек. '
        '<nobr>В 2009 году,</nobr> в результате строительства новых домов, число жителей выросло на '
        '<span data-inline-latex="8\\%"></span>, а в <nobr>2010 году</nobr> на '
        '<span data-inline-latex="9\\%"></span> по сравнению с <nobr>2009 годом.</nobr> '
        'Сколько человек стало проживать в квартале в <nobr>2010 году?</nobr></p>'
    )

    plan = population_plan(context)

    assert plan.answer == "47088"
    assert not any(item["transformation_target_id"] == "section:solution" for item in plan.transformations)
