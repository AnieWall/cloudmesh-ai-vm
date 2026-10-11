import os
import subprocess
import datetime
from io import StringIO
from contextlib import redirect_stdout
import yaml

def save_benchmark(tag, config_path):
    """
    Captures the output of StopWatch.benchmark and saves it to a file in the results directory.
    """
    from cloudmesh.ai.common.stopwatch import StopWatch

    # 1. Capture the benchmark output
    f = StringIO()
    with redirect_stdout(f):
        StopWatch.benchmark(tag=tag)
    benchmark_output = f.getvalue()

    # 2. Collect Metadata
    # Git info
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        git_info = f"Branch: {branch}\nCommit: {commit}"
    except Exception:
        git_info = "Git info unavailable"

    # Username from config
    try:
        with open(config_path, "r") as cf:
            config = yaml.safe_load(cf)
            username = config.get("username", "unknown")
    except Exception:
        username = "unknown"

    # Date
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. Write to file
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    # Sanitize tag for filename
    safe_tag = tag.replace(" ", "_").replace("/", "_").replace(":", "_")
    # Use a timestamp to ensure unique files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_tag}_{timestamp}.txt"
    file_path = os.path.join(results_dir, filename)

    with open(file_path, "w") as rf:
        rf.write(f"Benchmark: {tag}\n")
        rf.write(f"Date: {date_str}\n")
        rf.write(f"User: {username}\n")
        rf.write(f"{git_info}\n")
        rf.write("-" * 40 + "\n")
        rf.write(benchmark_output)

    print(f"Benchmark saved to {file_path}")
