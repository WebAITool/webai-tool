"""
Integration test: simple file creation.

Verifies that the agent can create a file with specific content.
Requires LLM API key configured in .env.

Usage:
    uv run python tests/integration/test_hello_world.py
    just test-integration
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from helpers import make_workdir, cleanup, run_in_dir, check_file_contains, run_test

TARGET_FILENAME = "hello.txt"
EXPECTED_CONTENT = "Hello, World!"


def test_hello_world():
    """Agent should create a text file with the expected content."""
    workdir = make_workdir("webai_hello_")
    try:
        goal = "Create a file named 'hello.txt' with the text 'Hello, World!'"
        spec = "Create the file in the current directory."

        print(f"Work dir: {workdir}")
        print(f"Goal: {goal}\n")

        run_in_dir(goal, spec, workdir, max_steps=5)

        return check_file_contains(
            os.path.join(workdir, TARGET_FILENAME),
            [EXPECTED_CONTENT],
            "file created with correct content",
        )
    finally:
        cleanup(workdir)


if __name__ == "__main__":
    run_test(test_hello_world)
