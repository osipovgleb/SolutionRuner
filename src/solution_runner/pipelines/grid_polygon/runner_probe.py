"""Find existing deterministic content rules that may fit one answered task."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import getpass
from html import unescape
import json
import os
import re
from typing import Any, Callable, Iterable, Mapping, Protocol

from bs4 import BeautifulSoup

from ..core.group_profiles import all_group_profiles
from .mcp_runtime import DEFAULT_MCP_URL, JsonRpcMcpGateway
from ..core.models import GroupProfile


class RunnerProbeError(RuntimeError):
    """Report invalid single-task input without treating it as a runner miss."""


class ProbeGateway(Protocol):
    """Expose the two read-only operations used by the probe."""

    def find_source_catalog_path(
        self, catalog_snapshot_id: str, source_id: str, target_type: str
    ) -> dict[str, Any]: ...

    def get_problem_context(self, problem_id: str) -> dict[str, Any]: ...


PlanBuilder = Callable[..., Any]


@dataclass(frozen=True)
class RunnerCandidate:
    """Describe one answer-matching rule without claiming full compatibility."""

    content_rule_key: str
    registered_groups: tuple[str, ...]
    computed_answer: str


@dataclass(frozen=True)
class RunnerRejection:
    """Keep one compact reason why a strict rule did not accept the task."""

    content_rule_key: str
    reason: str


@dataclass(frozen=True)
class ProbeReport:
    """Summarize one read-only pass over unique registered content rules."""

    problem_id: str
    source_problem_id: str | None
    stored_answer: str
    unique_rules_tried: int
    registered_content_profiles: int
    skipped_geometry_profiles: int
    answer_mismatches: int
    candidates: tuple[RunnerCandidate, ...]
    rejections: tuple[RunnerRejection, ...]


def _normalized_content(context: Mapping[str, Any]) -> Mapping[str, Any]:
    content = context.get("normalized_content")
    if (
        not isinstance(content, Mapping)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RunnerProbeError("schema-v3 Normalized content is required")
    return content


def _unique_section(content: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    sections = content.get("sections")
    matches = [
        item
        for item in (sections if isinstance(sections, list) else [])
        if isinstance(item, Mapping) and item.get("key") == key
    ]
    if len(matches) > 1:
        raise RunnerProbeError(f"task has multiple {key!r} sections")
    return matches[0] if matches else None


def _answer_text(section: Mapping[str, Any]) -> str:
    soup = BeautifulSoup(str(section.get("html") or ""), "html.parser")
    for element in soup.find_all(attrs={"data-inline-latex": True}):
        element.replace_with(str(element.get("data-inline-latex") or ""))
    return unescape(soup.get_text(" ", strip=True)).strip()


def stored_answer(context: Mapping[str, Any]) -> str:
    """Return the required non-empty answer from exactly one task context."""

    answer = _unique_section(_normalized_content(context), "answer")
    value = _answer_text(answer) if answer is not None else ""
    if not value:
        raise RunnerProbeError("the selected task has no stored answer")
    return value


def _canonical_answer(value: object) -> tuple[str, object]:
    text = unescape(str(value)).strip()
    text = text.replace("−", "-").replace("–", "-")
    text = re.sub(r"^\s*(?:ответ\s*[:=]\s*)", "", text, flags=re.IGNORECASE)
    text = text.replace("{,}", ".").replace(",", ".")
    text = re.sub(r"\\(?:left|right)", "", text)
    text = re.sub(r"\\(?:,|;|!|quad|qquad)", "", text)
    text = re.sub(r"(?:\^\{?\\circ\}?|°)", "", text)
    text = text.strip().rstrip(".;")
    compact = re.sub(r"\s+", "", text)
    decimal_match = re.fullmatch(r"[+-]?\d+(?:\.\d+)?", compact)
    if decimal_match:
        try:
            return "number", Decimal(compact).normalize()
        except InvalidOperation:
            pass
    fraction_match = re.fullmatch(
        r"\\frac\{([+-]?\d+)\}\{([+-]?\d+)\}|([+-]?\d+)\/([+-]?\d+)",
        compact,
    )
    if fraction_match:
        numerator = int(fraction_match.group(1) or fraction_match.group(3))
        denominator = int(fraction_match.group(2) or fraction_match.group(4))
        if denominator:
            from fractions import Fraction

            return "number", Fraction(numerator, denominator)
    compact = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", compact)
    compact = re.sub(r"√\s*\(?([^()\s]+)\)?", r"sqrt(\1)", compact)
    return "text", compact.casefold()


def answers_match(stored: object, computed: object) -> bool:
    """Compare common numeric/LaTeX answer forms without evaluating code."""

    left = _canonical_answer(stored)
    right = _canonical_answer(computed)
    if left[0] == "number" and right[0] == "number":
        return left[1] == right[1]
    return left == right


def _rule_groups(
    profiles: Iterable[GroupProfile],
) -> tuple[dict[str, tuple[str, ...]], int, int]:
    groups: dict[str, list[str]] = {}
    content_profiles = 0
    geometry_profiles = 0
    for profile in profiles:
        if profile.workflow_kind != "content_rule" or not profile.content_rule_key:
            geometry_profiles += 1
            continue
        content_profiles += 1
        groups.setdefault(profile.content_rule_key, []).append(profile.group_key)
    return (
        {key: tuple(sorted(values)) for key, values in sorted(groups.items())},
        content_profiles,
        geometry_profiles,
    )


def _probe_parent_asset_id(context: Mapping[str, Any]) -> str | None:
    assets = _normalized_content(context).get("assets")
    matches = [
        str(item.get("asset_id"))
        for item in (assets if isinstance(assets, list) else [])
        if isinstance(item, Mapping)
        and item.get("asset_key") == "image_1"
        and item.get("asset_id")
    ]
    return matches[0] if len(matches) == 1 else None


def _probe_solution_assets(context: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    content = _normalized_content(context)
    solution = _unique_section(content, "solution")
    keys = tuple(str(key) for key in (solution or {}).get("asset_keys", []) if key)
    assets = content.get("assets")
    by_key = {
        str(item.get("asset_key")): item
        for item in (assets if isinstance(assets, list) else [])
        if isinstance(item, Mapping) and item.get("asset_key") and item.get("asset_id")
    }
    return tuple(
        {
            "asset_key": key,
            "source_asset_id": str(by_key[key]["asset_id"]),
            "url": str(by_key[key].get("url") or f"/assets/{by_key[key]['asset_id']}"),
            "alt": str(by_key[key].get("alt") or ""),
        }
        for key in keys
        if key in by_key
    )


def _probe_solution_html(context: Mapping[str, Any]) -> str:
    solution = _unique_section(_normalized_content(context), "solution")
    return str(solution.get("html") or "") if solution is not None else ""


def _default_plan_builder(*args: Any, **kwargs: Any) -> Any:
    from ..core.content_runtime import _build_content_plan

    return _build_content_plan(*args, **kwargs)


def probe_context(
    context: Mapping[str, Any],
    *,
    problem_id: str,
    source_problem_id: str | None = None,
    profiles: Iterable[GroupProfile] | None = None,
    plan_builder: PlanBuilder = _default_plan_builder,
) -> ProbeReport:
    """Run one answered task through every unique registered content rule."""

    expected = stored_answer(context)
    selected_profiles = tuple((profiles or all_group_profiles().values()))
    rules, content_profiles, geometry_profiles = _rule_groups(selected_profiles)
    parent_asset_id = _probe_parent_asset_id(context)
    parent_solution_assets = _probe_solution_assets(context)
    parent_solution_html = _probe_solution_html(context)
    candidates: list[RunnerCandidate] = []
    rejections: list[RunnerRejection] = []
    mismatches = 0
    for rule, registered_groups in rules.items():
        try:
            plan = plan_builder(
                dict(context),
                parent_asset_id=parent_asset_id,
                content_rule_key=rule,
                parent_solution_assets=parent_solution_assets,
                parent_solution_html=parent_solution_html,
                current_asset_content_type="image/svg+xml",
            )
            computed = str(plan.answer)
        except Exception as exc:  # noqa: BLE001 - every strict parser is isolated.
            rejections.append(
                RunnerRejection(rule, " ".join(str(exc).split())[:300] or type(exc).__name__)
            )
            continue
        if answers_match(expected, computed):
            candidates.append(RunnerCandidate(rule, registered_groups, computed))
        else:
            mismatches += 1
    return ProbeReport(
        problem_id=problem_id,
        source_problem_id=source_problem_id,
        stored_answer=expected,
        unique_rules_tried=len(rules),
        registered_content_profiles=content_profiles,
        skipped_geometry_profiles=geometry_profiles,
        answer_mismatches=mismatches,
        candidates=tuple(candidates),
        rejections=tuple(rejections),
    )


def _resolved_problem_id(payload: Mapping[str, Any], source_problem_id: str) -> str:
    target = payload.get("target")
    if isinstance(target, Mapping):
        problem_id = str(target.get("id") or target.get("uuid") or "").strip()
        resolved_source = str(target.get("source_id") or "").strip()
        if not problem_id:
            raise RunnerProbeError("source problem lookup omitted the internal problem id")
        if resolved_source and resolved_source != source_problem_id:
            raise RunnerProbeError("source problem lookup returned a different task")
        return problem_id

    matches = payload.get("matches")
    exact = []
    for item in matches if isinstance(matches, list) else []:
        problem = item.get("problem") if isinstance(item, Mapping) else None
        name = str(problem.get("name") or "") if isinstance(problem, Mapping) else ""
        if re.fullmatch(rf"\s*Задача\s+{re.escape(source_problem_id)}\s*", name):
            exact.append(problem)
    if len(exact) != 1:
        raise RunnerProbeError("source problem lookup did not return one exact task")
    problem_id = str(exact[0].get("uuid") or exact[0].get("id") or "").strip()
    if not problem_id:
        raise RunnerProbeError("source problem lookup omitted the internal problem id")
    return problem_id


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--problem-id", help="internal problem UUID")
    selector.add_argument("--source-problem-id", help="visible source task number")
    parser.add_argument(
        "--confirm-catalog",
        help="required with --source-problem-id to make lookup scope explicit",
    )
    parser.add_argument("--json", action="store_true", help="emit the complete JSON report")
    parser.add_argument(
        "--show-rejections",
        action="store_true",
        help="show compact strict-parser rejection reasons",
    )
    return parser


def _api_key() -> str:
    value = os.environ.get("TEACHERHELPER_MCP_API_KEY", "").strip()
    return value or getpass.getpass("TEACHERHELPER_MCP_API_KEY: ").strip()


def _print_report(report: ProbeReport, *, show_rejections: bool) -> None:
    label = report.source_problem_id or report.problem_id
    print(f"TASK {label}  STORED ANSWER {report.stored_answer}")
    print(
        "TRIED "
        f"{report.unique_rules_tried} UNIQUE CONTENT RULES  "
        f"CANDIDATES {len(report.candidates)}  "
        f"ANSWER MISMATCHES {report.answer_mismatches}  "
        f"STRICT REJECTIONS {len(report.rejections)}"
    )
    print(f"SKIPPED GEOMETRY PROFILES {report.skipped_geometry_profiles}")
    if not report.candidates:
        print("NO THEORETICAL CANDIDATES")
    for candidate in report.candidates:
        groups = ",".join(candidate.registered_groups)
        print(
            f"CANDIDATE {candidate.content_rule_key}  "
            f"GROUPS {groups}  COMPUTED ANSWER {candidate.computed_answer}"
        )
    if show_rejections:
        for rejection in report.rejections:
            print(f"REJECTED {rejection.content_rule_key}  {rejection.reason}")
    print("RESULT IS HEURISTIC: verify condition grammar, method, assets, and solution style.")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.source_problem_id and not args.confirm_catalog:
        parser.error("--source-problem-id requires --confirm-catalog")
    if args.problem_id and args.confirm_catalog:
        parser.error("--confirm-catalog is only valid with --source-problem-id")
    gateway = JsonRpcMcpGateway(
        url=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
        api_key=_api_key(),
    )
    try:
        problem_id = str(args.problem_id or "")
        source_problem_id = str(args.source_problem_id or "") or None
        if source_problem_id is not None:
            problem_id = _resolved_problem_id(
                gateway.find_source_catalog_path(
                    str(args.confirm_catalog), source_problem_id, "problem"
                ),
                source_problem_id,
            )
        context = gateway.get_problem_context(problem_id)
        report = probe_context(
            context,
            problem_id=problem_id,
            source_problem_id=source_problem_id,
        )
    except RunnerProbeError as exc:
        parser.error(str(exc))
    finally:
        gateway.close()
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        _print_report(report, show_rejections=args.show_rejections)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
