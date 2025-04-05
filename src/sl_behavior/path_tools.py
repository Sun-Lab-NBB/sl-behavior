from pathlib import Path


def find_raw_data_directories(root_dir: Path) -> tuple[Path, ...]:
    """ Recursively finds all raw_data directories inside the input root directory.

    This service function is used to discover all unprocessed raw_data directories stored in the root Sun lab data
    directory on the BioHPC server. Candidate directories should contain ax_checksum.txt file and should not contain the
    telomere.bin marker.

    Args:
        root_dir: The absolute path to the root Sun lab data directory on the BioHPC server.

    Returns:
        A tuple of Paths to all discovered candidate directories.
    """
    directories = []

    # Defines a nested function to handle recursive search
    def search_directory(directory: Path):
        # Checks if ax_checksum.txt exists in this directory
        checksum_file = directory.joinpath("ax_checksum.txt")
        if checksum_file.exists():
            directories.append(directory)
            return True  # If checksum is found, aborts traversing this subdirectory tree early

        # If the directory does not contain a checksum file, searches other subdirectories
        found_in_subdirs = False
        for child in directory.iterdir():
            if child.is_dir():
                # If checksum is found in this subdirectory, marks this branch as "processed"
                if search_directory(child):
                    found_in_subdirs = True

        return found_in_subdirs

    # Starts the recursive search
    search_directory(root_dir)
    return tuple(directories)