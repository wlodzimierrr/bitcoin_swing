# Bitcoin Swing Predictor

Low-frequency Bitcoin swing trading decision-support system.

The initial implementation is organized around the project rulebook and ticket
backlog:

- `bitcoin_swing_predictor_rulebook_v1.md`
- `bitcoin_swing_predictor_project_tickets_v1.md`
- `bitcoin_swing_predictor_project_tickets_structured_v1.md`

## Development

Create a virtual environment and install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
```

Run database migrations against a database URL:

```bash
alembic \
  -x database_url=postgresql+psycopg://user:password@localhost/dbname \
  -x runtime_role=btc_predictor_runtime \
  -x research_role=btc_predictor_research \
  upgrade head
```

The application also exposes migration helpers for tests and scripts:

```python
from btc_predictor.db import upgrade_database, verify_research_connection

upgrade_database("postgresql+psycopg://user:password@localhost/dbname")
verify_research_connection("postgresql+psycopg://user:password@localhost/dbname")
```

Predictor output is persisted through `signals.predictor_runs`,
`signals.recommendations`, and `signals.recommendation_reason_codes`. Together
these tables carry the strategy/config/code identity, point-in-time data cutoff,
scores, levels, risk payload, action, and ordered reason codes needed to
reconstruct a historical recommendation.

Runtime environment can be selected with `BTC_PREDICTOR_ENV`. The default is
`dev`.

Strategy parameters are loaded from the versioned TOML file at
`btc_predictor/config/strategy/default.toml`. Startup code can load runtime and
strategy config together, validating both before returning:

```python
from btc_predictor.config import load_application_config

config = load_application_config()
run_metadata = config.strategy.run_metadata()
```
