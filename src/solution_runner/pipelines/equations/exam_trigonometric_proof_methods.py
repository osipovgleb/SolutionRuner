"""Choose the reviewed parent method without changing the shared rendering."""

from .exam_trigonometric_compile import C, S, T, U


def method_proof(a):
    if a.square_difference is not None:
        from .exam_trigonometric_square_difference import proof

        return proof(a)
    if a.symmetric is not None:
        from .exam_trigonometric_symmetric_proof import proof

        return proof(a)
    if a.angle_product is not None:
        from .exam_trigonometric_angle_product import proof

        return proof(a)
    if (
        len(a.branches) == 2
        and {b.variable for b in a.branches} == {S, C}
        and any(b.grouping for b in a.branches)
    ):
        from .exam_trigonometric_grouping import pure_proof

        return pure_proof(a)
    if a.affine is not None:
        from .exam_trigonometric_affine_proof import proof

        return proof(a)
    if len(a.branches) > 1 and all(
        b.original is not None and not b.impossible for b in a.branches
    ):
        from .exam_trigonometric_grouping import proof

        return proof(a)
    if a.homogeneous is not None:
        from .exam_trigonometric_homogeneous_proof import proof

        return proof(a)
    if any(b.impossible for b in a.branches):
        from .exam_trigonometric_combination import proof

        return proof(a)
    if a.absolute is not None:
        from .exam_trigonometric_absolute import proof

        return proof(a)
    if a.translation:
        from .exam_trigonometric_translation import proof

        return proof(a)
    if a.strict_domain:
        from .exam_trigonometric_radical_quotient import proof

        return proof(a)
    if a.fraction is not None:
        from .exam_trigonometric_rational import proof

        return proof(a)
    if a.domain is not None:
        from .exam_trigonometric_domain import proof

        return proof(a)
    if a.preferred == T:
        if any(b.variable != T for b in a.branches):
            return None
        from .exam_trigonometric_ratios import tangent_proof

        return tangent_proof(a)
    if a.poles and a.reciprocal is None:
        from .exam_trigonometric_poles import proof

        return proof(a)
    if a.scale != 1 or a.reciprocal is not None or a.division:
        from .exam_trigonometric_variants import proof

        return proof(a)
    if a.preferred == U:
        from .exam_trigonometric_ratios import cotangent_proof

        return cotangent_proof(a)
    return None
