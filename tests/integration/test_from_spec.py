"""
Integration test: implement a project from a specification.

The agent receives a mini-SRS for a simple FastAPI app, implements it
(including installing dependencies), and then the test actually starts
the server and verifies the endpoints work.

Requires LLM API key configured in .env.

Usage:
    uv run python tests/integration/test_from_spec.py
    just test-integration
"""

import os
import sys
import subprocess
import time

sys.path.insert(0, os.path.dirname(__file__))

from helpers import make_workdir, cleanup, run_in_dir, check_file_contains, run_test

SPEC = """\
Project: Simple Greeting API

Technology: Python, FastAPI

Setup:
- Install required packages: uv pip install fastapi uvicorn

Files to create:
- app.py — the main application file

Endpoints:
- GET / — returns JSON {"status": "ok"}
- GET /hello/{name} — returns JSON {"message": "Hello, {name}!"}

Constraints:
- Single file app.py
- Do NOT run the server, just create the file and install dependencies
"""


def test_from_spec():
    """Agent implements a FastAPI project from spec; test verifies it runs."""
    workdir = make_workdir("webai_spec_")
    server_proc = None
    try:
        goal = "Implement the project described in the specification. Work in the current directory."

        print(f"Work dir: {workdir}")
        print(f"Goal: {goal}\n")

        run_in_dir(goal, SPEC, workdir, max_steps=10)

        # 1. Check app.py exists and has expected content
        app_path = os.path.join(workdir, "app.py")
        file_ok = check_file_contains(
            app_path,
            ["FastAPI", "@app.get", "/hello"],
            "app.py contains FastAPI app with endpoints",
        )
        if not file_ok:
            return False

        # 2. Start the server
        print("\nStarting uvicorn server...")
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--port", "9876"],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # 3. Wait for server to be ready
        import httpx

        base = "http://127.0.0.1:9876"
        ready = False
        for _ in range(25):
            try:
                httpx.get(base + "/", timeout=0.5)
                ready = True
                break
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError):
                time.sleep(0.2)

        if not ready:
            # dump stderr for diagnostics
            if server_proc and server_proc.poll() is not None:
                print(f"Server exited with code {server_proc.returncode}")
                print(server_proc.stderr.read().decode(errors="replace"))
            print("FAIL  server did not start within timeout")
            return False

        print("Server is ready.\n")

        # 4. Verify endpoints
        ok = True

        r = httpx.get(base + "/")
        if r.json() == {"status": "ok"}:
            print("PASS  GET / returns {\"status\": \"ok\"}")
        else:
            print(f"FAIL  GET / returned {r.json()}")
            ok = False

        r = httpx.get(base + "/hello/World")
        if r.json() == {"message": "Hello, World!"}:
            print("PASS  GET /hello/World returns correct greeting")
        else:
            print(f"FAIL  GET /hello/World returned {r.json()}")
            ok = False

        return ok
    finally:
        if server_proc is not None:
            server_proc.kill()
            server_proc.wait()
        cleanup(workdir)


if __name__ == "__main__":
    run_test(test_from_spec)
