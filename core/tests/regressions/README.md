# Core regression tests

This package contains small tests for bugs that have already reached local boot,
CI or staging.

Use this area for cross-cutting regressions such as:

- root URLConf import failures;
- missing required dependencies;
- auth/rate-limit boot contracts;
- settings/configuration mismatches that break `manage.py check` or `runserver`.

Keep these tests focused and cheap. They should explain the incident they protect
through the test name or docstring.
