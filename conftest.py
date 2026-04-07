"""
Root conftest.py.

Excludes tests/ci/ from the default pytest collection so that
CI meta-tests (which require a GITHUB_TOKEN and live GitHub API)
don't run inside the CI unit-test job itself.

To run meta-tests explicitly:
  pytest tests/ci/ -v
"""

collect_ignore_glob = ["tests/ci/test_ci_pipeline.py"]
