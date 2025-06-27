import polars as pl
from pathlib import Path

file_path = Path("/home/cyberaxolotl/Data/TestMice/6/2025-06-18-15-51-09-880186/processed_data/behavior_data/mesoscope_frame_data.feather")

df = pl.read_ipc(file_path, use_pyarrow=True)

pl.Config.set_tbl_rows(200)
print(df.head(90).with_row_index())