from fractions import Fraction

import pytest

from solution_runner.pipelines.probability.coins import CoinCase
from solution_runner.pipelines.probability.coins import outcomes as coin_outcomes
from solution_runner.pipelines.probability.coins import parse as parse_coin
from solution_runner.pipelines.probability.coins import render as render_coin
from solution_runner.pipelines.probability.common import (
    count,
    probability,
    require_content,
    rounded,
)
from solution_runner.pipelines.probability.counting import solve as solve_counting
from solution_runner.pipelines.probability.dice import DiceCase
from solution_runner.pipelines.probability.dice import outcomes as dice_outcomes
from solution_runner.pipelines.probability.integer_outcomes import (
    solve as solve_integer,
)
from solution_runner.pipelines.probability.rates import solve as solve_rates


@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [
        (Fraction(1, 200), 2, "0,01"),
        (Fraction(199, 200), 2, "1,00"),
        (Fraction(1, 270), 3, "0,004"),
        (Fraction(1, 60), 3, "0,017"),
    ],
)
def test_rounding_is_exact_school_half_up(value, places, expected):
    assert rounded(value, places) == expected


@pytest.mark.parametrize(
    ("token", "expected"),
    [("одного", 1), ("восемь", 8), ("двадцать одна", 21), ("21", 21)],
)
def test_audited_digit_and_word_counts(token, expected):
    assert count(token) == expected


@pytest.mark.parametrize("token", ["один два", "двадцать тридцать", "0 одна", "-1"])
def test_ambiguous_or_unsupported_word_counts_are_rejected(token):
    with pytest.raises(ValueError):
        count(token)


@pytest.mark.parametrize(("m", "n"), [(-1, 10), (11, 10), (0, 0)])
def test_invalid_probability_counts_fail_closed(m, n):
    with pytest.raises(ValueError):
        probability(m, n)


@pytest.mark.parametrize(("m", "n", "decimal_fraction"), [
    (42, 48, r"\frac{875}{1000}"),
    (57, 60, r"\frac{95}{100}"),
    (36, 45, r"\frac{8}{10}"),
])
def test_combined_probability_shows_decimal_denominator(m, n, decimal_fraction):
    _, html = probability(m, n, combine_steps=True)
    assert decimal_fraction in html


def test_rounded_probability_does_not_claim_exact_decimal_equivalence():
    _, html = probability(1, 3, 2, combine_steps=True)
    assert r"\frac{33}{100}" not in html
    assert r"\approx" in html


def test_two_dice_use_ordered_pairs_and_the_correct_sum_distribution():
    counts = [
        len(dice_outcomes(DiceCase(2, "sum", total))[1]) for total in range(2, 13)
    ]
    assert counts == [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
    assert len(dice_outcomes(DiceCase(2, "sum", 1))[1]) == 0


def test_conditional_dice_counts_are_restricted_to_the_conditioning_event():
    domain, favorable = dice_outcomes(DiceCase(3, "contains", 3, conditional_sum=6))
    assert len(domain) == 10
    assert len(favorable) == 6
    assert all(sum(row) == 6 for row in domain)
    with pytest.raises(ValueError):
        dice_outcomes(DiceCase(3, "contains", 3, conditional_sum=1))


@pytest.mark.parametrize(
    ("kind", "k", "side", "expected"),
    [
        ("exact", 2, 1, 3),
        ("at-least", 2, 0, 4),
        ("at-most", 1, 1, 4),
        ("majority", 0, 0, 4),
    ],
)
def test_coin_counting_handles_both_sides_and_inequality_events(
    kind, k, side, expected
):
    assert len(coin_outcomes(CoinCase(3, kind, k, side))[1]) == expected


def test_a_fixed_coin_sequence_is_not_multiplied_by_a_binomial_coefficient():
    case = CoinCase(3, "sequence", 0, sequence=(1, 0, 0))
    answer, html = render_coin(case, "<p>Формула Бернулли</p>")
    assert answer == "0,125"
    assert "C_{3}^{1}" not in html
    assert "порядок фиксирован" in html


def test_contradictory_coin_sequence_description_fails_closed():
    with pytest.raises(ValueError):
        parse_coin(
            "В случайном эксперименте симметричную монету бросают дважды. Найдите вероятность того, что наступит исход ОР (оба раза выпадет решка)."
        )


def test_total_and_quality_subtotal_have_different_denominators():
    total = "Фабрика выпускает сумки. В среднем 8 сумок из 100 имеют скрытые дефекты. Найдите вероятность того, что купленная сумка окажется без дефектов."
    parts = "Фабрика выпускает сумки. В среднем на 100 качественных сумок приходится восемь сумок со скрытыми дефектами. Найдите вероятность того, что купленная сумка окажется качественной. Результат округлите до сотых."
    assert solve_counting(total)[0] == "0,92"
    assert solve_counting(parts)[0] == "0,93"


def test_clock_wraps_forward_across_twelve_and_rejects_an_ambiguous_full_turn():
    prefix = "Механические часы с двенадцатичасовым циферблатом в какой-то момент сломались и перестали идти. Найдите вероятность того, что часовая стрелка остановилась, достигнув отметки "
    assert solve_integer(prefix + "10, но не дойдя до отметки 1.")[0] == "0,25"
    with pytest.raises(ValueError):
        solve_integer(prefix + "4, но не дойдя до отметки 4.")


def test_frequency_difference_is_an_absolute_difference():
    text = "Вероятность того, что новый ноутбук в течение года поступит в гарантийный ремонт, равна 0,091. В некотором городе из 1000 проданных ноутбуков в течение года в гарантийную мастерскую поступило 80 штук. На сколько отличается частота события «гарантийный ремонт» от его вероятности в этом городе?"
    assert solve_rates(text)[0] == "0,011"


@pytest.mark.parametrize(
    "html",
    [
        '<p style="display:none">не</p>',
        '<p><b class="hidden">не</b></p>',
        '<p><img src="/asset"/></p>',
    ],
)
def test_unknown_markup_is_not_silently_discarded(html):
    context = {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [{"key": "condition", "html": html}],
        }
    }
    with pytest.raises(ValueError):
        require_content(context)


def test_last_helicopter_flight_counts_only_occupied_places():
    prefix = "В группе туристов 14 человек. Их вертолетом в несколько приемов забрасывают в труднодоступный район по 6 человек за рейс. Порядок, в котором вертолет перевозит туристов, случаен. Найдите вероятность того, что турист А. полетит "
    from solution_runner.pipelines.probability.selection_counts import parse

    assert parse(prefix + "последним рейсом вертолета.")[:2] == (14, 2)
    with pytest.raises(ValueError):
        parse(prefix + "четвертым рейсом вертолета.")


@pytest.mark.parametrize(
    ("key", "old", "new"),
    [
        ("320170", "1, 1, 1, 1", "1, 1, 1, 2"),
        ("672740", "100 шариков", "101 шариков"),
        ("285928", "из Парагвая.", "из Китая."),
        ("285925", "26 бадминтонистов", "25 бадминтонистов"),
        ("285922", "75 докладов", "76 докладов"),
        ("500037", "по восьми игровым", "по семи игровым"),
    ],
)
def test_inconsistent_counts_and_unknown_requested_categories_fail_closed(
    key, old, new
):
    import json
    from pathlib import Path

    from solution_runner.pipelines.probability.common import normalize

    data = json.loads((Path(__file__).parent / "fixtures/category_4.json").read_text())
    case = next(c for c in data["cases"] if c["task"] == key)
    text = normalize(require_content(case["context"])[-1])
    assert old in text
    with pytest.raises(ValueError):
        solve_counting(new.join(text.rsplit(old, 1)))


@pytest.mark.parametrize("n", range(3, 9))
@pytest.mark.parametrize(
    "event",
    [
        "девочки будут сидеть рядом",
        "девочки не будут сидеть рядом",
        "между девочками будет сидеть один мальчик",
    ],
)
def test_circular_seating_agrees_with_independent_pairs_of_chairs(n, event):
    from itertools import combinations

    from solution_runner.pipelines.probability.circular_counts import parse

    text = f"За круглый стол на {n} стульев в случайном порядке рассаживаются {n - 2} мальчиков и 2 девочки. Найдите вероятность того, что {event}."
    total, favorable, _, _ = parse(text)
    pairs = list(combinations(range(n), 2))

    def suitable(pair):
        a, b = pair
        adjacent = (b - a) in (1, n - 1)
        if event.startswith("между"):
            return (b - a) in (2, n - 2)
        return not adjacent if "не будут" in event else adjacent

    assert Fraction(favorable, total) == Fraction(sum(map(suitable, pairs)), len(pairs))


@pytest.mark.parametrize(("n", "groups"), [(6, 2), (6, 3), (8, 2), (8, 4), (9, 3)])
def test_friends_same_group_probability_agrees_with_all_group_memberships(n, groups):
    from itertools import combinations

    from solution_runner.pipelines.probability.arrangement_counts import parse

    size = n // groups
    text = f"В классе {n} учащихся, среди них два друга — Андрей и Сергей. Класс случайным образом разбивают на {groups} равные группы. Найдите вероятность того, что Андрей и Сергей окажутся в одной группе."
    total, favorable, html, _ = parse(text)
    companions = list(combinations(range(1, n), size - 1))
    assert Fraction(favorable, total) == Fraction(
        sum(1 in row for row in companions), len(companions)
    )
    assert all(f"Способ {i}." in html for i in range(1, 6))


def test_festival_orders_use_distinct_labels_even_for_equal_country_initials():
    from solution_runner.pipelines.probability.arrangement_counts import parse

    text = "На рок-фестивале выступают группы — по одной от каждой из заявленных стран. Порядок выступления определяется жребием. Какова вероятность того, что группа из Китая будет выступать после группы из Канады и после группы из Англии?"
    total, favorable, html, _ = parse(text)
    assert (total, favorable) == (6, 2)
    assert "1 — группа из Китая" in html and "2 — группа из Канады" in html
    with pytest.raises(ValueError):
        parse(text.replace("из Канады", "из Китая"))
