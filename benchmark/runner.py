import os
import sys
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class TaskMeta:
    id: str
    name: str
    category: str
    difficulty: str
    language: str
    framework: str = ""
    timeout_seconds: int = 300
    max_agent_steps: int = 50
    setup_command: str = ""

    @classmethod
    def from_json(cls, path: str) -> "TaskMeta":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TaskResult:
    task_id: str
    task_name: str
    category: str
    difficulty: str
    success: bool
    tests_passed: int
    tests_failed: int
    tests_total: int
    test_output: str
    agent_steps: int
    time_seconds: float
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BenchmarkRunner:
    def __init__(
        self,
        tasks_dir: str = "benchmark/tasks",
        results_dir: str = "benchmark/results",
        workspaces_dir: str = "benchmark/workspaces",
    ):
        self.tasks_dir = Path(tasks_dir)
        self.results_dir = Path(results_dir)
        self.workspaces_dir = Path(workspaces_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)

    def discover_tasks(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[Path]:
        tasks = []
        if not self.tasks_dir.exists():
            print(f"Tasks directory not found: {self.tasks_dir}")
            return tasks

        for item in sorted(self.tasks_dir.iterdir()):
            if not item.is_dir():
                continue
            if not (item / "meta.json").exists():
                continue
            if not (item / "task.md").exists():
                continue

            meta = TaskMeta.from_json(str(item / "meta.json"))
            if category and meta.category != category:
                continue
            if difficulty and meta.difficulty != difficulty:
                continue
            tasks.append(item)

        return tasks

    def prepare_workspace(self, task_dir: Path, task_id: str) -> Path:
        workspace = self.workspaces_dir / task_id
        if workspace.exists():
            shutil.rmtree(workspace)

        project_src = task_dir / "project"
        tests_src = task_dir / "tests"

        if project_src.exists():
            shutil.copytree(project_src, workspace)
        else:
            workspace.mkdir(parents=True, exist_ok=True)

        if tests_src.exists():
            dst_tests = workspace / "tests"
            if dst_tests.exists():
                shutil.rmtree(dst_tests)
            shutil.copytree(tests_src, dst_tests)

        if not (workspace / "conftest.py").exists() and not (workspace / "pytest.ini").exists():
            conftest = workspace / "conftest.py"
            conftest.write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parent))\n",
                encoding="utf-8",
            )

        return workspace

    def install_deps(self, workspace: Path, meta: TaskMeta) -> bool:
        req_file = workspace / "requirements.txt"
        if req_file.exists():
            print(f"  Installing dependencies from requirements.txt...")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    capture_output=True, text=True, timeout=120,
                    encoding="utf-8", errors="replace",
                )
                if result.returncode != 0:
                    print(f"  pip install warning: {result.stderr[-500:]}")
            except Exception as e:
                print(f"  pip install error: {e}")

        if meta.setup_command:
            print(f"  Running setup: {meta.setup_command}")
            try:
                subprocess.run(
                    meta.setup_command, shell=True, cwd=str(workspace),
                    capture_output=True, text=True, timeout=120,
                    encoding="utf-8", errors="replace",
                )
            except Exception as e:
                print(f"  setup error: {e}")

        return True

    def run_verification(self, workspace: Path, timeout: int = 120, language: str = "python") -> Dict[str, Any]:
        if language in ("javascript", "typescript"):
            return self._run_js_verification(workspace, timeout)
        return self._run_py_verification(workspace, timeout)

    def _run_py_verification(self, workspace: Path, timeout: int) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return {
                "passed": 0,
                "failed": 0,
                "total": 0,
                "output": "Verification timed out",
                "success": False,
            }
        except Exception as e:
            return {
                "passed": 0,
                "failed": 0,
                "total": 0,
                "output": f"Verification error: {e}",
                "success": False,
            }

        output = result.stdout + result.stderr

        passed = 0
        failed = 0
        for line in output.splitlines():
            if " passed" in line and "failed" not in line.split("passed")[0]:
                try:
                    passed = int(line.split("passed")[0].strip().split()[-1])
                except (ValueError, IndexError):
                    pass
            if " failed" in line:
                try:
                    failed = int(line.split("failed")[0].strip().split()[-1])
                except (ValueError, IndexError):
                    pass
            if "passed" in line and "failed" in line:
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        try:
                            passed = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    if "failed" in part:
                        try:
                            failed = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass

        total = passed + failed
        return {
            "passed": passed,
            "failed": failed,
            "total": total,
            "output": output[-3000:] if len(output) > 3000 else output,
            "success": failed == 0 and passed > 0,
        }

    def _run_js_verification(self, workspace: Path, timeout: int) -> Dict[str, Any]:
        test_files = list((workspace / "tests").glob("test_*.js")) + list((workspace / "tests").glob("*_test.js")) + list((workspace / "tests").glob("test_*.cjs")) + list((workspace / "tests").glob("*_test.cjs"))
        if not test_files:
            return {"passed": 0, "failed": 0, "total": 0, "output": "No JS test files found", "success": False}

        all_output = []
        total_passed = 0
        total_failed = 0

        for tf in test_files:
            try:
                result = subprocess.run(
                    ["node", str(tf.relative_to(workspace))],
                    cwd=str(workspace),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="replace",
                )
            except FileNotFoundError:
                return {"passed": 0, "failed": 0, "total": 0, "output": "node not found", "success": False}
            except subprocess.TimeoutExpired:
                return {"passed": 0, "failed": 0, "total": 0, "output": "JS tests timed out", "success": False}
            except Exception as e:
                return {"passed": 0, "failed": 0, "total": 0, "output": f"JS test error: {e}", "success": False}

            output = result.stdout + result.stderr
            all_output.append(output)

            for line in output.splitlines():
                if line.startswith("PASS:"):
                    total_passed += 1
                elif line.startswith("FAIL:"):
                    total_failed += 1

        combined = "\n".join(all_output)
        return {
            "passed": total_passed,
            "failed": total_failed,
            "total": total_passed + total_failed,
            "output": combined[-3000:] if len(combined) > 3000 else combined,
            "success": total_failed == 0 and total_passed > 0,
        }

    def run_agent(self, task_dir: Path, workspace: Path, meta: TaskMeta) -> Dict[str, Any]:
        task_md = (task_dir / "task.md").read_text(encoding="utf-8")

        src_dir = str(Path(__file__).parent.parent / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        os.environ['BENCHMARK_MODE'] = '1'
        os.environ['PYTHONIOENCODING'] = 'utf-8'

        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        if hasattr(sys.stderr, 'reconfigure'):
            try:
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

        try:
            from lg_agent import create_agent, get_initial_state

            import lg_agent as lg_agent_module
            original_ask = lg_agent_module.ask
            lg_agent_module.ask = lambda: ""

            state = get_initial_state(
                goal=task_md,
                prjdir=str(workspace),
                max_steps=meta.max_agent_steps,
            )

            agent = create_agent()
            config = {"recursion_limit": 250}

            start_time = time.time()
            try:
                final_state = agent.invoke(state, config=config)
            except Exception as e:
                return {"steps": 0, "time": time.time() - start_time, "error": str(e)}
            finally:
                lg_agent_module.ask = original_ask

            elapsed = time.time() - start_time
            steps = final_state.get("iterations", 0) if isinstance(final_state, dict) else 0

            return {"steps": steps, "time": elapsed, "error": None}

        except ImportError as e:
            print(f"  Cannot import agent: {e}")
            print("  Skipping agent run (dry-run verification only)")
            return {"steps": 0, "time": 0, "error": "agent not available"}
        except Exception as e:
            print(f"  Agent runtime error: {e}")
            return {"steps": 0, "time": time.time() - start_time if 'start_time' in dir() else 0, "error": str(e)}

    def run_single_task(self, task_dir: Path, dry_run: bool = False) -> TaskResult:
        meta = TaskMeta.from_json(str(task_dir / "meta.json"))
        task_name = meta.name

        print(f"\n{'='*60}")
        print(f"Task: {task_name} ({meta.id})")
        print(f"Category: {meta.category} | Difficulty: {meta.difficulty} | Lang: {meta.language}")
        print(f"{'='*60}")

        workspace = self.prepare_workspace(task_dir, meta.id)
        print(f"Workspace: {workspace}")

        self.install_deps(workspace, meta)

        print("\nPre-verification (tests should FAIL)...")
        pre = self.run_verification(workspace, timeout=meta.timeout_seconds, language=meta.language)
        print(f"  Pre: {pre['passed']} passed, {pre['failed']} failed")

        if not dry_run:
            print(f"\nRunning agent (max {meta.max_agent_steps} steps)...")
            agent_result = self.run_agent(task_dir, workspace, meta)
            if agent_result.get("error"):
                print(f"  Agent error: {agent_result['error']}")
        else:
            agent_result = {"steps": 0, "time": 0, "error": None}
            print("\n  (dry-run: skipping agent)")

        print("\nPost-verification (tests should PASS)...")
        post = self.run_verification(workspace, timeout=meta.timeout_seconds, language=meta.language)
        print(f"  Post: {post['passed']} passed, {post['failed']} failed")

        success = post["success"]
        print(f"\n  RESULT: {'SUCCESS' if success else 'FAILED'}")

        result = TaskResult(
            task_id=meta.id,
            task_name=task_name,
            category=meta.category,
            difficulty=meta.difficulty,
            success=success,
            tests_passed=post["passed"],
            tests_failed=post["failed"],
            tests_total=post["total"],
            test_output=post["output"],
            agent_steps=agent_result.get("steps", 0),
            time_seconds=agent_result.get("time", 0),
            error=agent_result.get("error"),
        )

        self._save_result(result)
        return result

    def run_all(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[TaskResult]:
        tasks = self.discover_tasks(category=category, difficulty=difficulty)
        if not tasks:
            print("No tasks found.")
            return []

        print(f"Found {len(tasks)} task(s)")

        results = []
        for task_dir in tasks:
            result = self.run_single_task(task_dir, dry_run=dry_run)
            results.append(result)

        self._print_summary(results)
        self._save_summary(results)
        return results

    def _save_result(self, result: TaskResult):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.results_dir / f"{result.task_id}_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, indent=2, ensure_ascii=False)
        print(f"  Result saved: {path}")

    def _save_summary(self, results: List[TaskResult]):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.results_dir / f"summary_{ts}.json"

        total = len(results)
        successes = sum(1 for r in results if r.success)
        by_category: Dict[str, Dict[str, Any]] = {}

        for r in results:
            cat = r.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "success": 0, "avg_time": 0, "times": []}
            by_category[cat]["total"] += 1
            if r.success:
                by_category[cat]["success"] += 1
            by_category[cat]["times"].append(r.time_seconds)

        for cat in by_category:
            times = by_category[cat].pop("times")
            by_category[cat]["avg_time"] = sum(times) / len(times) if times else 0
            by_category[cat]["rate"] = (
                by_category[cat]["success"] / by_category[cat]["total"] * 100
                if by_category[cat]["total"] > 0 else 0
            )

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": total,
            "total_success": successes,
            "overall_rate": successes / total * 100 if total > 0 else 0,
            "by_category": by_category,
            "tasks": [asdict(r) for r in results],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\nSummary saved: {path}")

    def _print_summary(self, results: List[TaskResult]):
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")

        total = len(results)
        successes = sum(1 for r in results if r.success)

        for r in results:
            status = "PASS" if r.success else "FAIL"
            print(f"  [{status}] {r.task_id} ({r.category}/{r.difficulty}) "
                  f"- {r.tests_passed}/{r.tests_total} tests, "
                  f"{r.agent_steps} steps, {r.time_seconds:.1f}s")

        print(f"\n  Total: {successes}/{total} passed ({successes/total*100:.0f}%)")


class SWEBenchAdapter:
    def __init__(self, cache_dir: str = "benchmark/swe_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._dataset = None

    def _load_dataset(self):
        if self._dataset is not None:
            return self._dataset

        try:
            from datasets import load_dataset
            print("Loading SWE-bench Verified dataset from huggingface...")
            ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
            self._dataset = ds
            print(f"  Loaded {len(ds)} tasks")
            return ds
        except ImportError:
            print("ERROR: 'datasets' package not installed.")
            print("  Install with: pip install datasets")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR loading dataset: {e}")
            sys.exit(1)

    def list_tasks(self, limit: int = 0):
        ds = self._load_dataset()
        count = 0
        for row in ds:
            print(f"  {row['instance_id']:50s} {row.get('repo', ''):30s}")
            count += 1
            if limit and count >= limit:
                break
        print(f"\n  Total shown: {count} / {len(ds)}")

    def _clone_repo(self, repo: str, base_commit: str, work_dir: Path) -> bool:
        if work_dir.exists():
            shutil.rmtree(work_dir)

        repo_url = f"https://github.com/{repo}.git"
        print(f"  Cloning {repo} at {base_commit[:8]}...")

        try:
            subprocess.run(
                ["git", "clone", repo_url, str(work_dir)],
                capture_output=True, text=True, timeout=300,
            )
            subprocess.run(
                ["git", "checkout", base_commit],
                cwd=str(work_dir), capture_output=True, text=True, timeout=60,
            )
            return True
        except FileNotFoundError:
            print("  ERROR: git not found. Install git and add to PATH.")
            return False
        except subprocess.TimeoutExpired:
            print("  ERROR: git clone timed out")
            return False
        except Exception as e:
            print(f"  ERROR cloning repo: {e}")
            return False

    def _get_test_command(self, repo: str) -> str:
        test_commands = {
            "django/django": "python -m pytest tests/ -x -q",
            "scikit-learn/scikit-learn": "python -m pytest sklearn/tests/ -x -q",
            "matplotlib/matplotlib": "python -m pytest lib/matplotlib/tests/ -x -q",
            "flask/flask": "python -m pytest tests/ -x -q",
            "sympy/sympy": "python -m pytest sympy/ -x -q",
            "pydata/xarray": "python -m pytest xarray/tests/ -x -q",
            "pallets/werkzeug": "python -m pytest tests/ -x -q",
        }
        return test_commands.get(repo, "python -m pytest -x -q")

    def run_single(self, instance_id: str, dry_run: bool = False) -> TaskResult:
        ds = self._load_dataset()
        row = None
        for r in ds:
            if r["instance_id"] == instance_id:
                row = r
                break
        if row is None:
            print(f"Task not found: {instance_id}")
            return TaskResult(
                task_id=instance_id, task_name=instance_id, category="swe-bench",
                difficulty="unknown", success=False, tests_passed=0, tests_failed=0,
                tests_total=0, test_output="Task not found", agent_steps=0, time_seconds=0,
            )

        repo = row["repo"]
        base_commit = row["base_commit"]
        problem = row.get("problem_statement", "")
        hints_text = row.get("hints_text", "")

        work_dir = self.cache_dir / "workspaces" / instance_id.replace("/", "__")
        if not self._clone_repo(repo, base_commit, work_dir):
            return TaskResult(
                task_id=instance_id, task_name=instance_id, category="swe-bench",
                difficulty="unknown", success=False, tests_passed=0, tests_failed=0,
                tests_total=0, test_output="Clone failed", agent_steps=0, time_seconds=0,
            )

        task_md = f"# SWE-bench Task: {instance_id}\n\n## Problem\n{problem}\n"
        if hints_text:
            task_md += f"\n## Hints\n{hints_text}\n"
        task_md += f"\n## Repository\n{repo} at commit {base_commit[:8]}"

        req_file = work_dir / "requirements.txt"
        if req_file.exists():
            print("  Installing project dependencies...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(work_dir)],
                capture_output=True, text=True, timeout=300,
            )

        test_cmd = self._get_test_command(repo)
        print("  Pre-verification...")
        pre = self._run_repo_tests(work_dir, test_cmd)
        print(f"  Pre: {pre['passed']} passed, {pre['failed']} failed")

        if not dry_run:
            try:
                from lg_agent import create_agent, get_initial_state
                state = get_initial_state(
                    goal=task_md, spec="", prjdir=str(work_dir),
                    max_steps=50, action_memory_size=10,
                )
                agent = create_agent(commits_enabled=False)
                start = time.time()
                try:
                    agent.invoke(state, config={"recursion_limit": 300})
                except Exception as e:
                    print(f"  Agent error: {e}")
                elapsed = time.time() - start
                agent_steps = state.get("iter_cnt", 0)
            except ImportError:
                print("  Agent not available, skipping")
                agent_steps = 0
                elapsed = 0
        else:
            agent_steps = 0
            elapsed = 0

        print("  Post-verification...")
        post = self._run_repo_tests(work_dir, test_cmd)
        print(f"  Post: {post['passed']} passed, {post['failed']} failed")

        success = post["success"] and post["passed"] > pre["passed"]
        print(f"  RESULT: {'SUCCESS' if success else 'FAILED'}")

        return TaskResult(
            task_id=instance_id, task_name=instance_id, category="swe-bench",
            difficulty="unknown", success=success,
            tests_passed=post["passed"], tests_failed=post["failed"],
            tests_total=post["total"], test_output=post["output"],
            agent_steps=agent_steps, time_seconds=elapsed,
        )

    def _run_repo_tests(self, work_dir: Path, test_cmd: str, timeout: int = 300) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                test_cmd, shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return {"passed": 0, "failed": 0, "total": 0, "output": "Tests timed out", "success": False}
        except Exception as e:
            return {"passed": 0, "failed": 0, "total": 0, "output": str(e), "success": False}

        output = result.stdout + result.stderr
        passed = failed = 0
        for line in output.splitlines():
            if " passed" in line:
                try:
                    parts = line.split("passed")[0].strip().split()
                    passed = int(parts[-1]) if parts else 0
                except (ValueError, IndexError):
                    pass
            if " failed" in line:
                try:
                    parts = line.split("failed")[0].strip().split()
                    failed = int(parts[-1]) if parts else 0
                except (ValueError, IndexError):
                    pass
            if "passed" in line and "failed" in line:
                for segment in line.split(","):
                    s = segment.strip()
                    if "passed" in s:
                        try: passed = int(s.split()[0])
                        except: pass
                    if "failed" in s:
                        try: failed = int(s.split()[0])
                        except: pass

        return {
            "passed": passed, "failed": failed,
            "total": passed + failed,
            "output": output[-3000:] if len(output) > 3000 else output,
            "success": failed == 0 and passed > 0,
        }

    def run_batch(self, limit: int = 10, dry_run: bool = False) -> List[TaskResult]:
        ds = self._load_dataset()
        results = []
        for i, row in enumerate(ds):
            if limit and i >= limit:
                break
            print(f"\n[{i+1}/{min(limit, len(ds))}]", end="")
            result = self.run_single(row["instance_id"], dry_run=dry_run)
            results.append(result)
        return results


def main():
    parser = argparse.ArgumentParser(description="SWE-bench style benchmark runner")
    parser.add_argument("--task", "-t", help="Task ID to run")
    parser.add_argument("--category", "-c", help="Filter by category (bugfix/feature/refactor/create)")
    parser.add_argument("--difficulty", "-d", help="Filter by difficulty (easy/medium/hard)")
    parser.add_argument("--all", "-a", action="store_true", help="Run all tasks")
    parser.add_argument("--dry-run", action="store_true", help="Only run verification, skip agent")
    parser.add_argument("--list", "-l", action="store_true", help="List available tasks")

    parser.add_argument("--swe-bench", action="store_true", help="Use SWE-bench Verified dataset")
    parser.add_argument("--swe-limit", type=int, default=10, help="Max SWE-bench tasks to run (default: 10)")

    args = parser.parse_args()

    if args.swe_bench:
        swe = SWEBenchAdapter()
        if args.list or not args.task:
            swe.list_tasks(limit=args.swe_limit)
        if args.task:
            swe.run_single(args.task, dry_run=args.dry_run)
        elif not args.list:
            swe.run_batch(limit=args.swe_limit, dry_run=args.dry_run)
        return

    runner = BenchmarkRunner()

    if args.list:
        tasks = runner.discover_tasks(category=args.category, difficulty=args.difficulty)
        for t in tasks:
            meta = TaskMeta.from_json(str(t / "meta.json"))
            print(f"  {meta.id:30s} {meta.category:10s} {meta.difficulty:8s} {meta.language:12s} {meta.name}")
        print(f"\n  Total: {len(tasks)} tasks")
        return

    if args.task:
        task_dir = runner.tasks_dir / args.task
        if not task_dir.exists():
            print(f"Task not found: {args.task}")
            return
        runner.run_single_task(task_dir, dry_run=args.dry_run)
    else:
        runner.run_all(category=args.category, difficulty=args.difficulty, dry_run=args.dry_run)


if __name__ == "__main__":
    main()