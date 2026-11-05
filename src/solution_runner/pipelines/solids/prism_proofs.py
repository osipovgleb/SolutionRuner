"""Render the reviewed prism method for the actual child's target and figure role."""

from . import prism_measurement_proofs as measured
from . import prism_metric_proofs as metrics
from . import prism_oblique_proofs as oblique
from . import prism_ratio_proofs as ratios
from . import prism_region_proofs as regions
from . import prism_section_proofs as sections
from . import prism_water_proofs as water
from .prism_metric_model import KINDS as METRIC_KINDS
from .prism_model import MEASUREMENTS
from .prism_region import KIND as REGION_KIND


def render(m, pictures):
    if m.kind in {"oblique_rhombus", "oblique_hex"}:
        return oblique.render(m, "".join(pictures.values()))
    prefix = "".join("<p>" + p + "</p>" for p in pictures.values())
    if m.kind == "immersion":
        return prefix + water.render(m)
    if m.kind == REGION_KIND:
        return prefix + regions.render(m)
    if m.kind in METRIC_KINDS:
        return prefix + metrics.render(m)
    if m.kind in MEASUREMENTS:
        return prefix + measured.render(m)
    if m.kind in sections.METHODS:
        return prefix + sections.render(m)
    return prefix + ratios.render(m)
