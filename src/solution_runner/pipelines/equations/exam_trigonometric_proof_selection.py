"""Choose and render the reviewed root-selection proof."""


def select_proof(a, image, selection_image, system_image):
    from .exam_trigonometric_affine_proof import selection as number_line_selection
    from .exam_trigonometric_neighbors import proof as neighbor_selection
    from .exam_trigonometric_proof import inequality_selection
    from .exam_trigonometric_selection import progressions
    from .exam_trigonometric_variants import selection_notes

    selectors = {
        "neighbors": neighbor_selection,
        "number_line": number_line_selection,
        "inequalities": inequality_selection,
        "progressions": progressions,
    }
    from .exam_trigonometric_finite_log import data_of

    if data_of(a) is not None:
        from .exam_trigonometric_bounded_log_proof import selection

        second = selection(a)
    elif a.global_radical is not None:
        from .exam_trigonometric_global_radical_proof import selection

        second = selection(a)
    elif a.log_polynomial is not None and a.log_polynomial.alternative_selection:
        from .exam_trigonometric_log_selection import selection

        second = selection(a, image)
    elif a.bounded_log is not None:
        from .exam_trigonometric_bounded_log_proof import selection

        second = selection(a)
    elif (
        a.radical_equation is not None
        and a.radical_equation.kind == "half_tangent"
        and any(b.is_Rational is not True for b in a.bounds[:2])
    ):
        from .exam_trigonometric_radical_proof import numeric_selection

        second = numeric_selection(a)
    elif a.selection_method in selectors:
        second = selectors[a.selection_method](a)
    else:
        from .exam_trigonometric_circle import selection_proof

        second = selection_proof(a, selection_image, paired=selection_image != image)
    second += selection_notes(a, system_image)
    return second
