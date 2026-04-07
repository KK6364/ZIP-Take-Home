"""
Meta-tests: verify the CI pipeline configuration and runtime behavior
using the GitHub API (PyGithub).

Run these locally after setting:
  export GITHUB_TOKEN=<PAT with repo scope>

They are intentionally NOT collected by the default pytest run
(see conftest.py) so they don't block the unit-test job.
Run them explicitly:
  pytest tests/ci/ -v
"""

import os

import pytest
import requests
from github import Auth, Github, GithubException

REPO_NAME = "KK6364/ZIP-Take-Home"
MAIN_BRANCH = "main"
REQUIRED_WORKFLOW_FILE = ".github/workflows/ci.yml"
REQUIRED_JOBS = {"lint", "test", "notify"}
REQUIRED_STATUS_CHECKS = ["Lint (flake8)", "Unit Tests (pytest)"]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gh_token():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN not set — skipping CI meta-tests")
    return token


@pytest.fixture(scope="module")
def repo(gh_token):
    g = Github(auth=Auth.Token(gh_token))
    return g.get_repo(REPO_NAME)


@pytest.fixture(scope="module")
def rulesets(gh_token):
    """Fetch repository rulesets via REST API (Rulesets are not in PyGithub yet)."""
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.get(
        f"https://api.github.com/repos/{REPO_NAME}/rulesets",
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        pytest.skip(f"Could not fetch rulesets: {resp.status_code}")
    rules = resp.json()
    if not rules:
        pytest.skip("No rulesets configured on this repository")
    return rules


@pytest.fixture(scope="module")
def main_ruleset(gh_token, rulesets):
    """Return the detailed ruleset that targets main."""
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    for rs in rulesets:
        resp = requests.get(
            f"https://api.github.com/repos/{REPO_NAME}/rulesets/{rs['id']}",
            headers=headers,
            timeout=10,
        )
        detail = resp.json()
        conditions = detail.get("conditions", {})
        ref_name = conditions.get("ref_name", {})
        includes = ref_name.get("include", [])
        if any(MAIN_BRANCH in inc for inc in includes):
            return detail
    pytest.skip("No ruleset targeting main branch found")


# ---------------------------------------------------------------------------
# Workflow file structure
# ---------------------------------------------------------------------------


class TestWorkflowFile:
    def test_workflow_file_exists(self, repo):
        """ci.yml must exist in the repository."""
        try:
            repo.get_contents(REQUIRED_WORKFLOW_FILE)
        except GithubException:
            pytest.fail(f"{REQUIRED_WORKFLOW_FILE} not found in {REPO_NAME}")

    def test_workflow_file_is_yaml(self, repo):
        """ci.yml must be parseable YAML."""
        import yaml

        content_file = repo.get_contents(REQUIRED_WORKFLOW_FILE)
        raw = content_file.decoded_content.decode()
        parsed = yaml.safe_load(raw)
        assert isinstance(parsed, dict), "ci.yml is not valid YAML"

    def test_workflow_has_required_jobs(self, repo):
        """Workflow must define lint, test, and notify jobs."""
        import yaml

        content_file = repo.get_contents(REQUIRED_WORKFLOW_FILE)
        raw = content_file.decoded_content.decode()
        parsed = yaml.safe_load(raw)
        jobs = set(parsed.get("jobs", {}).keys())
        missing = REQUIRED_JOBS - jobs
        assert not missing, f"Workflow missing jobs: {missing}"

    def test_workflow_triggers_on_pr(self, repo):
        """Workflow must trigger on pull_request events."""
        import yaml

        content_file = repo.get_contents(REQUIRED_WORKFLOW_FILE)
        raw = content_file.decoded_content.decode()
        parsed = yaml.safe_load(raw)
        on_block = parsed.get("on", parsed.get(True, {}))
        # 'on' is parsed as True by PyYAML in some versions
        assert "pull_request" in on_block, "Workflow does not trigger on pull_request"

    def test_lint_job_uses_flake8(self, repo):
        """Lint job must invoke flake8."""
        content_file = repo.get_contents(REQUIRED_WORKFLOW_FILE)
        raw = content_file.decoded_content.decode()
        assert "flake8" in raw, "flake8 not referenced in ci.yml"

    def test_test_job_uses_pytest(self, repo):
        """Test job must invoke pytest."""
        content_file = repo.get_contents(REQUIRED_WORKFLOW_FILE)
        raw = content_file.decoded_content.decode()
        assert "pytest" in raw, "pytest not referenced in ci.yml"


# ---------------------------------------------------------------------------
# Branch protection (via Rulesets API)
# ---------------------------------------------------------------------------


class TestBranchProtection:
    def test_ruleset_exists_for_main(self, main_ruleset):
        """A ruleset targeting main must exist and be active."""
        assert main_ruleset["enforcement"] == "active", (
            f"Ruleset '{main_ruleset['name']}' is not active"
        )

    def test_require_pull_request_reviews(self, main_ruleset):
        """Ruleset must require at least one PR approving review."""
        rules = {r["type"]: r for r in main_ruleset.get("rules", [])}
        assert "pull_request" in rules, "pull_request rule not configured"
        params = rules["pull_request"].get("parameters", {})
        assert params.get("required_approving_review_count", 0) >= 1

    def test_required_status_checks(self, main_ruleset):
        """lint and test status checks must be required."""
        rules = {r["type"]: r for r in main_ruleset.get("rules", [])}
        assert "required_status_checks" in rules, "required_status_checks rule not configured"
        params = rules["required_status_checks"].get("parameters", {})
        configured = {c["context"] for c in params.get("required_status_checks", [])}
        missing = set(REQUIRED_STATUS_CHECKS) - configured
        assert not missing, f"Missing required checks: {missing}"

    def test_no_force_push(self, main_ruleset):
        """Force-push to main must be blocked."""
        rule_types = {r["type"] for r in main_ruleset.get("rules", [])}
        assert "non_fast_forward" in rule_types or "deletion" in rule_types, (
            "No force-push/deletion restriction found in ruleset"
        )

    def test_dismiss_stale_reviews(self, main_ruleset):
        """Stale reviews must be dismissed on new commits."""
        rules = {r["type"]: r for r in main_ruleset.get("rules", [])}
        assert "pull_request" in rules, "pull_request rule not configured"
        params = rules["pull_request"].get("parameters", {})
        assert params.get("dismiss_stale_reviews_on_push", False), (
            "dismiss_stale_reviews_on_push is not enabled"
        )


# ---------------------------------------------------------------------------
# Recent workflow runs (smoke check)
# ---------------------------------------------------------------------------


class TestWorkflowRuns:
    def test_ci_workflow_has_runs(self, repo):
        """At least one CI workflow run must exist."""
        workflows = list(repo.get_workflows())
        ci_workflows = [w for w in workflows if "ci" in w.name.lower()]
        assert ci_workflows, "No CI workflow found in the repository"
        runs = list(ci_workflows[0].get_runs())
        assert runs, "CI workflow has never run — push a commit to trigger it"

    def test_latest_run_on_main_passed(self, repo):
        """The most recent CI run on main must have concluded successfully."""
        workflows = list(repo.get_workflows())
        ci_workflows = [w for w in workflows if "ci" in w.name.lower()]
        assert ci_workflows, "No CI workflow found"
        runs = list(ci_workflows[0].get_runs(branch=MAIN_BRANCH, status="completed"))
        if not runs:
            pytest.skip("No completed runs on main yet")
        latest = runs[0]
        assert latest.conclusion == "success", (
            f"Latest CI run on main concluded with '{latest.conclusion}'. "
            f"See: {latest.html_url}"
        )
