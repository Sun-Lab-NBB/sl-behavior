#!/usr/bin/env python3
"""Profiles memory usage for behavior data processing with parallel workers.

Measures peak memory during actual processing by monitoring /proc/[pid]/status
to capture total memory across all worker processes.

This provides realistic SLURM memory allocation requirements.
"""

import os
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ProcessingProfile:
    """Stores memory profiling results for a processing run."""

    job_type: str
    input_file: str
    input_size_bytes: int
    peak_memory_mb: float
    elapsed_seconds: float
    workers: int


def format_size(size_bytes: int) -> str:
    """Formats bytes as human-readable string."""
    if size_bytes >= 1024**3:
        return f"{size_bytes / (1024**3):.1f}G"
    if size_bytes >= 1024**2:
        return f"{size_bytes / (1024**2):.1f}M"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f}K"
    return f"{size_bytes}B"


def get_process_tree_memory_kb(pid: int) -> int:
    """Returns total RSS memory in KB for a process and all its children.

    Uses /proc filesystem on Linux.
    """
    total_rss = 0
    try:
        # Get memory of main process
        status_file = Path(f"/proc/{pid}/status")
        if status_file.exists():
            content = status_file.read_text()
            for line in content.split("\n"):
                if line.startswith("VmRSS:"):
                    total_rss += int(line.split()[1])
                    break

        # Get memory of all child processes
        children_file = Path(f"/proc/{pid}/task/{pid}/children")
        if children_file.exists():
            children = children_file.read_text().strip().split()
            for child_pid in children:
                total_rss += get_process_tree_memory_kb(int(child_pid))
        else:
            # Alternative: scan /proc for processes with this parent
            for proc_dir in Path("/proc").iterdir():
                if proc_dir.name.isdigit():
                    try:
                        stat_file = proc_dir / "stat"
                        if stat_file.exists():
                            stat_content = stat_file.read_text()
                            # Format: pid (comm) state ppid ...
                            parts = stat_content.split()
                            if len(parts) > 3:
                                ppid = int(parts[3])
                                if ppid == pid:
                                    total_rss += get_process_tree_memory_kb(int(proc_dir.name))
                    except (PermissionError, ProcessLookupError, FileNotFoundError):
                        pass
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass

    return total_rss


class MemoryMonitor:
    """Monitors peak memory usage of a subprocess tree."""

    def __init__(self, pid: int, poll_interval: float = 0.1):
        self.pid = pid
        self.poll_interval = poll_interval
        self.peak_memory_kb = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                current_kb = get_process_tree_memory_kb(self.pid)
                if current_kb > self.peak_memory_kb:
                    self.peak_memory_kb = current_kb
            except Exception:
                pass
            time.sleep(self.poll_interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> int:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        return self.peak_memory_kb


def run_processing_with_memory_tracking(
    session_path: Path,
    job_flag: str,
    workers: int = 30,
) -> tuple[int, float]:
    """Runs processing and returns (peak_memory_kb, elapsed_seconds)."""
    cmd = ["sl-behavior", "process", "--session-path", str(session_path), "--workers", str(workers), job_flag]

    start_time = time.time()

    # Start subprocess
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Start memory monitoring
    monitor = MemoryMonitor(proc.pid, poll_interval=0.05)
    monitor.start()

    # Wait for process to complete
    stdout, stderr = proc.communicate()

    # Stop monitoring and get peak memory
    peak_kb = monitor.stop()
    elapsed_sec = time.time() - start_time

    return peak_kb, elapsed_sec


def setup_test_session(source_session: Path, temp_dir: Path, log_files: list[str]) -> Path:
    """Creates a minimal test session with only the necessary files for profiling."""
    test_session = temp_dir / source_session.name
    raw_data = test_session / "raw_data"
    behavior_data = raw_data / "behavior_data"
    tracking_data = test_session / "tracking_data"

    # Create directory structure
    behavior_data.mkdir(parents=True, exist_ok=True)
    tracking_data.mkdir(parents=True, exist_ok=True)

    # Copy essential session files
    source_raw = source_session / "raw_data"
    for yaml_file in ["session_data.yaml", "hardware_state.yaml"]:
        src = source_raw / yaml_file
        if src.exists():
            shutil.copy2(src, raw_data / yaml_file)

    # Copy specified log files
    source_behavior = source_raw / "behavior_data"
    for log_file in log_files:
        src = source_behavior / log_file
        if src.exists():
            shutil.copy2(src, behavior_data / log_file)

    return test_session


def main() -> None:
    # Sessions to profile (with varying file sizes)
    source_sessions = [
        Path("/home/data/MaalstroomicFlow/11/2025-07-13-18-28-09-495709"),  # Small
        Path("/home/data/StateSpaceOdyssey/26/2025-08-28-18-58-02-766013"),  # Medium
        Path("/home/data/StateSpaceOdyssey/14/2025-08-22-16-32-29-378081"),  # Large
    ]

    # Job configurations: (job_type, cli_flag, log_files_needed)
    job_configs = [
        ("runtime", "--runtime", ["1_log.npz"]),
        ("face_camera", "--face-camera", ["51_log.npz"]),
        ("body_camera", "--body-camera", ["62_log.npz"]),
        ("actor_mc", "--actor", ["101_log.npz"]),
        ("sensor_mc", "--sensor", ["152_log.npz"]),
        ("encoder_mc", "--encoder", ["203_log.npz"]),
    ]

    workers = 30  # Standard allocation

    print("=" * 90)
    print(f"Memory Profiling with {workers} Workers (SLURM-realistic)")
    print("=" * 90)
    print()
    print("This runs actual processing jobs with full parallelization to measure")
    print("real-world memory requirements including all worker processes.")
    print("Memory is monitored via /proc filesystem at 50ms intervals.")
    print()

    all_results: list[dict[str, Any]] = []

    for source_session in source_sessions:
        session_name = source_session.name
        project = source_session.parent.parent.name
        source_behavior = source_session / "raw_data" / "behavior_data"

        print(f"\n{'=' * 70}")
        print(f"Session: {project}/{session_name}")
        print(f"{'=' * 70}")

        for job_type, cli_flag, log_files in job_configs:
            # Check if log file exists
            log_file = log_files[0]
            log_path = source_behavior / log_file
            if not log_path.exists():
                print(f"  {job_type}: SKIPPED (file not found)")
                continue

            file_size = log_path.stat().st_size
            print(f"  {job_type} ({format_size(file_size)}): ", end="", flush=True)

            try:
                # Create temporary test session
                with tempfile.TemporaryDirectory() as temp_dir:
                    test_session = setup_test_session(source_session, Path(temp_dir), log_files)

                    # Run processing with memory tracking
                    peak_kb, elapsed_sec = run_processing_with_memory_tracking(test_session, cli_flag, workers=workers)

                    peak_mb = peak_kb / 1024
                    print(f"peak={peak_mb:.0f}MB, time={elapsed_sec:.1f}s")

                    all_results.append(
                        {
                            "project": project,
                            "session": session_name,
                            "job_type": job_type,
                            "log_file": log_file,
                            "input_size_bytes": file_size,
                            "input_size_human": format_size(file_size),
                            "peak_memory_mb": round(peak_mb, 1),
                            "elapsed_seconds": round(elapsed_sec, 2),
                            "workers": workers,
                        }
                    )

            except Exception as e:
                print(f"ERROR: {e}")

    # Summary analysis
    print("\n" + "=" * 90)
    print(f"SUMMARY: Memory Usage with {workers} Workers")
    print("=" * 90)

    print(f"\n{'Job Type':<15} {'Input Size':<12} {'Peak Memory':<14} {'Time':<10} {'Ratio':<10}")
    print("-" * 65)

    for result in sorted(all_results, key=lambda x: (x["job_type"], x["input_size_bytes"])):
        input_mb = result["input_size_bytes"] / (1024 * 1024)
        ratio = result["peak_memory_mb"] / input_mb if input_mb > 0.01 else 0
        print(
            f"{result['job_type']:<15} "
            f"{result['input_size_human']:<12} "
            f"{result['peak_memory_mb']:.0f}MB{'':<7} "
            f"{result['elapsed_seconds']:.1f}s{'':<5} "
            f"{ratio:.1f}x"
        )

    # Calculate SLURM recommendations
    print("\n" + "=" * 90)
    print("SLURM MEMORY RECOMMENDATIONS (with parallel workers)")
    print("=" * 90)
    print(f"\nBased on {workers}-worker processing runs:")
    print("Formula: requested_memory = (input_file_size × multiplier) + baseline")
    print()

    job_types = sorted(set(r["job_type"] for r in all_results))
    for job_type in job_types:
        job_results = [r for r in all_results if r["job_type"] == job_type]
        if not job_results:
            continue

        ratios = [
            r["peak_memory_mb"] / (r["input_size_bytes"] / (1024 * 1024))
            for r in job_results
            if r["input_size_bytes"] > 10240  # Ignore files < 10KB
        ]

        if ratios:
            max_ratio = max(ratios)
            # Add 25% safety margin
            recommended = round(max_ratio * 1.25, 1)
            print(f"  {job_type:<15}: {recommended}x input + 1024MB baseline")

    # Save results
    output_file = Path(__file__).parent / "memory_profile_parallel_results.csv"
    import csv

    with open(output_file, "w", newline="") as f:
        if all_results:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
