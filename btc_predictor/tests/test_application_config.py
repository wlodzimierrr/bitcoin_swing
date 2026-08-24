from btc_predictor.config import load_application_config


def test_load_application_config_validates_runtime_and_strategy() -> None:
    config = load_application_config(environment="test")

    assert config.runtime.environment == "test"
    assert config.strategy.identity.parameter_set_id == "default_phase1"
