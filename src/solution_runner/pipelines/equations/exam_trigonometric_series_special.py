"""Select root series for equations with reviewed domain constraints."""


def _special_series(compiled, branches, residues, domain):
    from .exam_trigonometric_selection import (
        constrained_series,
        restricted_series,
        square_series,
    )

    if compiled.power_polynomial is not None:
        from .exam_trigonometric_power_polynomial_roots import series

        return series(compiled, branches, residues), False, False
    if compiled.original_quotient is not None:
        from .exam_trigonometric_original_quotients import series

        return series(compiled.original_quotient, branches), False, False
    if compiled.strict_quotient is not None:
        from .exam_trigonometric_compile import C
        from .exam_trigonometric_inverse import centred

        series = tuple(dict.fromkeys(s for b in branches for s in restricted_series(b)))
        if compiled.strict_quotient.variable == C:
            series = centred(series)
        return series, False, False
    if compiled.log_product is not None or compiled.log_polynomial is not None:
        from .exam_trigonometric_log_product import series as log_series

        return log_series(compiled, branches, residues), False, False

    constrained = constrained_series(compiled, branches, residues)
    if constrained is not None:
        return constrained
    if domain is not None and compiled.poles:
        from .exam_trigonometric_inverse import centred

        return (
            tuple(
                s
                for b in branches
                for item in (
                    square_series(b)
                    if compiled.radical_product is not None and b.square_level
                    else restricted_series(b)
                )
                for s in centred((item,))
            ),
            False,
            False,
        )

    return None
