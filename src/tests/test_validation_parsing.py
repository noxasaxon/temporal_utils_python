import importlib.util
import pathlib
import sys

import pytest

from temporal_utils.collectors import (
    get_all_classes_from_module_and_submodules,
    get_classes_with_activity_methods,
)
from temporal_utils.validation import (
    TemporalUtilsValidationError,
    bulk_validate_module_activities,
)

from .conftest import (
    BAD_VALIDATION_DATA_FORMATTED_PATH,
    GOOD_VALIDATION_DATA_FORMATTED_PATH,
    GOOD_VALIDATION_DATA_SOURCE,
    TOTAL_FILES_IN_VALIDATION_DATA_DIR,
    load_validation_data_as_module,
)

NUM_CLASSES_IN_VALIDATION_FILE = 6
NUM_CLASS_WITH_ACTIVITY_METHODS = 3
NUM_ACTIVITIES_IN_FILE = 6

TEST_FILE_PATH = pathlib.Path(__file__).parent / GOOD_VALIDATION_DATA_SOURCE
TEST_FILE_PATH_AS_STR = str(pathlib.Path(__file__).parent / GOOD_VALIDATION_DATA_SOURCE)


def helper_get_all_classes_from_file_contents_without_exec(
    file_contents: str,
) -> list[type]:
    """Parse a Python file and return all classes defined in it.

    Args:
        file_contents: String containing Python source code

    Returns:
        List of class types defined in the file
    """
    # Create a temporary module to execute the code in an isolated namespace
    spec = importlib.util.spec_from_loader("temp_module", loader=None)
    if spec is None:
        raise ImportError("Could not create module spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules["temp_module"] = module

    # Execute the code in the temporary module
    exec(file_contents, module.__dict__)

    classes = []

    # Get all classes defined in the module
    for item_name in dir(module):
        item = getattr(module, item_name)
        if isinstance(item, type) and item.__module__ == "temp_module":
            classes.append(item)

    # Clean up
    del sys.modules["temp_module"]

    return classes


def test_primary_data_source_is_correct():
    content = TEST_FILE_PATH.read_text()

    classes = helper_get_all_classes_from_file_contents_without_exec(content)
    assert NUM_CLASSES_IN_VALIDATION_FILE == len(classes)

    all_activity_methods = []

    result = get_classes_with_activity_methods(classes)
    assert NUM_CLASS_WITH_ACTIVITY_METHODS == len(result)

    for _cls_name, cls_methods_list in result:
        all_activity_methods.extend(cls_methods_list)

    assert NUM_ACTIVITIES_IN_FILE == len(all_activity_methods)


def test_get_all_classes_from_module_and_submodules():
    temporal_module = load_validation_data_as_module(
        GOOD_VALIDATION_DATA_FORMATTED_PATH
    )
    classes = get_all_classes_from_module_and_submodules(temporal_module)
    assert (
        len(classes)
        == NUM_CLASSES_IN_VALIDATION_FILE * TOTAL_FILES_IN_VALIDATION_DATA_DIR
    )

    classes_with_activity_methods = get_classes_with_activity_methods(classes)
    assert (
        len(classes_with_activity_methods)
        == NUM_CLASS_WITH_ACTIVITY_METHODS * TOTAL_FILES_IN_VALIDATION_DATA_DIR
    )


def test_bulk_validate_module_activities():
    temporal_module = load_validation_data_as_module(
        GOOD_VALIDATION_DATA_FORMATTED_PATH
    )
    bulk_validate_module_activities(temporal_module)


def test_bulk_validate_module_activities_with_bad_data():
    temporal_module = load_validation_data_as_module(BAD_VALIDATION_DATA_FORMATTED_PATH)
    with pytest.raises(TemporalUtilsValidationError):
        bulk_validate_module_activities(temporal_module)
