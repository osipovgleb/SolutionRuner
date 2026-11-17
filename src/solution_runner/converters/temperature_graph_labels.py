"""Interpret OCR ticks and dates for temperature charts."""

import itertools
import re
from datetime import date


def recover_y_axis_labels(
    horizontal_lines: tuple[float, ...],
    ocr_tokens: tuple[str, ...],
) -> tuple[tuple[float, float], ...]:
    """Recover the monotone scale even when OCR omits some negative signs."""

    if len(horizontal_lines) != len(ocr_tokens):
        raise ValueError("OCR tick count does not match horizontal grid lines")
    observations: list[tuple[int, float, bool]] = []
    for index, token in enumerate(ocr_tokens):
        normalized = token.replace("−", "-").strip()
        match = re.search(r"\d+(?:[.,]\d+)?", normalized)
        if match is None:
            continue
        magnitude = float(match.group(0).replace(",", "."))
        observations.append((index, magnitude, "-" in normalized))
    if len(observations) < 3:
        raise ValueError("OCR produced fewer than three numeric y-axis ticks")
    candidates: list[tuple[tuple[int, int, float], float, float]] = []
    for step in (0.5, 1.0, 2.0):
        intercepts = {
            signed * magnitude + step * index
            for index, magnitude, _ in observations
            for signed in (-1.0, 1.0)
        }
        for intercept in intercepts:
            matches = 0
            signed_matches = 0
            residual = 0.0
            for index, magnitude, explicit_negative in observations:
                predicted = intercept - step * index
                error = abs(abs(predicted) - magnitude)
                if error <= 0.12 and (not explicit_negative or predicted < 0):
                    matches += 1
                    signed_matches += int(explicit_negative and predicted < 0)
                    residual += error
            candidates.append(((matches, signed_matches, -residual), intercept, step))
    score, intercept, step = max(candidates, key=lambda item: item[0])
    if score[0] < 3:
        raise ValueError("OCR ticks do not support a stable arithmetic scale")
    return tuple(
        (float(pixel_y), float(intercept - step * index))
        for index, pixel_y in enumerate(horizontal_lines)
    )


_MONTHS = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
_MONTH_NUMBERS = {name: index for index, name in enumerate(_MONTHS) if name}


def _plain_russian_text(value: str) -> str:
    """Normalize invisible source separators without altering visible letters."""

    return re.sub(r"\s+", " ", value.replace("­", "").replace(" ", " ")).strip().lower()


def requested_date_from_condition(condition_text: str) -> date:
    """Extract the one requested Russian calendar date from problem text."""

    normalized = _plain_russian_text(condition_text)
    matches = re.findall(
        r"\b(\d{1,2})\s+(" + "|".join(_MONTH_NUMBERS) + r")\b",
        normalized,
    )
    if len(matches) != 1:
        raise ValueError("condition must contain exactly one requested date")
    day, month = matches[0]
    return date(2000, _MONTH_NUMBERS[month], int(day))


def day_labels_from_ocr(value: str, requested: date) -> tuple[date, date, date]:
    """Parse and validate the three chronological Russian dates read by OCR."""

    normalized = _plain_russian_text(value)
    matches = re.findall(
        r"\b(\d{1,2})\s+(" + "|".join(_MONTH_NUMBERS) + r")\b",
        normalized,
    )
    unique = tuple(dict.fromkeys(matches))
    if len(unique) != 3:
        raise ValueError(f"OCR must return exactly three dates, found {len(unique)}")
    days = tuple(date(2000, _MONTH_NUMBERS[month], int(day)) for day, month in unique)
    if requested not in days:
        raise ValueError("requested date is absent from OCR date labels")
    if any((right - left).days != 1 for left, right in itertools.pairwise(days)):
        raise ValueError("OCR date labels are not consecutive")
    return days  # type: ignore[return-value]
