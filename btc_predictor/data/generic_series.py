"""Generic point-in-time series helpers."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select

from btc_predictor.data.ohlcv import require_utc_datetime
from btc_predictor.db.raw import generic_series


SUPPORTED_SERIES_TYPES = ("macro", "liquidity", "onchain", "market_proxy")


def latest_generic_series_available_at(
    signal_time: datetime,
    *,
    series_ids: Sequence[str] | None = None,
    series_types: Sequence[str] | None = None,
) -> Select:
    """Select latest generic-series revisions available at a signal timestamp."""

    signal_time = require_utc_datetime(signal_time, "signal_time")
    ranked_revisions = (
        select(
            generic_series,
            func.row_number()
            .over(
                partition_by=(
                    generic_series.c.series_id,
                    generic_series.c.observation_time,
                    generic_series.c.provider,
                ),
                order_by=(
                    generic_series.c.available_at.desc(),
                    generic_series.c.revision.desc(),
                ),
            )
            .label("revision_rank"),
        )
        .where(generic_series.c.available_at <= signal_time)
    )

    if series_ids is not None:
        ranked_revisions = ranked_revisions.where(generic_series.c.series_id.in_(series_ids))

    if series_types is not None:
        unsupported = sorted(set(series_types) - set(SUPPORTED_SERIES_TYPES))
        if unsupported:
            raise ValueError(f"Unsupported series types: {', '.join(unsupported)}")
        ranked_revisions = ranked_revisions.where(generic_series.c.series_type.in_(series_types))

    subquery = ranked_revisions.subquery()
    return select(subquery).where(subquery.c.revision_rank == 1)
