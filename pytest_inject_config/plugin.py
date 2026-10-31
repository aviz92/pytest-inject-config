"""Load a config file given by ``--config-path`` and inject its content into every test class as ``self.config``.

The format is chosen by the file extension (``.json``, ``.yaml``, ``.yml``); any other extension is rejected, so
adding a format later never changes how an existing file is read. Every loader has the same shape: it takes the
path, loads it with its own library, and returns a mapping. File-level errors (missing, not UTF-8, unreadable)
are handled once, in ``load_config``.

Without the flag the injector module is never registered, so no fixture runs. The file is read once, at startup;
a missing, unreadable or invalid file stops the run with a usage error before any test is collected.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from pytest_inject_config import injector
from pytest_inject_config.const import CLASS_ATTRIBUTE, CONFIG_DATA_KEY, FLAG, INJECTOR_PLUGIN_NAME

ConfigLoader = Callable[[Path], dict[str, Any]]


def ensure_mapping(data: Any, path: Path) -> dict[str, Any]:
    if data is None:
        raise pytest.UsageError(f"{FLAG}: {path} is empty or null")
    if not isinstance(data, dict):
        raise pytest.UsageError(f"{FLAG}: top level of {path} must be a mapping, got {type(data).__name__}")
    return data


def load_json_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as config_file:
        try:
            data = json.load(config_file)
        except json.JSONDecodeError as e:
            raise pytest.UsageError(f"{FLAG}: invalid JSON in {path}: {e}") from e
    return ensure_mapping(data=data, path=path)


def load_yaml_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as config_file:
        # safe_load only: full YAML loading can construct arbitrary Python objects (code execution) from the file.
        try:
            data = yaml.safe_load(config_file)
        except yaml.YAMLError as e:
            raise pytest.UsageError(f"{FLAG}: invalid YAML in {path}: {e}") from e
    return ensure_mapping(data=data, path=path)


# Keyed by lowercase file extension. To support a new format, write a load_<format>_config and add it here.
CONFIG_LOADERS: dict[str, ConfigLoader] = {
    ".json": load_json_config,
    ".yaml": load_yaml_config,
    ".yml": load_yaml_config,
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        FLAG,
        action="store",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"Load a config file ({', '.join(CONFIG_LOADERS)}) and expose its content to test classes "
        f"as `self.{CLASS_ATTRIBUTE}`.",
    )


def pytest_configure(config: pytest.Config) -> None:
    if (config_path := config.getoption(FLAG)) is None:
        return

    config.stash[CONFIG_DATA_KEY] = load_config(path=config_path)
    config.pluginmanager.register(injector, INJECTOR_PLUGIN_NAME)


def get_config_loader(path: Path) -> ConfigLoader:
    suffix = path.suffix.lower()
    if (loader := CONFIG_LOADERS.get(suffix)) is None:
        supported = ", ".join(CONFIG_LOADERS)
        raise pytest.UsageError(
            f"{FLAG}: unsupported format {suffix or '(no extension)'!r} in {path}, supported: {supported}"
        )
    return loader


def load_config(path: Path) -> dict[str, Any]:
    loader = get_config_loader(path=path)
    try:
        return loader(path)
    except FileNotFoundError as e:
        raise pytest.UsageError(f"{FLAG}: file not found: {path}") from e
    except UnicodeDecodeError as e:
        raise pytest.UsageError(f"{FLAG}: {path} is not UTF-8 text: {e}") from e
    except OSError as e:
        raise pytest.UsageError(f"{FLAG}: cannot read {path}: {e}") from e
