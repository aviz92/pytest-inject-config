![PyPI version](https://img.shields.io/pypi/v/pytest-inject-config)
![Python](https://img.shields.io/badge/python->=3.12-blue)
![Development Status](https://img.shields.io/badge/status-stable-green)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
![PyPI](https://img.shields.io/pypi/dm/pytest-inject-config)
![License](https://img.shields.io/pypi/l/pytest-inject-config)

---

# 💡 pytest-inject-config
A pytest plugin that loads a JSON file given by `--config-path` and injects it into every test class as `self.config`.
Run the same test suite against different environments by switching a single flag.

---

## 📦 Installation
```bash
uv add pytest-inject-config
```

---

## 🚀 Features
  - ✅ **One flag, any environment** — point `--config-path` at a different JSON file per environment
  - ✅ **Isolated per class** — each test class gets its own copy, so a test that mutates its config can't affect others
  - ✅ **Fails fast** — a missing file, a directory, or invalid JSON stops the run at startup with a clear usage error
  - ✅ **Read once** — the file is loaded at startup, not once per class
  - ✅ **Zero footprint without the flag** — nothing is registered and no fixture runs

---

## 🛠️ How to Use
1. Create a JSON file per environment:
   ```json
   {
       "host": "10.0.0.1",
       "port": 8080
   }
   ```
2. Read it from your test classes through `self.config`:
   ```python
   class TestDevice:
       def test_connect(self):
           assert connect(self.config["host"], self.config["port"])
   ```
3. Run with the file for the environment you want:
   ```bash
   pytest --config-path=config/staging.json
   ```

---

## ⚙️ Behavior
| Situation | Result |
|---|---|
| Test inside a class | `self.config` holds the file's content (any JSON value: object, list, ...) |
| Module-level test function | Unaffected |
| Relative path | Resolved from the directory pytest is run in |
| Missing file, directory, unreadable or invalid JSON | `UsageError` at startup (exit code 4), no tests run |
| No `--config-path` | Nothing is injected; no fixture runs |

---

## ▶️ Usage Examples
### Select the environment in CI
```bash
pytest --config-path="config/${TARGET_ENV}.json"
```

### Set a default in `pytest.ini`
```ini
[pytest]
addopts =
    --config-path=config/local.json
```

---

## 🔁 Migrating from pytest-plugins
This plugin was previously `add_config_parameters` in `pytest-plugins`, where it never worked.
Both register the `--config-path` option, so don't install them together until you're on a `pytest-plugins`
release without it.

---

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-addition`
3. Make your changes
4. Commit your changes: `git commit -m 'Add my addition'`
5. Push to the branch: `git push origin feature/my-addition`
6. Open a Pull Request

Additions that promote clean, productive, and maintainable development are always welcome.

---

## 📄 License
MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Thanks
Thanks for exploring this repository! <br>
Happy coding!

[![GitHub](https://img.shields.io/badge/GitHub-aviz92-181717?logo=github)](https://github.com/aviz92)
&nbsp; [![PyPI](https://img.shields.io/badge/PyPI-aviz-3775A9?logo=pypi)](https://pypi.org/user/aviz/)
&nbsp; [![Blog](https://img.shields.io/badge/Blog-aviz92.github.io-0066CC?logo=googlechrome)](https://aviz92.github.io/)
&nbsp; [![LinkedIn](https://img.shields.io/badge/LinkedIn-avi--zaguri-0A66C2?logo=linkedin)](https://www.linkedin.com/in/avi-zaguri-41869b11b)
