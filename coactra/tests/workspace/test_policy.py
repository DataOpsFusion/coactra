import pytest

from coactra.workspace import CliPolicy, PolicyError


def test_default_policy_requires_explicit_allowlist():
    with pytest.raises(PolicyError, match="explicit allowlist"):
        CliPolicy().check("ls -la")


def test_deny_blocks_matching_command():
    pol = CliPolicy(allow=["ls"], deny=["rm"])
    pol.check("ls")  # allowed
    with pytest.raises(PolicyError, match="rm"):
        pol.check("rm -rf /")


def test_allowlist_blocks_anything_not_listed():
    pol = CliPolicy(allow=["ls", "cat"])
    pol.check("ls -la")
    pol.check("cat notes.md")
    with pytest.raises(PolicyError, match="curl"):
        pol.check("curl http://evil")


def test_deny_takes_precedence_over_allow():
    pol = CliPolicy(allow=["git"], deny=["git push"])
    pol.check("git status")
    with pytest.raises(PolicyError):
        pol.check("git push origin main")


def test_empty_command_is_rejected():
    with pytest.raises(PolicyError):
        CliPolicy().check("   ")


def test_safe_default_denies_python_exec():
    pol = CliPolicy.safe_default()
    with pytest.raises(PolicyError, match="python"):
        pol.check("python -c print('hi')")
    with pytest.raises(PolicyError, match="python3"):
        pol.check(["python3", "-c", "print('hi')"])
