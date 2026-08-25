"""ETF flow point-in-time helpers."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select

from btc_predictor.data.ohlcv import require_utc_datetime
from btc_predictor.db.raw import etf_flows


def latest_etf_flows_available_at(signal_time: datetime) -> Select:
    """Select latest ETF flow revisions available at a signal timestamp."""

    signal_time = require_utc_datetime(signal_time, "signal_time")
    ranked_revisions = (
        select(
            etf_flows,
            func.row_number()
            .over(
                partition_by=(
                    etf_flows.c.fund,
                    etf_flows.c.observation_date,
                    etf_flows.c.provider,
                ),
                order_by=(
                    etf_flows.c.available_at.desc(),
                    etf_flows.c.revision.desc(),
                ),
            )
            .label("revision_rank"),
        )
        .where(etf_flows.c.available_at <= signal_time)
        .subquery()
    )

    return select(ranked_revisions).where(ranked_revisions.c.revision_rank == 1)
