"""Registered by ``plugin.pytest_configure`` only when ``--config-path`` is set; never loaded on its own."""

import copy

import pytest

from pytest_inject_config.const import CLASS_ATTRIBUTE, CONFIG_DATA_KEY


# Why a separate module, and not a fixture in plugin.py that returns early when the flag isn't set:
# plugin.py is always registered (it is the entry point), so a fixture there would be attached to every test class
# in every run and would execute even without --config-path. This module is registered only when the flag is set,
# so without it pytest never sees the fixture and nothing runs.
# It is a module-level function rather than a method on a plugin object because class-scoped fixtures defined as
# instance methods are deprecated (PytestRemovedIn10Warning).
@pytest.fixture(scope="class", autouse=True)
def inject_config_into_class(request: pytest.FixtureRequest) -> None:
    if request.cls is not None:
        # A copy per class, so a test that mutates its config can't leak into other classes.
        setattr(request.cls, CLASS_ATTRIBUTE, copy.deepcopy(request.config.stash[CONFIG_DATA_KEY]))
