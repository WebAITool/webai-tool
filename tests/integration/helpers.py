"""Shared utilities for integration tests."""

import sys
import os
import tempfile
import shutil
import importlib.util

# Add src to path once
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from lg_agent import run_agent  # noqa: E402

GENERATOR_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "generate_fake_project.py")


def make_workdir(prefix: str = "webai_test_") -> str:
    """Create a temporary working directory."""
    return tempfile.mkdtemp(prefix=prefix)


def cleanup(workdir: str) -> None:
    """Remove a temporary working directory."""
    shutil.rmtree(workdir, ignore_errors=True)


def run_in_dir(goal: str, spec: str, workdir: str, max_steps: int = 10) -> None:
    """Run the agent with cwd set to workdir, then restore cwd."""
    original = os.getcwd()
    os.chdir(workdir)
    try:
        run_agent(goal, spec, prjdir=".", max_steps=max_steps)
    finally:
        os.chdir(original)


def generate_demo_project(target: str) -> None:
    """Generate the demo Vue + FastAPI project into target dir."""
    spec = importlib.util.spec_from_file_location("generator", GENERATOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.create_structure(target)


def check_file_contains(path: str, substrings: list[str], label: str) -> bool:
    """Check that a file exists and contains all expected substrings.

    Prints PASS/FAIL with the label. Returns True if all checks pass.
    """
    if not os.path.exists(path):
        print(f"FAIL  {label}: file not found at {path}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    missing = [s for s in substrings if s not in content]
    if missing:
        print(f"FAIL  {label}: missing {missing!r}")
        return False

    print(f"PASS  {label}")
    return True


def run_test(fn) -> None:
    """Run a test function, print result, exit with proper code.

    The test function should return True on success, False on failure.
    Exceptions are caught and printed as failures.
    """
    try:
        success = fn()
    except Exception as e:
        print(f"FAIL: exception: {e}")
        import traceback
        traceback.print_exc()
        success = False
    sys.exit(0 if success else 1)
