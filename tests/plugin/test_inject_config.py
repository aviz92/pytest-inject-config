import json

import pytest

CONFIG_DATA = {"host": "10.0.0.1", "port": 8080, "features": ["a", "b"]}


def _write_config(pytester: pytest.Pytester, data: object = None, name: str = "config.json") -> str:
    path = pytester.path / name
    path.write_text(json.dumps(CONFIG_DATA if data is None else data), encoding="utf-8")
    return str(path)


class TestInjection:
    def test_config_path_option_registered(self, pytester: pytest.Pytester) -> None:
        result = pytester.runpytest_subprocess("--help")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.stdout.fnmatch_lines(["*--config-path=PATH*"])

    def test_config_injected_into_test_class(self, pytester: pytest.Pytester) -> None:
        config_path = _write_config(pytester)
        pytester.makepyfile(
            """
            class TestUsesConfig:
                def test_host(self):
                    assert self.config["host"] == "10.0.0.1"

                def test_port(self):
                    assert self.config["port"] == 8080
        """
        )
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=2)

    def test_non_object_json_is_injected_as_is(self, pytester: pytest.Pytester) -> None:
        config_path = _write_config(pytester, data=["first", "second"])
        pytester.makepyfile(
            """
            class TestUsesConfig:
                def test_list(self):
                    assert self.config == ["first", "second"]
        """
        )
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=1)

    def test_relative_path_resolved_from_invocation_dir(self, pytester: pytest.Pytester) -> None:
        _write_config(pytester, name="relative.json")
        pytester.makepyfile(
            """
            class TestUsesConfig:
                def test_host(self):
                    assert self.config["host"] == "10.0.0.1"
        """
        )
        result = pytester.runpytest_subprocess("--config-path=relative.json")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=1)

    def test_module_level_tests_unaffected(self, pytester: pytest.Pytester) -> None:
        config_path = _write_config(pytester)
        pytester.makepyfile(
            """
            def test_function():
                assert True
        """
        )
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=1)

    def test_each_class_gets_its_own_copy(self, pytester: pytest.Pytester) -> None:
        config_path = _write_config(pytester)
        pytester.makepyfile(
            """
            class TestMutates:
                def test_mutate(self):
                    self.config["features"].append("leaked")

            class TestReads:
                def test_not_leaked(self):
                    assert self.config["features"] == ["a", "b"]
        """
        )
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=2)


class TestWithoutFlag:
    def test_runs_normally_without_flag(self, pytester: pytest.Pytester) -> None:
        pytester.makepyfile(
            """
            class TestNoConfig:
                def test_no_config_attribute(self):
                    assert not hasattr(self, "config")
        """
        )
        result = pytester.runpytest_subprocess()
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=1)

    def test_injector_not_registered_without_flag(self, pytester: pytest.Pytester) -> None:
        pytester.makeconftest(
            """
            def pytest_sessionstart(session):
                assert not session.config.pluginmanager.has_plugin("inject-config-injector")
        """
        )
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess()
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"

    def test_injector_registered_with_flag(self, pytester: pytest.Pytester) -> None:
        config_path = _write_config(pytester)
        pytester.makeconftest(
            """
            def pytest_sessionstart(session):
                assert session.config.pluginmanager.has_plugin("inject-config-injector")
        """
        )
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"


class TestInvalidInput:
    def test_flag_without_value_is_usage_error(self, pytester: pytest.Pytester) -> None:
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"

    def test_missing_file_is_usage_error(self, pytester: pytest.Pytester) -> None:
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=does-not-exist.json")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: file not found: does-not-exist.json*"])

    def test_invalid_json_is_usage_error(self, pytester: pytest.Pytester) -> None:
        bad_path = pytester.path / "bad.json"
        bad_path.write_text("{not json", encoding="utf-8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={bad_path}")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: invalid JSON in*"])

    def test_non_utf8_file_is_usage_error(self, pytester: pytest.Pytester) -> None:
        binary_path = pytester.path / "binary.json"
        binary_path.write_bytes(b"\xff\xfe\x00not-utf8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={binary_path}")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: invalid JSON in*"])

    def test_directory_is_usage_error(self, pytester: pytest.Pytester) -> None:
        pytester.mkdir("a_directory")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=a_directory")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: cannot read a_directory*"])
