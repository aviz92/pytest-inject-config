"""Load a JSON file given by ``--config-path`` and inject its content into every test class as ``self.config``.

Without the flag nothing is registered, so no fixture runs. The file is read once, at startup; a missing,
unreadable or invalid file stops the run with a usage error before any test is collected.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

FLAG = "--config-path"
CLASS_ATTRIBUTE = "config"
INJECTOR_PLUGIN_NAME = "inject-config-injector"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        FLAG,
        action="store",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"Load a JSON file and expose its content to test classes as `self.{CLASS_ATTRIBUTE}`.",
    )


def pytest_configure(config: pytest.Config) -> None:
    if (config_path := config.getoption(FLAG)) is None:
        return

    config.pluginmanager.register(ConfigInjector(data=load_config(path=config_path)), INJECTOR_PLUGIN_NAME)


def load_config(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as config_file:
            return json.load(config_file)
    except FileNotFoundError as e:
        raise pytest.UsageError(f"{FLAG}: file not found: {path}") from e
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise pytest.UsageError(f"{FLAG}: invalid JSON in {path}: {e}") from e
    except OSError as e:
        raise pytest.UsageError(f"{FLAG}: cannot read {path}: {e}") from e


class ConfigInjector:
    """Registered only when ``--config-path`` is set."""

    def __init__(self, data: Any) -> None:
        self.data = data

    @pytest.fixture(scope="class", autouse=True)
    def inject_config_into_class(self, request: pytest.FixtureRequest) -> None:
        if request.cls is not None:
            # A copy per class, so a test that mutates its config can't leak into other classes.
            setattr(request.cls, CLASS_ATTRIBUTE, copy.deepcopy(self.data))
