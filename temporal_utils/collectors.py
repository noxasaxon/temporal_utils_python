import importlib.util
import inspect
import pathlib
import sys
import types
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

    del sys.modules["temp_module"]

    return classes


def get_all_classes_from_module_and_submodules(module: types.ModuleType) -> list[type]:
    """
    Recursively finds all classes defined in a module and its submodules.
    This includes sibling modules and their submodules.

    Args:
        module: A Python module object to search for classes

    Returns:
        list[type]: A list of all class types found in the module hierarchy
    """
    all_classes = []
    visited_modules = set()

    def _collect_from_module(current_module: types.ModuleType):
        if current_module in visited_modules:
            return
        visited_modules.add(current_module)

        # Get base package name (e.g., 'foo' from 'foo.bar.baz')
        base_package = current_module.__name__.split(".")[0]  # type: ignore[attr-defined]

        # Get classes directly defined in this module
        for item_name in dir(current_module):
            item = getattr(current_module, item_name)

            # Check for classes
            if isinstance(item, type):
                # Only include if it's defined in our module hierarchy
                if hasattr(item, "__module__") and item.__module__.startswith(
                    base_package
                ):
                    all_classes.append(item)

            # Check for submodules
            elif isinstance(item, types.ModuleType):
                # Process if it's part of our package
                if item.__name__.startswith(base_package):
                    _collect_from_module(item)

    _collect_from_module(module)
    return all_classes
