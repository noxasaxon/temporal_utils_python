import pathlib
import shutil

import pytest

GOOD_VALIDATION_DATA_DIR = "data/good_validation_data_generated"
GOOD_VALIDATION_DATA_SOURCE = "data/validation_good_data_primary.py"

GOOD_VALIDATION_DATA_FORMATTED_PATH = (
    pathlib.Path(__file__).parent / GOOD_VALIDATION_DATA_DIR
)

BAD_VALIDATION_DATA_DIR = "data/bad_validation_data_generated"
BAD_VALIDATION_DATA_SOURCE = "data/validation_bad_data_primary.py"

BAD_VALIDATION_DATA_FORMATTED_PATH = (
    pathlib.Path(__file__).parent / BAD_VALIDATION_DATA_DIR
)

TOTAL_FILES_IN_VALIDATION_DATA_DIR = 7

GOOD_VALIDATION_DATA_PATH = pathlib.Path(__file__).parent / GOOD_VALIDATION_DATA_SOURCE
BAD_VALIDATION_DATA_PATH = pathlib.Path(__file__).parent / BAD_VALIDATION_DATA_SOURCE


def generate_clone_data(source_file_path: pathlib.Path, output_dir_path: pathlib.Path):
    """
    sets up the following structure, where every file is a clone of the source file:
    data/<output_dir>/
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
    output_dir_path.mkdir(parents=True, exist_ok=True)
    # Create root level clones
    for i in range(2):
        clone_path = output_dir_path / f"clone_{i}.py"
        shutil.copy2(source_file_path, clone_path)

    # Create dir_one and its clones
    dir_one = output_dir_path / "dir_one"
    dir_one.mkdir(exist_ok=True)
    for i in range(2):
        clone_path = dir_one / f"dir_one_clone_{i}.py"
        shutil.copy2(source_file_path, clone_path)

    # Create dir_with_sub_dir structure
    dir_with_sub_dir = output_dir_path / "dir_with_sub_dir"
    dir_with_sub_dir.mkdir(exist_ok=True)

    sub_dir = dir_with_sub_dir / "sub_dir"
    sub_dir.mkdir(exist_ok=True)

    # Create sub_dir clones
    for i in range(2):
        clone_path = sub_dir / f"sub_dir_clone_{i}.py"
        shutil.copy2(source_file_path, clone_path)

    # Create sibling clone
    sibling_clone = dir_with_sub_dir / "sibling_clone.py"
    shutil.copy2(source_file_path, sibling_clone)


@pytest.fixture(scope="session", autouse=True)
def set_up_good_validation_clone_data():
    generate_clone_data(GOOD_VALIDATION_DATA_PATH, GOOD_VALIDATION_DATA_FORMATTED_PATH)


@pytest.fixture(scope="session", autouse=True)
def set_up_bad_validation_clone_data():
    generate_clone_data(BAD_VALIDATION_DATA_PATH, BAD_VALIDATION_DATA_FORMATTED_PATH)


# @pytest.fixture(scope="session", autouse=True)
# def set_up_validation_clone_data():
#     """
#     sets up the following structure:
#     data/validation_data_generated/
#         clone_0.py
#         clone_1.py
#         dir_one/
#             dir_one_clone_0.py
#             dir_one_clone_1.py
#         dir_with_sub_dir/
#             sub_dir/
#                 sub_dir_clone_0.py
#                 sub_dir_clone_1.py
#             sibling_clone.py
#     """

#     # Create the directory structure
#     VALIDATION_DATA_FORMATTED_PATH.mkdir(parents=True, exist_ok=True)
#     # Create root level clones
#     for i in range(2):
#         clone_path = VALIDATION_DATA_FORMATTED_PATH / f"clone_{i}.py"
#         shutil.copy2(VALIDATION_DATA_PATH, clone_path)

#     # Create dir_one and its clones
#     dir_one = VALIDATION_DATA_FORMATTED_PATH / "dir_one"
#     dir_one.mkdir(exist_ok=True)
#     for i in range(2):
#         clone_path = dir_one / f"dir_one_clone_{i}.py"
#         shutil.copy2(VALIDATION_DATA_PATH, clone_path)

#     # Create dir_with_sub_dir structure
#     dir_with_sub_dir = VALIDATION_DATA_FORMATTED_PATH / "dir_with_sub_dir"
#     dir_with_sub_dir.mkdir(exist_ok=True)

#     sub_dir = dir_with_sub_dir / "sub_dir"
#     sub_dir.mkdir(exist_ok=True)

#     # Create sub_dir clones
#     for i in range(2):
#         clone_path = sub_dir / f"sub_dir_clone_{i}.py"
#         shutil.copy2(VALIDATION_DATA_PATH, clone_path)

#     # Create sibling clone
#     sibling_clone = dir_with_sub_dir / "sibling_clone.py"
#     shutil.copy2(VALIDATION_DATA_PATH, sibling_clone)


def load_validation_data_as_module(data_dir_path: pathlib.Path):
    import importlib.util
    import sys
    import types

    # Create the root module
    temporal_module = types.ModuleType("temporal_module")
    sys.modules["temporal_module"] = temporal_module

    # Load all Python files as submodules
    for file_path in data_dir_path.glob("**/*.py"):
        # Get module name based on file path
        relative_path = file_path.relative_to(data_dir_path)
        module_name = (
            f"temporal_module.{str(relative_path.with_suffix('')).replace('/', '.')}"
        )

        # Create and load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        # Create parent modules if they don't exist
        parts = module_name.split(".")
        parent = temporal_module
        for i in range(1, len(parts) - 1):
            parent_name = ".".join(parts[: i + 1])
            if not hasattr(parent, parts[i]):
                parent_module = types.ModuleType(parent_name)
                setattr(parent, parts[i], parent_module)
                sys.modules[parent_name] = parent_module
            parent = getattr(parent, parts[i])

        # Execute the module
        spec.loader.exec_module(module)
        setattr(parent, parts[-1], module)

    return temporal_module
