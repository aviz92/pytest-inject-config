from typing import Any

import pytest

FLAG = "--config-path"
CLASS_ATTRIBUTE = "config"
INJECTOR_PLUGIN_NAME = "inject-config-injector"
CONFIG_DATA_KEY = pytest.StashKey[Any]()
