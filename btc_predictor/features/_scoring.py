"""Decimal compatibility boundary for the float64 quantitative score engine."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from btc_predictor.quant.scoring import weighted_score


@dataclass(frozen=True)
class DecimalWeightedScore:
    score: Decimal | None
    contributions: dict[str, Decimal | None]
    missing_components: tuple[str, ...]


def decimal_weighted_score(
    input_values: Mapping[str, Decimal | None],
    weights: Mapping[str, Decimal],
    *,
    component_ids: Sequence[str],
    expected_weight_total: float | None = 1.0,
) -> DecimalWeightedScore:
    """Delegate score math to float64 while retaining existing Decimal scale."""

    names = tuple(component_ids)
    values = [
        float(input_values[name]) if input_values[name] is not None else np.nan
        for name in names
    ]
    result = weighted_score(
        values,
        {name: float(weights[name]) for name in names},
        component_names=names,
        expected_weight_total=expected_weight_total,
    )
    contributions: dict[str, Decimal | None] = {}
    exact_templates: list[Decimal] = []
    missing_components = []
    for index, name in enumerate(names):
        input_value = input_values[name]
        if bool(result.missing_mask[index]):
            contributions[name] = None
            missing_components.append(name)
            continue
        if input_value is None:
            raise RuntimeError("quant missing mask disagrees with Decimal input")
        template = weights[name] * input_value
        exact_templates.append(template)
        contributions[name] = _decimal_with_template(
            float(result.contributions[index]),
            template,
        )

    score = None
    if bool(result.complete_mask):
        template_total = sum(exact_templates, Decimal("0"))
        score = _decimal_with_template(float(result.scores), template_total)
    return DecimalWeightedScore(
        score=score,
        contributions=contributions,
        missing_components=tuple(missing_components),
    )


def _decimal_with_template(value: float, template: Decimal) -> Decimal:
    quantum = Decimal(1).scaleb(template.as_tuple().exponent)
    return Decimal(str(value)).quantize(quantum)
