"""
Simple E2E test - uses real DeepSeek V4 Flash API to run through the pipeline.

Usage:
  1. Start backend:  cd backend && uvicorn app.main:app --reload --port 8000
  2. Run test:       python scripts/test_simple_flow.py

Uses the simplest possible task to minimize API cost.
"""
import sys
import io
# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import time
import json

BASE = "http://localhost:8000/api"


def log(tag, msg):
    print(f"  [{tag}] {msg}")


def check_backend():
    try:
        r = requests.get(f"{BASE}/projects/", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def create_project():
    log("INFO", "Creating test project...")
    r = requests.post(f"{BASE}/projects/", json={
        "name": "Hello World Test",
        "description": "Testing real DeepSeek V4 Flash API pipeline",
        "requirements": "Write a Python function hello() that returns 'Hello, World!'. Code must be runnable.",
        "team_config": {},
        "created_by": "test-script"
    })
    r.raise_for_status()
    project = r.json()
    log("OK", f"Project created: {project['id'][:8]}...")
    return project


def list_agents():
    log("INFO", "Fetching available agents...")
    r = requests.get(f"{BASE}/agents/")
    r.raise_for_status()
    data = r.json()
    agents = data.get("agents", [])
    available = [a for a in agents if a.get("status") in ("idle", None)]
    log("OK", f"Found {len(available)} available agents")
    for a in available:
        print(f"       - {a['name']} ({a.get('type', 'unknown')})")
    return available


def create_pipeline(project_id, agent_ids):
    log("INFO", f"Creating pipeline with {len(agent_ids)} agents...")
    r = requests.post(f"{BASE}/pipelines/", json={
        "project_id": project_id,
        "name": "Test Pipeline",
        "agent_ids": agent_ids
    })
    r.raise_for_status()
    data = r.json()
    log("OK", f"Pipeline created: {data['id'][:8]}...")
    return data


def start_pipeline(pipeline_id):
    log("INFO", "Starting pipeline execution...")
    r = requests.post(f"{BASE}/pipelines/{pipeline_id}/start")
    r.raise_for_status()
    log("OK", "Pipeline started, waiting for completion...")


def poll_pipeline(pipeline_id, timeout=300):
    start = time.time()
    last_log_count = 0
    last_stage = ""

    while time.time() - start < timeout:
        try:
            r = requests.get(f"{BASE}/pipelines/{pipeline_id}", timeout=10)
            r.raise_for_status()
            pipeline = r.json()
        except Exception as e:
            print(f"       [WARN] Pipeline query error: {e}, retrying...")
            time.sleep(2)
            continue

        status = pipeline.get("status", "unknown")
        progress = pipeline.get("progress", 0)
        current_stage = pipeline.get("current_stage", "unknown")
        logs = pipeline.get("logs", [])

        # Print new logs
        for entry in logs[last_log_count:]:
            stage = entry.get("stage", "")
            msg = entry.get("message", "")
            level = entry.get("level", "info")
            prefix = {"error": "ERR", "warning": "WARN", "info": "   "}.get(level, "   ")
            print(f"       {prefix} [{stage}] {msg}")
        last_log_count = len(logs)

        # Print stage transitions
        if current_stage != last_stage:
            log("STAGE", f"-> {current_stage}")
            last_stage = current_stage

        if status in ("completed", "failed"):
            elapsed = time.time() - start
            log("DONE" if status == "completed" else "FAIL",
                f"Pipeline {status} (elapsed {elapsed:.0f}s, progress {progress:.0%})")
            return pipeline

        pct = int(progress * 100)
        print(f"       [...] status={status} stage={current_stage} progress={pct}% elapsed={time.time()-start:.0f}s")
        time.sleep(3)

    log("TIMEOUT", f"Pipeline did not complete within {timeout}s")
    return {}


def list_tasks(project_id):
    r = requests.get(f"{BASE}/tasks/", params={"project_id": project_id})
    r.raise_for_status()
    data = r.json()
    # API returns either a list or {"tasks": [...]}
    if isinstance(data, list):
        return data
    return data.get("tasks", [])


def get_project(project_id):
    r = requests.get(f"{BASE}/projects/{project_id}")
    r.raise_for_status()
    return r.json()


def print_summary(project, pipeline, tasks):
    print()
    print("=" * 60)
    print("  Execution Summary")
    print("=" * 60)
    print(f"  Project:      {project.get('name', '?')}")
    print(f"  Status:       {project.get('status', '?')}")
    print(f"  Pipeline:     {pipeline.get('status', '?')}")
    print(f"  Stage:        {pipeline.get('current_stage', '?')}")
    print(f"  Progress:     {pipeline.get('progress', 0):.0%}")
    print(f"  Tasks:        {len(tasks)}")
    print()

    for i, task in enumerate(tasks, 1):
        status = task.get("status", "?")
        title = task.get("title", "?")
        comments = task.get("comments", [])
        last_comment = comments[-1].get("content", "") if comments else ""
        print(f"  [{i}] [{status}] {title}")
        if last_comment:
            print(f"      {last_comment[:150]}")

    # Print requirement analysis summary
    context = pipeline.get("context", {})
    if context.get("requirement_analysis"):
        print()
        print("--- Requirement Analysis ---")
        print(context["requirement_analysis"][:600])

    print()
    print("=" * 60)


def main():
    print()
    print("=" * 60)
    print("  DevTeam-AI Simple E2E Test")
    print("  Model: deepseek-v4-flash (non-thinking)")
    print("=" * 60)
    print()

    # 1. Check backend
    log("CHECK", "Checking backend connection...")
    if not check_backend():
        log("FATAL", "Cannot connect to backend! Start it first:")
        print("       cd backend && uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    log("OK", "Backend is alive")

    # 2. Get agents
    agents = list_agents()
    if len(agents) < 1:
        log("FATAL", "No available agents. Check agent configuration.")
        sys.exit(1)
    # Take 2 agents
    selected = agents[:2]
    agent_ids = [a["id"] for a in selected]
    print(f"       Selected: {[a['name'] for a in selected]}")

    # 3. Create project
    project = create_project()

    # 4. Create pipeline
    pipeline_info = create_pipeline(project["id"], agent_ids)

    # 5. Start pipeline
    start_pipeline(pipeline_info["id"])

    # 6. Wait for completion
    print()
    log("WAIT", "Waiting for pipeline execution (each stage ~5-15s)...")
    print()
    pipeline = poll_pipeline(pipeline_info["id"], timeout=600)

    # 7. Get latest state
    project = get_project(project["id"])
    tasks = list_tasks(project["id"])

    # 8. Print summary
    print_summary(project, pipeline, tasks)


if __name__ == "__main__":
    main()
