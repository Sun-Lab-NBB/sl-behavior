from pathlib import Path


def find_raw_data_directories(project_directory: Path) -> tuple[Path, ...]:
    """Recursively finds all raw_data directories inside the input root directory.

    This service function is used to discover all unprocessed raw_data directories stored in the root Sun lab data
    directory on the BioHPC server. Candidate directories should contain ax_checksum.txt file and should not contain the
    telomere.bin marker.

    Args:
        project_directory: The absolute path to the root Sun lab data directory on the BioHPC server.

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
    search_directory(project_directory)
    return tuple(directories)


def find_videos(project_directory: Path, base_name: str = "face_camera") -> tuple[Path, ...]:
    """Recursively finds all face_camera.mp4 video files inside the input project directory.

    This service function is used to discover all face_camera videos stored inside a project directory stored on the
    Sun lab BioHPC server. Currently, this is used during DeepLabCut (DLC) video tracking pipeline to either train a
    new model or apply model inference using a pretrained model.

    Args:
        project_directory: The absolute path to the root project directory on the BioHPC server.

    Returns:
        A tuple of Paths to all discovered face_camera.mp4 files stored under all animal and session directories of the
        target project.
    """

    directories = find_raw_data_directories(project_directory=project_directory)

    video_paths = []
    for directory in directories:
        video_path = directory.joinpath("camera_frames", f"{base_name}.mp4")
        if video_path.exists():
            video_paths.append(video_path)

    return tuple(video_paths)


for vid_p in find_videos(Path("/home/cybermouse/Desktop/Projects/TestMice")):
    print(vid_p)


