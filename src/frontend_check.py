import os
import subprocess
import time
import base64
import re
from pathlib import Path
from typing import Optional, Tuple, List
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

    def discover_routes(self, frontend_path: Path) -> List[str]:
        routes = ["/"]
        
        router_patterns = [
            r'path:\s*["\']([^"\']+)["\']',
            r'to:\s*["\']([^"\']+)["\']',
            r'href:\s*["\']([^"\']+)["\']',
        ]
        
        router_files = [
            "router/index.js", "router/index.ts",
            "src/router/index.js", "src/router/index.ts",
            "src/router.js", "src/router.ts",
        ]
        
        for router_file in router_files:
            router_path = frontend_path / router_file
            if router_path.exists():
                content = router_path.read_text(encoding='utf-8')
                for pattern in router_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if match.startswith('/') and match not in routes:
                            routes.append(match)
        
        return routes[:10]

    def crawl_links(self, base_url: str, max_pages: int = 10) -> List[str]:
        try:
            from playwright.sync_api import sync_playwright
            
            routes = ["/"]
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.goto(base_url, wait_until="networkidle")
                
                links = page.query_selector_all("a[href]")
                for link in links:
                    href = link.get_attribute("href")
                    if href and href.startswith('/') and href not in routes:
                        routes.append(href)
                        if len(routes) >= max_pages:
                            break
                
                browser.close()
            
            return routes
        except Exception:
            return ["/"]

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
        route: str = "/",
        goal: str = "",
        spec: str = "",
        max_tokens: int = 4000
    ) -> str:
        try:
            image_base64 = self.encode_image(screenshot_path)

            prompt = f"""Analyze this frontend UI screenshot for route '{route}'.

Goal: {goal if goal else "Build a web application"}
Spec: {spec if spec else "Not provided"}

Analyze:
1. Layout and positioning
2. Visual design (colors, fonts, spacing)
3. Usability and accessibility
4. Completeness vs goal/spec
5. Issues and improvements

Provide actionable feedback."""

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
                max_tokens=max_tokens
            )

            return response.choices[0].message.content
        except Exception as e:
            return f"Analysis failed: {e}"

    def verify_frontend(
        self,
        frontend_path: Path,
        goal: str = "",
        spec: str = "",
        port: int = 5173,
        max_pages: int = 10,
        max_tokens: int = 4000
    ) -> Tuple[bool, str]:
        results = []

        if not frontend_path.exists():
            return False, f"Frontend path does not exist: {frontend_path}"

        if not self.start_dev_server(frontend_path, port):
            return False, "Failed to start dev server"

        try:
            base_url = f"http://localhost:{port}"
            
            routes = self.discover_routes(frontend_path)
            routes = self.crawl_links(base_url, max_pages)
            routes = list(dict.fromkeys(routes))[:max_pages]
            
            print(f"Found {len(routes)} routes: {routes}")
            
            all_success = True
            
            for route in routes:
                url = base_url + route
                safe_route = route.replace("/", "_").strip("_") or "home"
                screenshot_path = str(frontend_path / f"screenshot_{safe_route}.png")
                
                screenshot = self.take_screenshot(url=url, output_path=screenshot_path)
                
                if not screenshot:
                    results.append(f"[{route}] Screenshot failed")
                    all_success = False
                    continue
                
                analysis = self.analyze_ui(screenshot, route, goal, spec, max_tokens)
                results.append(f"[{route}]\n{analysis}\n")
                
                if "error" in analysis.lower() or "fail" in analysis.lower():
                    all_success = False

            return all_success, "\n".join(results)

        finally:
            self.stop_dev_server()


def check_frontend(
    prjdir: str,
    goal: str = "",
    spec: str = ""
) -> Tuple[bool, str]:
    prjdir_path = Path(prjdir)
    
    # Find project root (where package.json is)
    project_root = prjdir_path
    if not (project_root / "package.json").exists():
        # Check if it's in a subdirectory structure
        for parent in prjdir_path.parents:
            if (parent / "package.json").exists():
                project_root = parent
                break
    
    if not (project_root / "package.json").exists():
        return True, "No package.json found"

    checker = FrontendChecker()
    return checker.verify_frontend(project_root, goal, spec)