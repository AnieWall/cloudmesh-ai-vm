import os
import subprocess
import datetime
import json
from io import StringIO
from contextlib import redirect_stdout
import yaml

def get_results_username(config_path: Optional[str] = None) -> str:
    """
    Determines the username for result filenames.
    Only uses ~/.config/cloudmesh/clouds.yaml.
    If not found, raises a RuntimeError asking the user to set it.
    """
    # Try ~/.config/cloudmesh/clouds.yaml
    global_config_path = os.path.expanduser("~/.config/cloudmesh/clouds.yaml")
    try:
        if os.path.exists(global_config_path):
            with open(global_config_path, "r") as cf:
                config = yaml.safe_load(cf)
                if config and isinstance(config, dict):
                    username = config.get("username")
                    if username:
                        return username.replace("cloudmesh-", "")
    except Exception:
        pass

    # No fallback to config_path or 'unknown-user' as per user request
    raise RuntimeError(
        "Username is missing from the global configuration file ~/.config/cloudmesh/clouds.yaml. "
        "Please set the 'username' field in the YAML file to run benchmarks."
    )


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
        git_data = {"branch": branch, "commit": commit}
    except Exception:
        git_info = "Git info unavailable"
        git_data = {}

    # Username from config
    username = get_results_username(config_path)

    # Date
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_short = now.strftime("%Y%m%d")

    # 3. Write to file
    results_dir = "results/smoke"
    os.makedirs(results_dir, exist_ok=True)

    # Sanitize tag for filename (use - instead of _ to match requested example)
    safe_tag = tag.replace(" ", "-").replace("/", "-").replace(":", "-")

    # Use a timestamp to ensure unique files, but place it before the username/date
    # to ensure the filename ends with -<username>-<date>
    timestamp = now.strftime("%H%M%S")

    # Format: <safe_tag>-<timestamp>-<username>-<date>
    # This ensures it ends with -<username>-<date> as requested
    filename_base = f"{safe_tag}-{timestamp}-{username}-{date_short}"

    # Text version
    txt_filename = f"{filename_base}.txt"
    txt_file_path = os.path.join(results_dir, txt_filename)
    with open(txt_file_path, "w") as rf:
        rf.write(f"Benchmark: {tag}\n")
        rf.write(f"Date: {date_str}\n")
        rf.write(f"User: {username}\n")
        rf.write(f"{git_info}\n")
        rf.write("-" * 40 + "\n")
        rf.write(benchmark_output)

    # JSON version
    json_filename = f"{filename_base}.json"
    json_file_path = os.path.join(results_dir, json_filename)

    results_data = {
        "benchmark": tag,
        "date": date_str,
        "user": username,
        "git_info": git_data,
        "output": benchmark_output
    }
    with open(json_file_path, "w") as jf:
        json.dump(results_data, jf, indent=4)

    print(f"Benchmark saved to {txt_file_path} and {json_file_path}")
