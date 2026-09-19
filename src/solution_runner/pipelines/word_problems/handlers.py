"""Explicit handler declarations owned by the word-problems domain."""

from solution_runner.pipelines.core.handlers import HandlerSpec


HANDLERS = (
    HandlerSpec(
        "word-problem-26623-monthly-travel-pass-savings",
        "solution_runner.pipelines.word_problems.group_26623:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-77334-currency-purchase-rounding",
        "solution_runner.pipelines.word_problems.group_77334:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-506389-whole-item-purchase",
        "solution_runner.pipelines.word_problems.group_506389:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-26626-bundle-promotion",
        "solution_runner.pipelines.word_problems.group_26626:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-26637-odd-bouquet",
        "solution_runner.pipelines.word_problems.group_26637:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-26641-full-bookcases",
        "solution_runner.pipelines.word_problems.group_26641:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-26624-medicine-course-ceiling",
        "solution_runner.pipelines.word_problems.group_26624:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-323514-wallpaper-rolls-ceiling",
        "solution_runner.pipelines.word_problems.group_323514:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-99565-successive-population-change",
        "solution_runner.pipelines.word_problems.group_99565:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-99566-equal-rise-fall-percent",
        "solution_runner.pipelines.word_problems.group_99566:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "word-problem-99567-shirt-jacket-percent",
        "solution_runner.pipelines.word_problems.group_99567:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec("word-problem-99568-family-income-system", "solution_runner.pipelines.word_problems.group_99568:build_context_repair_plan", requires_parent_condition_asset=False),
    HandlerSpec("word-problem-99569-refrigerator-price-decline", "solution_runner.pipelines.word_problems.group_99569:build_context_repair_plan", requires_parent_condition_asset=False),
    HandlerSpec("word-problem-99570-company-capital-profit-tables", "solution_runner.pipelines.word_problems.group_99570:build_context_repair_plan", requires_parent_condition_asset=False),
)
