from sl_behavior.path_tools import find_hardware_configs
from sl_behavior.log_processing import process_log_directory
from pathlib import Path


if __name__ == "__main__":
    directories = find_hardware_configs(root_dir=Path("/home/cybermouse/Desktop/Projects"))
    for directory in directories:
        process_log_directory(data_directory=directory, verbose=True)
