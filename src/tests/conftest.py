import pathlib
import shutil

import pytest

VALIDATION_DATA_DIR = "data/validation_data_generated"
VALIDATION_DATA_SOURCE = "data/validation_primary_data.py"

VALIDATION_DATA_FORMATTED_PATH = pathlib.Path(__file__).parent / VALIDATION_DATA_DIR

TOTAL_FILES_IN_VALIDATION_DATA_DIR = 7

VALIDATION_DATA_PATH = pathlib.Path(__file__).parent / VALIDATION_DATA_SOURCE


@pytest.fixture(scope="session", autouse=True)
def set_up_validation_clone_data():
    """
    sets up the following structure:
    data/validation_data_generated/
        clone_0.py
        clone_1.py
        dir_one/
            dir_one_clone_0.py
            dir_one_clone_1.py
        dir_with_sub_dir/
            sub_dir/
                sub_dir_clone_0.py
                sub_dir_clone_1.py
            sibling_clone.py
    """

    # Create the directory structure
    VALIDATION_DATA_FORMATTED_PATH.mkdir(parents=True, exist_ok=True)
    # Create root level clones
    for i in range(2):
        clone_path = VALIDATION_DATA_FORMATTED_PATH / f"clone_{i}.py"
        shutil.copy2(VALIDATION_DATA_PATH, clone_path)

    # Create dir_one and its clones
    dir_one = VALIDATION_DATA_FORMATTED_PATH / "dir_one"
    dir_one.mkdir(exist_ok=True)
    for i in range(2):
        clone_path = dir_one / f"dir_one_clone_{i}.py"
        shutil.copy2(VALIDATION_DATA_PATH, clone_path)

    # Create dir_with_sub_dir structure
    dir_with_sub_dir = VALIDATION_DATA_FORMATTED_PATH / "dir_with_sub_dir"
    dir_with_sub_dir.mkdir(exist_ok=True)

    sub_dir = dir_with_sub_dir / "sub_dir"
    sub_dir.mkdir(exist_ok=True)

    # Create sub_dir clones
    for i in range(2):
        clone_path = sub_dir / f"sub_dir_clone_{i}.py"
        shutil.copy2(VALIDATION_DATA_PATH, clone_path)

    # Create sibling clone
    sibling_clone = dir_with_sub_dir / "sibling_clone.py"
    shutil.copy2(VALIDATION_DATA_PATH, sibling_clone)
