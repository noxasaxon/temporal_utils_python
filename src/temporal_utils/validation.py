import inspect
import types
from dataclasses import is_dataclass
from types import FunctionType
from typing import Any, Callable

from temporal_utils.collectors import (
    TEMPORAL_ACTIVITY_DEFINITION_SEARCH_ATTRIBUTE,
    get_all_classes_from_module_and_submodules,
    get_classes_with_activity_methods,
)


class TemporalUtilsValidationError(Exception):
    """Base class for all TemporalUtils validation errors."""

    def __init__(self, message: str, error_msgs: list[str] = []):
        if not error_msgs:
            error_msgs = [message]

        self.error_msgs = error_msgs
        super().__init__(message)


class _BaseValidator:
    """Collection of class validation utilities that are generic for use on workflows and activities."""

    @staticmethod
    def get_search_attribute() -> str:
        """Must be implemented in subclass before use. This attribute is used to find the methods to validate, and have been decorated by temporal."""
        raise NotImplementedError

    @staticmethod
    def get_opts_keys_that_must_be_set() -> list[str]:
        """list of dict keys required to exist in the opts dict for each method we validate."""
        raise NotImplementedError

    def run_validators(self, class_to_validate: type | object) -> None:  # type: ignore[reportSelfClsParameterName]
        """Runs all validators on the input class."""

        validation_fn_prefix = "_validate_"

        if not isinstance(class_to_validate, type):
            class_to_validate = class_to_validate.__class__

        # get all methods from Self that begin with "validate_"
        validators = [
            getattr(self, method_name)
            for method_name in dir(self)
            if method_name.startswith(validation_fn_prefix)
        ]

        # if no validators are found, raise error
        if not validators:
            raise TemporalUtilsValidationError(
                f"No validators found in {self.__name__}. Please add a validator method that begins with `{validation_fn_prefix}`."  # type: ignore[attr-defined]
            )

        # run all validators and collect their outputs into a flattened errors list
        errors = []

        for (
            method_name,
            method_type,
        ) in self._collect_methods_to_validate(class_to_validate):
            for validator in validators:
                validator_errors = validator(
                    class_to_validate, method_name, method_type
                )

                # add context to errors and add them to the total errors list
                errors.extend(
                    [
                        f"{e} |Reported via {self.__class__.__name__}.{validator.__name__}()"
                        for e in validator_errors
                    ]
                )

        if errors:
            raise TemporalUtilsValidationError(
                f"Validation Errors found in class `{class_to_validate.__name__}`: {errors}",
                error_msgs=errors,
            )

    def _collect_methods_to_validate(
        self,
        class_to_validate: type,
    ) -> list[tuple[str, FunctionType]]:  # type: ignore[reportSelfClsParameterName]
        search_attribute = self.get_search_attribute()

        all_class_methods = inspect.getmembers(
            class_to_validate, predicate=lambda x: inspect.isfunction(x)
        )

        fns_requiring_validation = [
            fn_tup
            for fn_tup in all_class_methods
            if hasattr(fn_tup[1], search_attribute)
        ]

        if (
            not fns_requiring_validation
            and "base" not in class_to_validate.__name__.lower()
        ):
            raise TemporalUtilsValidationError(
                f"Class `{class_to_validate.__name__}` does not have any methods annotated with `{search_attribute}`. If this is intentional, please put the word `Base` somewhere in your class name. If not, did you forget to decorate your activity or workflow method with a Temporal decorator?"
            )
        return fns_requiring_validation

    @staticmethod
    def _generate_opts_name(method_name: str) -> str:
        return f"opts_{method_name}"

    def _validate_method_has_a_default_opts(
        self,
        class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        method_name: str,
        _method_type: FunctionType,
    ) -> list[str]:
        """Ensures activities have a unique execution options property set by the activity writer."""
        errors = []

        opts_name = TemporalActivityValidators._generate_opts_name(method_name)
        try:
            # check that the method writer provided execution options
            opts = getattr(class_to_validate, opts_name)
        except AttributeError:
            errors.append(
                f"Class `{class_to_validate.__name__}` created Temporal activity `{method_name}` without providing default options for executing it. Please add a class attribute `{opts_name}` to the {class_to_validate.__class__.__name__}."
            )
        else:
            # check that the provided options are the correct type
            if not isinstance(opts, dict):
                errors.append(
                    f"Class `{class_to_validate.__name__}` created Temporal activity `{method_name}` with invalid execution options. `{opts_name}` should be a dict."
                )
            # check that the provided options include the required keys defined in the validator (and that they aren't just `None`)
            elif not all(
                (key in opts and opts[key] is not None)
                for key in self.get_opts_keys_that_must_be_set()
            ):
                errors.append(
                    f"Class `{class_to_validate.__name__}` created Temporal activity `{method_name}` without setting all required execution options. Please add the following keys to `{opts_name}`: {self.get_opts_keys_that_must_be_set()}"
                )

        return errors

    def _validate_method_takes_a_single_arg(
        self,
        _class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        method_name: str,
        method_type: FunctionType,
    ) -> list[str]:
        """Returns an error message if the activity does not take a single argument."""
        errors = []

        num_params = len(inspect.signature(method_type).parameters)

        if num_params <= 1:
            errors.append(
                f"No input defined for Activity `{method_name}`. Activities should take a single argument (not including `self`)."
            )
        elif num_params > 2:
            errors.append(
                f"Too many arguments defined for Activity `{method_name}`. Activities should take a single argument (not including `self`)."
            )

        return errors

    @staticmethod
    def _throw_if_annotation_is_dataclass_or_not_child_of_basemodel(
        annotation_from_inspect: Any,
    ) -> None | bool:
        """dataclasses interfere with the Temporal Pydantic converter we're using, so we want to block them from being used as inputs or outputs."""
        if not annotation_from_inspect:
            return None

        if not hasattr(annotation_from_inspect, "__pydantic_fields_set__"):
            return False

        if is_dataclass(annotation_from_inspect):
            return False
        return True

    def _validate_method_input_arg_is_pydantic_serializable(
        self,
        _class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        method_name: str,
        method_type: FunctionType,
    ) -> list[str]:
        errors = []

        params = inspect.signature(method_type).parameters

        try:
            input_arg_name, input_arg_param = list(params.items())[1]
        except IndexError:
            errors.append(
                f"No input defined for Activity `{method_name}`. Activities should take a single arg inherited from pydantic's basemodel."
            )
        else:
            is_pydantic = (
                self._throw_if_annotation_is_dataclass_or_not_child_of_basemodel(
                    input_arg_param.annotation
                )
            )

            if is_pydantic is None:
                errors.append(
                    f"Activity `{method_name}` requires a type hint for its input argument."
                )
            elif not is_pydantic:
                errors.append(
                    f"Activity `{method_name}` input argument `{input_arg_name}` can't be a `dataclass` & must be a child of pydantic's BaseModel."
                )

        return errors

    def _validate_method_output_is_pydantic_serializable(
        self,
        _class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        method_name: str,
        method_type: FunctionType,
    ) -> list[str]:
        errors = []

        argspec = inspect.getfullargspec(method_type)

        return_annotation = argspec.annotations.get("return")

        is_pydantic = self._throw_if_annotation_is_dataclass_or_not_child_of_basemodel(
            return_annotation
        )

        if is_pydantic is None:
            errors.append(
                f"Activity `{method_name}` does not have a type hint for its return value. Please add a type hint to the return value."
            )
        elif not is_pydantic:
            errors.append(
                f"Activity `{method_name}` return value can't be a dataclass and must be a child of pydantic's BaseModel."
            )

        return errors


class TemporalActivityValidators(_BaseValidator):
    """
    The Temporal team and community have discovered a few best practices for defining and calling Temporal Activities,
        and this class is a collection of validator functions that check those practices are followed.

    #### Options For Use:
    - Function-driven validation: use `validate_activity_class()` manually or set up the `bulk_validate_module_activities()` function in
        your unit tests to run validators on all activity classes found in a module and its submodules.
    - Inheritance-driven validation: Write your activities in a class that inherits from `BaseActivityValidated`. these validation functions
        will run and raise errors automatically at 'file interpret' time, even if the class itself is never initialized in your code. This
        works because the `__init_subclass__` dunder method on `BaseActivityValidated` automatically runs these validators.

    #### Validation Details:
        - Ensure activities expect a _single_ input parameter when being called.
        - Ensure activity input is a class descended from `pydantic.BaseModel` (required for the pydantic data_converter to work).
            - These two validations are recommended for backwards compatibility because the fn signature is unchanged when adding
                a new input arg via object field.
        - Ensure each activity definition comes with a recommended set of options (retries, etc) when executing it from a workflow.
            - This takes the burden off the workflow writer to also be a subject matter expert on each activity, which enables safer usage.

    #### Extending Validators with Custom Requirements:
    To add a custom validator method, create a new class that inherits from `TemporalActivityValidators` and has a `staticmethod`
    fn with a name starting with `_validate_` and with the same fn signature as the existing validators:
        ```python
        class CustomActivityValidator(TemporalActivityValidators):
            @staticmethod
            def _validate_my_new_requirement(self,
                class_to_validate: type,
                method_name: str,
                method_type: FunctionType,
            ) -> list[str]:
                errors = []
                # do some validation here, and add string to the `errors` list if something is wrong
                return errors
        ```
    """

    @staticmethod
    def get_search_attribute() -> str:
        return TEMPORAL_ACTIVITY_DEFINITION_SEARCH_ATTRIBUTE

    @staticmethod
    def get_opts_keys_that_must_be_set() -> list[str]:
        """Keys are from `temporalio.workflow.ActivityConfig`"""
        return [  #
            # max time of a single Execution of the Activity (should always be set!)
            "start_to_close_timeout",
            #
            # Setting an activity retry policy: https://docs.temporal.io/encyclopedia/retry-policies
            "retry_policy",
            #
            # max overrall execution time INCLUDING retries
            # "schedule_to_close_timeout": None,
            #
            # Limits the maximum time between Heartbeats. For long running Activities, enables a quicker response when a Heartbeat fails to be recorded.
            # "heartbeat_timeout": None,
        ]


class TemporalWorkflowValidators(_BaseValidator):
    """ """

    @staticmethod
    def get_search_attribute() -> str:
        return "__temporal_workflow_run"

    @staticmethod
    def get_opts_keys_that_must_be_set() -> list[str]:
        return [
            "execution_timeout",
            "run_timeout",
        ]


default_activity_validator = TemporalActivityValidators()


def validate_activity_class(
    activity_class: type | object,
    validator: TemporalActivityValidators = default_activity_validator,
) -> None:
    validator.run_validators(activity_class)


def bulk_validate_module_activities(
    module: types.ModuleType,
    class_validator_fn: Callable[[type], None] = validate_activity_class,
) -> list[tuple[type, list[FunctionType]]]:
    """Validate all activities in a module and its submodules.
    Raises:
        TemporalUtilsValidationError for all errors found
    """
    classes = get_all_classes_from_module_and_submodules(module)
    collected_activity_classes_and_methods = get_classes_with_activity_methods(classes)

    all_error_msgs = []

    for cls, _activity_methods in collected_activity_classes_and_methods:
        try:
            class_validator_fn(cls)
        except TemporalUtilsValidationError as e:
            all_error_msgs.extend(e.error_msgs)

    if all_error_msgs:
        raise TemporalUtilsValidationError(
            f"Validation Errors found in module `{module.__name__}`: {all_error_msgs}",
            error_msgs=all_error_msgs,
        )

    return collected_activity_classes_and_methods
