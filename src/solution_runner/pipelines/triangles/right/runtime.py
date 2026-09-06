"""Compatibility alias: shared content orchestration now lives in core."""
import sys
from solution_runner.pipelines.core import content_runtime

sys.modules[__name__] = content_runtime
