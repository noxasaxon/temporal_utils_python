import importlib.util
import inspect
import pathlib
import sys
from types import FunctionType, MethodType

TEMPORAL_ACTIVITY_DEFINITION_SEARCH_ATTRIBUTE = "__temporal_activity_definition"


def get_all_activity_methods_from_object(
    instance_or_class_type: object,
) -> list[MethodType | FunctionType]:
    """A helper for getting every @activity.defn method in a class to pass to a Worker.
    This means you don't need to remember to add it to the worker every time you add an activity, and
    you don't need to list them out manually.
    """

    all_methods = inspect.getmembers(
        instance_or_class_type,
        predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x),
    )

    activity_methods_tup = [
        method_tuple
        for method_tuple in all_methods
        # filter for methods decorated with temporalio's @activity.defn
        if hasattr(method_tuple[1], TEMPORAL_ACTIVITY_DEFINITION_SEARCH_ATTRIBUTE)
    ]

    activity_methods = [method_tuple[1] for method_tuple in activity_methods_tup]

    return activity_methods  # type: ignore[no-any-return]


def get_all_python_files_recursively(directory: pathlib.Path) -> list[pathlib.Path]:
    """Recursively get all Python files from a directory and its subdirectories.

    Args:
        directory: Path to the directory to search

    Returns:
        List of paths to Python files
    """
    python_files = []
    for item in directory.rglob("*.py"):
        if item.is_file():
            python_files.append(item)
    return python_files


def get_classes_with_activity_methods(
    classes: list[type],
) -> list[tuple[type, list]]:
    """For each class, get its activity methods and return only classes that have activity methods."""
    result = []
    for cls in classes:
        activity_methods = get_all_activity_methods_from_object(cls)
        if len(activity_methods) > 0:
            result.append((cls, activity_methods))
    return result


def get_all_classes_from_file_contents(
    file_contents: str,
) -> list[type]:
    """Parse a Python file and return all classes defined in it.

    Args:
        file_contents: String containing Python source code

    Returns:
        List of class types defined in the file
    """
    # Create a temporary module to execute the code
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

    return classes
