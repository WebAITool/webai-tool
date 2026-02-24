"""
Integration test: add a feature to an existing Vue + FastAPI project.

Generates a demo project, then asks the agent to:
1. Add a Logout button to Header.vue
2. Add a POST /logout endpoint to auth.py

Requires LLM API key configured in .env.

Usage:
    uv run python tests/integration/test_add_feature.py
    just test-integration
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from helpers import (
    make_workdir,
    cleanup,
    run_in_dir,
    generate_demo_project,
    check_file_contains,
    run_test,
)


def test_add_feature():
    """Agent should add logout button (Vue) and endpoint (FastAPI)."""
    workdir = make_workdir("webai_feature_")
    try:
        print(f"Work dir: {workdir}")
        generate_demo_project(workdir)
        print("Demo project generated.\n")

        goal = (
            "Implement Logout functionality:\n"
            "1. In frontend/src/components/Header.vue — add a <button> "
            "with text 'Logout' inside the .user-info div.\n"
            "2. In backend/app/routers/auth.py — add a POST endpoint "
            "'/logout' that returns {\"msg\": \"Logged out\"}."
        )
        spec = (
            "Project is a Vue 3 + FastAPI app.\n\n"
            "Frontend:\n"
            "- Modify Header.vue.\n"
            "- Add: <button @click=\"logout\">Logout</button>\n"
            "- Add a logout() function with console.log('logged out').\n\n"
            "Backend:\n"
            "- Modify auth.py.\n"
            "- Add @router.post('/logout') returning a JSON response.\n\n"
            "CONSTRAINTS:\n"
            "- This is a static code modification task.\n"
            "- DO NOT run the application (no uvicorn, no npm).\n"
            "- DO NOT install dependencies.\n"
            "- JUST edit the files and confirm completion."
        )

        run_in_dir(goal, spec, workdir, max_steps=15)

        frontend_ok = check_file_contains(
            os.path.join(workdir, "frontend", "src", "components", "Header.vue"),
            ["Logout", "<button"],
            "Frontend: Logout button in Header.vue",
        )
        backend_ok = check_file_contains(
            os.path.join(workdir, "backend", "app", "routers", "auth.py"),
            ["logout"],
            "Backend: logout endpoint in auth.py",
        )
        return frontend_ok and backend_ok
    finally:
        cleanup(workdir)


if __name__ == "__main__":
    run_test(test_add_feature)
