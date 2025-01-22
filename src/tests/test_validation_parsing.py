import pathlib

from temporal_utils.collectors import (
    get_all_classes_from_file_contents,
    get_all_python_files_recursively,
    get_classes_with_activity_methods,
)

from .conftest import (
    TOTAL_FILES_IN_VALIDATION_DATA_DIR,
    VALIDATION_DATA_FORMATTED_PATH,
    VALIDATION_DATA_SOURCE,
)

NUM_CLASSES_IN_VALIDATION_FILE = 6
NUM_CLASS_WITH_ACTIVITY_METHODS = 3
NUM_ACTIVITIES_IN_FILE = 6

TEST_FILE_PATH = pathlib.Path(__file__).parent / VALIDATION_DATA_SOURCE
TEST_FILE_PATH_AS_STR = str(pathlib.Path(__file__).parent / VALIDATION_DATA_SOURCE)


def test_primary_data_source_is_correct():
    content = TEST_FILE_PATH.read_text()

    classes = get_all_classes_from_file_contents(content)
    assert NUM_CLASSES_IN_VALIDATION_FILE == len(classes)

    all_activity_methods = []

    result = get_classes_with_activity_methods(classes)
    assert NUM_CLASS_WITH_ACTIVITY_METHODS == len(result)

    for _cls_name, cls_methods_list in result:
        all_activity_methods.extend(cls_methods_list)

    assert NUM_ACTIVITIES_IN_FILE == len(all_activity_methods)


def test_get_all_classes_from_file_contents():
    with open(TEST_FILE_PATH_AS_STR, "r") as file:
        file_contents = file.read()

    classes = get_all_classes_from_file_contents(file_contents)

    assert len(classes) == NUM_CLASSES_IN_VALIDATION_FILE

    # Verify these are actual class types
    for cls in classes:
        assert isinstance(cls, type)


def test_get_classes_with_activity_methods():
    with open(TEST_FILE_PATH_AS_STR, "r") as file:
        file_contents = file.read()

    classes = get_all_classes_from_file_contents(file_contents)
    classes_with_activity_methods = get_classes_with_activity_methods(classes)

    assert len(classes_with_activity_methods) == NUM_CLASS_WITH_ACTIVITY_METHODS


def test_get_all_python_files_recursively():
    python_files = get_all_python_files_recursively(VALIDATION_DATA_FORMATTED_PATH)

    assert len(python_files) == TOTAL_FILES_IN_VALIDATION_DATA_DIR

    # Convert to set of filenames to check for duplicates
    filenames = [file.name for file in python_files]
    assert len(filenames) == len(set(filenames)), "Duplicate Python files found"


def test_get_all_classes_from_python_files():
    python_files = get_all_python_files_recursively(VALIDATION_DATA_FORMATTED_PATH)

    classes = []

    for file in python_files:
        with open(file, "r") as f:
            file_contents = f.read()
        classes.extend(get_all_classes_from_file_contents(file_contents))

    assert (
        len(classes)
        == NUM_CLASSES_IN_VALIDATION_FILE * TOTAL_FILES_IN_VALIDATION_DATA_DIR
    )


def test_get_classes_from_all_files_with_activity_methods():
    python_files = get_all_python_files_recursively(VALIDATION_DATA_FORMATTED_PATH)
    classes = []
    for file in python_files:
        with open(file, "r") as f:
            file_contents = f.read()
        classes.extend(get_all_classes_from_file_contents(file_contents))

    classes_with_activity_methods = get_classes_with_activity_methods(classes)
    assert (
        len(classes_with_activity_methods)
        == NUM_CLASS_WITH_ACTIVITY_METHODS * TOTAL_FILES_IN_VALIDATION_DATA_DIR
    )
