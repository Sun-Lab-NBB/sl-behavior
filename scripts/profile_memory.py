#!/usr/bin/env python3
"""Profiles memory usage for behavior data processing operations.

Measures peak memory during data loading for each log file type.
Uses tracemalloc for Python memory tracking and resource module for process memory.

Results are used to determine optimal SLURM memory allocation based on input file size.
"""

import gc
import resource
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ataraxis_video_system import extract_logged_camera_timestamps


@dataclass
class MemoryProfile:
    """Stores memory profiling results for a single operation."""

    input_file: str
    input_size_bytes: int
    peak_python_mb: float = 0.0
    peak_process_mb: float = 0.0


def get_process_memory_mb() -> float:
    """Returns current process memory usage in MB (maxrss from resource module)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def profile_npz_loading(npz_path: Path, load_arrays: bool = True) -> MemoryProfile:
    """Profiles memory usage when loading an npz file into numpy arrays.

    Args:
        npz_path: Path to the npz file.
        load_arrays: If True, load all arrays into memory. If False, just open the file.
    """
    gc.collect()
    tracemalloc.start()
    baseline_process = get_process_memory_mb()

    data = np.load(npz_path, allow_pickle=True)

    if load_arrays:
        # Force loading all arrays into memory
        arrays = {key: np.array(data[key]) for key in data.files}
        # Keep reference to prevent GC
        _ = arrays

    current, peak = tracemalloc.get_traced_memory()
    peak_process = get_process_memory_mb() - baseline_process

    tracemalloc.stop()

    return MemoryProfile(
        input_file=npz_path.name,
        input_size_bytes=npz_path.stat().st_size,
        peak_python_mb=peak / (1024 * 1024),
        peak_process_mb=max(0, peak_process),
    )


def profile_camera_extraction(npz_path: Path) -> MemoryProfile:
    """Profiles memory for camera timestamp extraction."""
    gc.collect()
    tracemalloc.start()
    baseline_process = get_process_memory_mb()

    # This is the actual extraction function used in camera processing
    extracted_data = extract_logged_camera_timestamps(log_path=npz_path)

    current, peak = tracemalloc.get_traced_memory()
    peak_process = get_process_memory_mb() - baseline_process

    tracemalloc.stop()

    del extracted_data
    gc.collect()

    return MemoryProfile(
        input_file=npz_path.name,
        input_size_bytes=npz_path.stat().st_size,
        peak_python_mb=peak / (1024 * 1024),
        peak_process_mb=max(0, peak_process),
    )


def format_size(size_bytes: int) -> str:
    """Formats bytes as human-readable string."""
    if size_bytes >= 1024**3:
        return f"{size_bytes / (1024**3):.1f}G"
    if size_bytes >= 1024**2:
        return f"{size_bytes / (1024**2):.1f}M"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f}K"
    return f"{size_bytes}B"


def main() -> None:
    # Sessions to profile (small, medium, large by file sizes)
    sessions = [
        Path("/home/data/MaalstroomicFlow/11/2025-07-13-18-28-09-495709"),  # Small
        Path("/home/data/StateSpaceOdyssey/26/2025-08-28-18-58-02-766013"),  # Medium
        Path("/home/data/StateSpaceOdyssey/14/2025-08-22-16-32-29-378081"),  # Large
    ]

    # Log files to profile with their processing category
    log_configs = [
        # (log_file, job_type, profile_function)
        ("1_log.npz", "runtime", profile_npz_loading),
        ("51_log.npz", "face_camera", profile_camera_extraction),
        ("62_log.npz", "body_camera", profile_camera_extraction),
        ("101_log.npz", "actor_mc", profile_npz_loading),
        ("152_log.npz", "sensor_mc", profile_npz_loading),
        ("203_log.npz", "encoder_mc", profile_npz_loading),
    ]

    print("=" * 90)
    print("Memory Profiling for sl-behavior Processing Jobs")
    print("=" * 90)
    print()
    print("This measures peak memory during data extraction/loading phase.")
    print("Microcontroller jobs use raw npz loading as proxy (actual extraction adds ~10-20%).")
    print()

    all_results: list[dict[str, Any]] = []

    for session_path in sessions:
        session_name = session_path.name
        project = session_path.parent.parent.name
        behavior_dir = session_path / "raw_data" / "behavior_data"

        print(f"\n{'=' * 70}")
        print(f"Session: {project}/{session_name}")
        print(f"{'=' * 70}")

        for log_file, job_type, profile_func in log_configs:
            npz_path = behavior_dir / log_file

            if not npz_path.exists():
                print(f"  {job_type}: SKIPPED (file not found)")
                continue

            file_size = npz_path.stat().st_size
            print(f"  {job_type} ({format_size(file_size)}): ", end="", flush=True)

            try:
                profile = profile_func(npz_path)
                print(f"peak={profile.peak_python_mb:.1f}MB (python), process_delta={profile.peak_process_mb:.1f}MB")

                all_results.append(
                    {
                        "project": project,
                        "session": session_name,
                        "job_type": job_type,
                        "log_file": log_file,
                        "input_size_bytes": profile.input_size_bytes,
                        "input_size_human": format_size(profile.input_size_bytes),
                        "peak_python_mb": round(profile.peak_python_mb, 2),
                        "peak_process_mb": round(profile.peak_process_mb, 2),
                    }
                )
            except Exception as e:
                print(f"ERROR: {e}")

    # Summary analysis
    print("\n" + "=" * 90)
    print("SUMMARY: Memory Usage by Job Type (sorted by input size)")
    print("=" * 90)

    print(f"\n{'Job Type':<15} {'Input Size':<12} {'Peak Python':<14} {'Memory/Size Ratio':<18}")
    print("-" * 65)

    for result in sorted(all_results, key=lambda x: (x["job_type"], x["input_size_bytes"])):
        input_mb = result["input_size_bytes"] / (1024 * 1024)
        ratio = result["peak_python_mb"] / input_mb if input_mb > 0.01 else 0
        print(
            f"{result['job_type']:<15} "
            f"{result['input_size_human']:<12} "
            f"{result['peak_python_mb']:.1f}MB{'':<7} "
            f"{ratio:.2f}x"
        )

    # Calculate recommended memory multipliers per job type
    print("\n" + "=" * 90)
    print("MEMORY SCALING ANALYSIS BY JOB TYPE")
    print("=" * 90)

    job_types = sorted(set(r["job_type"] for r in all_results))
    for job_type in job_types:
        job_results = [r for r in all_results if r["job_type"] == job_type]
        if len(job_results) < 2:
            continue

        print(f"\n{job_type}:")
        ratios = []
        for r in sorted(job_results, key=lambda x: x["input_size_bytes"]):
            input_mb = r["input_size_bytes"] / (1024 * 1024)
            if input_mb > 0.01:  # Ignore very small files
                ratio = r["peak_python_mb"] / input_mb
                ratios.append(ratio)
                print(f"  {r['input_size_human']:>10} -> {r['peak_python_mb']:.1f}MB (ratio: {ratio:.2f}x)")

        if ratios:
            avg_ratio = sum(ratios) / len(ratios)
            max_ratio = max(ratios)
            # Recommend max ratio + 50% safety margin, rounded up
            recommended = max_ratio * 1.5
            print(f"  Avg ratio: {avg_ratio:.2f}x, Max ratio: {max_ratio:.2f}x")
            print(f"  RECOMMENDED: {recommended:.1f}x input size + 512MB baseline")

    # SLURM recommendations
    print("\n" + "=" * 90)
    print("SLURM MEMORY ALLOCATION RECOMMENDATIONS")
    print("=" * 90)
    print("\nFormula: requested_memory = (input_file_size * multiplier) + baseline_mb")
    print()

    recommendations = {
        "runtime": (15.0, 256),  # Small files, add generous baseline
        "face_camera": (4.0, 512),
        "body_camera": (4.0, 512),
        "actor_mc": (3.5, 512),
        "sensor_mc": (3.5, 512),
        "encoder_mc": (3.5, 512),
    }

    # Update recommendations based on actual measurements
    for job_type in job_types:
        job_results = [r for r in all_results if r["job_type"] == job_type]
        if job_results:
            ratios = [
                r["peak_python_mb"] / (r["input_size_bytes"] / (1024 * 1024))
                for r in job_results
                if r["input_size_bytes"] > 10240  # Ignore files < 10KB
            ]
            if ratios:
                max_ratio = max(ratios)
                recommended_mult = round(max_ratio * 1.5, 1)
                recommendations[job_type] = (recommended_mult, 512)

    for job_type, (mult, baseline) in sorted(recommendations.items()):
        print(f"  {job_type:<15}: {mult}x input + {baseline}MB")

    print("\nExample SLURM sbatch directive for 100MB encoder file:")
    mult, baseline = recommendations.get("encoder_mc", (3.5, 512))
    mem_mb = int(100 * mult + baseline)
    print(f"  #SBATCH --mem={mem_mb}M")

    # Save results to CSV
    output_file = Path(__file__).parent / "memory_profile_results.csv"
    import csv

    with open(output_file, "w", newline="") as f:
        if all_results:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)

    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
