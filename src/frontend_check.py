import os
import subprocess
import time
import base64
import signal
from pathlib import Path
from typing import Optional, Tuple
import dotenv

from openai import OpenAI

dotenv.load_dotenv()


class FrontendChecker:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("API_KEY")
        self.client = OpenAI(
            base_url="https://polza.ai/api/v1",
            api_key=self.api_key
        )
        self.dev_process = None

    def start_dev_server(self, frontend_path: Path, port: int = 5173) -> bool:
        if not frontend_path.exists():
            print(f"Frontend path does not exist: {frontend_path}")
            return False

        package_json = frontend_path / "package.json"
        if not package_json.exists():
            print(f"No package.json found in {frontend_path}")
            return False

        try:
            self.dev_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", str(port)],
                cwd=str(frontend_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            print(f"Starting dev server on port {port}...")
            time.sleep(5)
            return True
        except Exception as e:
            print(f"Failed to start dev server: {e}")
            return False

    def stop_dev_server(self):
        if self.dev_process:
            self.dev_process.terminate()
            try:
                self.dev_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.dev_process.kill()
            self.dev_process = None
            print("Dev server stopped")

    def take_screenshot(
        self,
        url: str = "http://localhost:5173",
        output_path: Optional[str] = None,
        timeout: int = 10000
    ) -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(timeout)

                print(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle")

                if output_path is None:
                    output_path = "screenshot.png"

                page.screenshot(path=output_path, full_page=True)
                print(f"Screenshot saved to {output_path}")

                browser.close()

                return output_path
        except ImportError:
            print("Playwright not installed. Run: pip install playwright && playwright install")
            return None
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return None

    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def analyze_ui(
        self,
        screenshot_path: str,
        goal: str = "",
        spec: str = ""
    ) -> str:
        try:
            image_base64 = self.encode_image(screenshot_path)

            prompt = f"""Analyze this frontend UI screenshot.

Goal of the project: {goal if goal else "Build a web application"}

Specification: {spec if spec else "Not provided"}

Please analyze:
1. Layout: is the layout reasonable? Are elements properly positioned?
2. Visual Design: are colors, fonts, and spacing appropriate?
3. Usability: can users easily understand and interact with the interface?
4. Completeness: does the UI match the goal and specification?
5. Issues: what problems or improvements do you see?

Provide specific, actionable feedback that a developer can use to improve the UI."""

            response = self.client.chat.completions.create(
                model="qwen/qwen3-vl-8b-thinking",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )

            return response.choices[0].message.content
        except Exception as e:
            return f"UI analysis failed: {e}"

    def verify_frontend(
        self,
        frontend_path: Path,
        goal: str = "",
        spec: str = "",
        port: int = 5173
    ) -> Tuple[bool, str]:
        results = []

        if not frontend_path.exists():
            return False, f"Frontend path does not exist: {frontend_path}"

        if not self.start_dev_server(frontend_path, port):
            return False, "Failed to start dev server"

        try:
            screenshot_path = self.take_screenshot(
                url=f"http://localhost:{port}",
                output_path=str(frontend_path / "screenshot.png")
            )

            if not screenshot_path:
                return False, "Failed to take screenshot"

            analysis = self.analyze_ui(screenshot_path, goal, spec)
            results.append(f"[UI ANALYSIS]\n{analysis}")

            success = "error" not in analysis.lower() and "fail" not in analysis.lower()

            return success, "\n".join(results)

        finally:
            self.stop_dev_server()


def check_frontend(
    prjdir: str,
    goal: str = "",
    spec: str = ""
) -> Tuple[bool, str]:
    frontend_path = Path(prjdir) / "frontend"

    if not frontend_path.exists():
        return True, "No frontend directory found, skipping frontend check"

    checker = FrontendChecker()
    return checker.verify_frontend(frontend_path, goal, spec)