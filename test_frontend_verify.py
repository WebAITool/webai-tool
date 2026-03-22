import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from frontend_check import check_frontend, FrontendChecker


def test_frontend_verify(project_path: str):
    frontend_path = Path(project_path) / "frontend"
    
    if not frontend_path.exists():
        frontend_path = Path(project_path)
        if not (frontend_path / "package.json").exists():
            print(f"No package.json in {frontend_path}")
            return False

    print(f"Frontend: {frontend_path}")
    
    checker = FrontendChecker()
    
    if not checker.start_dev_server(frontend_path):
        print("Dev server failed to start")
        return False

    try:
        screenshot_path = checker.take_screenshot(
            url="http://localhost:5173",
            output_path=str(frontend_path / "test_screenshot.png")
        )
        
        if not screenshot_path:
            print("Screenshot failed")
            return False
        
        print(f"Screenshot: {screenshot_path}")
        
        analysis = checker.analyze_ui(
            screenshot_path,
            goal="Test frontend application",
            spec="Testing the frontend verification system"
        )
        
        print(f"\nAnalysis:\n{analysis}")
        return True

    finally:
        checker.stop_dev_server()


def test_check_frontend(project_path: str):
    success, feedback = check_frontend(
        prjdir=project_path,
        goal="Test frontend application",
        spec="Testing the frontend verification system"
    )
    
    print(f"Success: {success}")
    print(f"Feedback: {feedback}")
    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_frontend_verify.py <project_path>")
        sys.exit(1)

    project_path = sys.argv[1]
    
    if not Path(project_path).exists():
        print(f"Path not found: {project_path}")
        sys.exit(1)

    success = test_frontend_verify(project_path)
    sys.exit(0 if success else 1)