from pathlib import Path

import pytest
from pydantic import ValidationError

from vigil.utils.config import load_config


def test_default_yaml_loads_without_environment():
    config = load_config(
        Path(__file__).resolve().parents[2] / "configs/base.yaml", use_environment=False
    )
    assert config.project_name == "VIGIL-AEM"
    assert config.random_seed == 42
    assert config.transfer_epsilon >= 0


def test_environment_override_is_explicit(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("random_seed: 42\n", encoding="utf-8")
    monkeypatch.setenv("VIGIL_RANDOM_SEED", "123")
    monkeypatch.setenv("OPENAI_API_KEY", "test-value-never-consumed")
    assert load_config(path).random_seed == 123
    assert load_config(path, use_environment=False).random_seed == 42


@pytest.mark.parametrize("text", ["[]", "", "transfer_epsilon: -1", "unexpected: true"])
def test_bad_configuration_fails(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises((ValueError, ValidationError)):
        load_config(path)


def test_yaml_does_not_execute_python(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("!!python/object/apply:os.system ['echo unsafe']", encoding="utf-8")
    import yaml

    with pytest.raises(yaml.constructor.ConstructorError):
        load_config(path)
