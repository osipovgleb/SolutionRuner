"""Read-only reproduction of one parent's transformation materialization."""
import os
import sys
from pathlib import Path
from io import StringIO
import json

sys.path.insert(0, "/Users/a1/projects/SolutionRuner/src")
sys.path.insert(0, "/Users/a1/projects/TeacherHelper/backend")
from solution_runner.pipelines.grid_polygon.mcp_runtime import JsonRpcMcpGateway, DEFAULT_MCP_URL
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.solution_asset_repair import _discover_group_records
from solution_runner.pipelines.grid_polygon.solution_runtime import _SolutionContext, _diagram_uploads
from solution_runner.pipelines.grid_polygon.solution_plan import build_solution_plan
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy
from solution_runner.pipelines.grid_polygon.progress import ProgressReporter
from app.services.normalized_html_content_problem_normalization import build_problem_normalization_working_document
from app.services.problem_content_transformations import upsert_problem_transformation, materialize_problem_transformations
from app.services.normalized_html_content import validate_normalized_content

profile = get_group_profile(sys.argv[1])
target = next(x for x in _discover_group_records(Path("var/grid-polygon/runs"), profile) if x.source_problem_id == sys.argv[1])
gateway = JsonRpcMcpGateway(url=DEFAULT_MCP_URL, api_key=os.environ["TEACHERHELPER_MCP_API_KEY"])
context = gateway.get_problem_context(target.problem_id)
parsed = gateway._call("get_problem_parsed_content", {"problem_id": target.problem_id}, read_only=True)
print("PARSED KEYS", list(parsed))
strategy = get_solution_strategy(profile.strategy_key)
analysis = strategy.analyze(target, profile)
runtime = _SolutionContext(gateway, profile, strategy, ProgressReporter(console=StringIO(), internal=StringIO(), color=False), False, 1)
uploads = _diagram_uploads(runtime, target, analysis, context["normalized_content"])
plan = build_solution_plan(context["normalized_content"], target, analysis, profile, strategy, uploads)
current = context["transformations"]
for item in plan.transformations:
    current = upsert_problem_transformation(current, {**item, "by": {"type": "mcp"}, "at": "2026-09-12T12:00:00+00:00"})
base = build_problem_normalization_working_document(parsed["parsed_content"])
output = materialize_problem_transformations(base, current)
print(json.dumps({"plan": plan.transformations, "assets": output["assets"], "sections": [s for s in output["sections"] if s["key"] == "solution"], "validation": validate_normalized_content(output, validation_level="runtime")}, ensure_ascii=False, indent=2))
gateway.close()
