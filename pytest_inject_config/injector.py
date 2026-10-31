"""Registered by ``plugin.pytest_configure`` only when ``--config-path`` is set; never loaded on its own."""

import copy

import pytest

from pytest_inject_config.const import CLASS_ATTRIBUTE, CONFIG_DATA_KEY


@pytest.fixture(scope="class", autouse=True)
def inject_config_into_class(request: pytest.FixtureRequest) -> None:
    if request.cls is not None:
        # A copy per class, so a test that mutates its config can't leak into other classes.
        setattr(request.cls, CLASS_ATTRIBUTE, copy.deepcopy(request.config.stash[CONFIG_DATA_KEY]))
