import polars as pl
from pathlib import Path

intake = Path("/mnt/data/TestMice/85/2025-12-18-16-56-59-536289/processed_data/camera_data/body_camera_timestamps.feather")

df = pl.read_ipc(intake, memory_map=True)

#Computes elapsed time relative to session onset in minutes.
# df = df.with_columns(
#     ((pl.col("time_us") - pl.col("time_us").first()) / 60_000_000).alias("elapsed_minutes")
# )
# print(df)

df = df.with_columns(
    ((pl.col("frame_time_us") - pl.col("frame_time_us").first()) / 60_000_000).alias("elapsed_minutes")
)

# Computes inter-frame delay statistics.
frame_delays = df.select(pl.col("frame_time_us").diff().drop_nulls().alias("delay_us"))
mean_delay_us = frame_delays["delay_us"].mean()
std_delay_us = frame_delays["delay_us"].std()

print(f"Inter-frame delay: {mean_delay_us / 1000:.2f} ± {std_delay_us / 1000:.2f} ms")
print(f"Average FPS: {1_000_000 / mean_delay_us:.2f}")

# Detects FPS drops (frames where delay > 1.5x mean, indicating dropped frame(s)).
drop_threshold = mean_delay_us * 2
df_with_delays = df.with_columns(pl.col("frame_time_us").diff().alias("delay_us"))
fps_drops = df_with_delays.filter(pl.col("delay_us") > drop_threshold)

print(f"\nFPS drops (delay > {drop_threshold / 1000:.2f} ms): {len(fps_drops)} frames")
if len(fps_drops) > 0:
    print(f"Drop rate: {len(fps_drops) / len(df) * 100:.3f}%")
    print(f"Worst delays (ms): {fps_drops['delay_us'].top_k(5).to_list()}")
    print(fps_drops.select("elapsed_minutes", "delay_us").head(10))