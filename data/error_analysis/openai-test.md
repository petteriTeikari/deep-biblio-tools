## **Background**

Developers recently encountered two test failures in the `claude-code-guardrails-template` project; the default behaviour of inheriting the parent process’ environment is bypassed[docs.python.org](https://docs.python.org/3/library/subprocess.html). The `pytest-cov` documentation also notes that **coverage measurement in subprocesses relies on environment variables being propagated and on the child interpreter having pytest‑cov installed**[pypi.org](https://pypi.org/project/pytest-cov/#:~:text=to%20start%20the%20plugin%20on,the%20worker). In GitHub Actions, the PATH and environment may differ from the developer’s machine, and a `subprocess` invocation of `pytest` may therefore fail even if it works locally.

To solidify the institutional knowledge and prevent similar bugs, this report analyses the root causes and recommends systemic practices.
