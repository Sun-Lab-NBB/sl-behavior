import re
from pathlib import Path

from sl_shared_assets import SessionData, packaging_tools
from ataraxis_base_utilities import console


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


def rename(project_directory: Path, output_directory: Path, base_name: str = "face_camera") -> None:
    """
    Searches for all {base_name}.mp4 files within the session directory, renames them to the
    format {project_animal_session}.mp4, and moves them to the specified output directory.

    Args:
        project_directory: The absolute path to the root project directory on the BioHPC server.
        output_directory: The absolute path to the directory where the renamed {base_name}.mp4 files
                          will be moved.
    """
    timestamp_pattern = re.compile(r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{6}")
    all_videos = find_videos(project_directory=project_directory, base_name=base_name)

    for video_path in all_videos:
        path_str = str(video_path)

        match = timestamp_pattern.search(path_str)
        timestamp_str = match[0]

        path_parts = Path(path_str).parts
        timestamp_index = path_parts.index(timestamp_str)

        project = path_parts[timestamp_index - 2]
        animal = path_parts[timestamp_index - 1]

        new_name = f"{project}_{animal}_{timestamp_str}_{base_name}.mp4"
        new_path = output_directory / new_name

        video_path.rename(new_path)


def verify_checksum(project_directory: Path):
    """
    Verifies that the stored checksum file for each session matches the calculated checksum.

    Args:
        project_directory: The absolute path to the root project directory on the BioHPC server.

    Returns:
        True if all stored checksum files for each session match the calculated checksums.
        The function returns false immediately when
    """
    raw_data_dirs = find_raw_data_directories(project_directory)

    for raw_data_dir in raw_data_dirs:
        checksum_file = raw_data_dir / "ax_checksum.txt"

        calculated_checksum = packaging_tools.calculate_directory_checksum(
            directory=raw_data_dir, batch=False, save_checksum=False
        )

        with open(checksum_file, "r") as f:
            stored_checksum = f.read().strip()

        if stored_checksum != calculated_checksum:
            message = (
                "Calculated checksum and ax_checksum.txt do not match.\n"
                f"Stored checksum: {stored_checksum}\n"
                f"Calculated checksum: {calculated_checksum}"
            )
            console.error(message=message, error=ValueError)

    return


def sort_text_files(root_folder: Path, working_directory: Path):
    """
    Searches for and loads all 'session_data.yaml' files and organizes each session by project name.

    This function generates a .txt file for each unique project name, which contains the paths
    to all associated sessions.

    Args:
        root_folder: The absolute path to the root project directory on the BioHPC server.
        working_directory: The path to the directory where project-specific .txt files containing
                           all session paths for the same project are written to.
    """
    raw_data_paths = [folder for folder in root_folder.rglob("session_data.yaml")]

    projects_dict = {}

    for session_file in raw_data_paths:
        timestamp_path = session_file.parent.parent

        session_data = SessionData.load(
            session_path=timestamp_path,
            on_server=False,
        )
        project_name = session_data.project_name

        if project_name not in projects_dict:
            projects_dict[project_name] = []

        projects_dict[project_name].append(str(timestamp_path))

    for project_name, session_paths in projects_dict.items():
        output_file = working_directory / f"{project_name}.txt"
        with open(output_file, "w") as f:
            f.write("\n".join(session_paths) + "\n")
