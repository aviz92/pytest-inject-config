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

    @pytest.mark.parametrize("file_name", ["binary.json", "binary.yaml"])
    def test_non_utf8_file_is_usage_error(self, pytester: pytest.Pytester, file_name: str) -> None:
        (pytester.path / file_name).write_bytes(b"\xff\xfe\x00not-utf8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={file_name}")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines([f"*--config-path: {file_name} is not UTF-8 text*"])

    def test_directory_is_usage_error(self, pytester: pytest.Pytester) -> None:
        pytester.mkdir("a_directory.json")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=a_directory.json")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: cannot read a_directory.json*"])


class TestFormatSelection:
    def test_extension_is_case_insensitive(self, pytester: pytest.Pytester) -> None:
        config_path = _write_config(pytester, name="CONFIG.JSON")
        pytester.makepyfile(
            """
            class TestUsesConfig:
                def test_host(self):
                    assert self.config["host"] == "10.0.0.1"
        """
        )
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=1)

    def test_unsupported_extension_is_usage_error(self, pytester: pytest.Pytester) -> None:
        # Valid JSON content, but the extension decides the format: it must not be read by accident.
        config_path = _write_config(pytester, name="config.toml")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(
            ["*--config-path: unsupported format '.toml' in *config.toml, supported: .json, .yaml, .yml*"]
        )

    def test_missing_extension_is_usage_error(self, pytester: pytest.Pytester) -> None:
        config_path = _write_config(pytester, name="config")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={config_path}")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: unsupported format '(no extension)'*"])

    def test_supported_formats_listed_in_help(self, pytester: pytest.Pytester) -> None:
        result = pytester.runpytest_subprocess("--help")
        result.stdout.fnmatch_lines(["*Load a config file (.json, .yaml, .yml)*"])


YAML_CONFIG = """
host: 10.0.0.1
port: 8080
features:
  - a
  - b
"""

USES_CONFIG_TEST = """
class TestUsesConfig:
    def test_values(self):
        assert self.config == {"host": "10.0.0.1", "port": 8080, "features": ["a", "b"]}
"""


class TestYaml:
    @pytest.mark.parametrize("file_name", ["config.yaml", "config.yml", "CONFIG.YML"])
    def test_yaml_injected_into_test_class(self, pytester: pytest.Pytester, file_name: str) -> None:
        (pytester.path / file_name).write_text(YAML_CONFIG, encoding="utf-8")
        pytester.makepyfile(USES_CONFIG_TEST)
        result = pytester.runpytest_subprocess(f"--config-path={file_name}")
        assert result.ret == pytest.ExitCode.OK, f"Expected OK, got {result.ret}"
        result.assert_outcomes(passed=1)

    def test_invalid_yaml_is_usage_error(self, pytester: pytest.Pytester) -> None:
        (pytester.path / "bad.yaml").write_text("host: [unclosed\n", encoding="utf-8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=bad.yaml")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: invalid YAML in bad.yaml*"])

    def test_multiple_documents_are_usage_error(self, pytester: pytest.Pytester) -> None:
        (pytester.path / "multi.yaml").write_text("host: a\n---\nhost: b\n", encoding="utf-8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=multi.yaml")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: invalid YAML in multi.yaml*"])

    def test_python_object_tags_are_rejected(self, pytester: pytest.Pytester) -> None:
        # Full YAML loading would run this; safe loading must refuse it.
        marker = pytester.path / "executed.txt"
        (pytester.path / "unsafe.yaml").write_text(
            f"!!python/object/apply:builtins.open ['{marker}', 'w']\n",
            encoding="utf-8",
        )
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=unsafe.yaml")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: invalid YAML in unsafe.yaml*"])
        assert not marker.exists(), "The YAML file must not be able to execute code"


class TestTopLevelMustBeMapping:
    def test_empty_yaml_is_usage_error(self, pytester: pytest.Pytester) -> None:
        (pytester.path / "empty.yaml").write_text("  \n\n", encoding="utf-8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=empty.yaml")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: empty.yaml is empty or null*"])

    @pytest.mark.parametrize(("file_name", "content"), [("null.json", "null"), ("null.yaml", "~\n")])
    def test_null_top_level_is_usage_error(self, pytester: pytest.Pytester, file_name: str, content: str) -> None:
        (pytester.path / file_name).write_text(content, encoding="utf-8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={file_name}")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines([f"*--config-path: {file_name} is empty or null*"])

    def test_empty_json_is_usage_error(self, pytester: pytest.Pytester) -> None:
        (pytester.path / "empty.json").write_text("", encoding="utf-8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess("--config-path=empty.json")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines(["*--config-path: invalid JSON in empty.json*"])

    @pytest.mark.parametrize(
        ("file_name", "content", "type_name"),
        [
            ("list.json", '["first", "second"]', "list"),
            ("number.json", "42", "int"),
            ("list.yaml", "- first\n- second\n", "list"),
            ("string.yaml", "just a string\n", "str"),
        ],
    )
    def test_non_mapping_top_level_is_usage_error(
        self, pytester: pytest.Pytester, file_name: str, content: str, type_name: str
    ) -> None:
        (pytester.path / file_name).write_text(content, encoding="utf-8")
        pytester.makepyfile("def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(f"--config-path={file_name}")
        assert result.ret == pytest.ExitCode.USAGE_ERROR, f"Expected USAGE_ERROR, got {result.ret}"
        result.stderr.fnmatch_lines([f"*--config-path: top level of {file_name} must be a mapping, got {type_name}*"])
