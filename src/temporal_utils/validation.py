from types import FunctionType
from pydantic import BaseModel
import inspect


class _BaseValidator:
    """Collection of class validation utilities that are generic for use on workflows and activities."""

    validation_fn_prefix = "_validate_"

    def get_search_attribute(self) -> str:
        """Must be implemented in subclass before use. This attribute is used to find the methods to validate, and have been decorated by temporal."""
        raise NotImplementedError

    def run_validators(self, class_to_validate: type) -> None:  # type: ignore[reportSelfClsParameterName]
        """Runs all validators on the input class."""

        # get all methods from Self that begin with "validate_"
        validators = [
            getattr(self, fn_name)
            for fn_name in dir(self)
            if fn_name.startswith(self.validation_fn_prefix)
        ]

        # if no validators are found, raise error
        if not validators:
            raise ValueError(
                f"No validators found in {self.__name__}. Please add a validator method that begins with `{self.validation_fn_prefix}`."  # type: ignore[attr-defined]
            )

        # run all validators and collect their outputs into a flattened errors list
        errors = []

        for (
            fn_name,
            fn_type,
        ) in self._collect_fns_to_validate(class_to_validate):
            for validator in validators:
                validator_errors = validator(class_to_validate, fn_name, fn_type)

                # add context to errors and add them to the total errors list
                errors.extend(
                    [
                        f"{e} |Reported via {self.__str__()}.{validator.__name__}()"
                        for e in validator_errors
                    ]
                )

        if errors:
            raise TypeError(
                f"Validation Errors found in class `{class_to_validate.__name__}`: {errors}"
            )

    def _collect_fns_to_validate(
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

        if not fns_requiring_validation:
            raise ValueError(
                f"Class `{class_to_validate.__name__}` does not have any methods annotated with `{search_attribute}`. Did you forget to decorate your activity or workflow method with a Temporal decorator?"
            )
        return fns_requiring_validation

    def _get_activity_defn_methods(
        self,
        class_to_validate: type,
    ) -> list[tuple[str, FunctionType]]:  # type: ignore[reportSelfClsParameterName]
        all_class_methods = inspect.getmembers(
            class_to_validate, predicate=lambda x: inspect.isfunction(x)
        )

        temporal_activity_defn_methods = [
            fn_tup
            for fn_tup in all_class_methods
            if hasattr(fn_tup[1], "__temporal_activity_definition")
        ]

        return temporal_activity_defn_methods

    @staticmethod
    def _generate_opts_name(fn_name: str) -> str:
        return f"opts_{fn_name}"

    def _validate_activity_has_a_default_ops(
        self,
        class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        fn_name: str,
        _fn_type: FunctionType,
    ) -> list[str]:
        """Ensures activities have a unique execution options property set by the activity writer."""
        errors = []

        opts_name = TemporalActivityValidators._generate_opts_name(fn_name)
        if not hasattr(class_to_validate, opts_name):
            errors.append(
                f"Class `{class_to_validate.__class__.__name__}` created Temporal activity `{fn_name}` without providing default options for executing it. Please add a class attribute `{opts_name}` to the {class_to_validate.__class__.__name__}."
            )

        return errors

    def _validate_activity_takes_a_single_arg(
        self,
        _class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        fn_name: str,
        fn_type: FunctionType,
    ) -> list[str]:
        """Returns an error message if the activity does not take a single argument."""
        errors = []

        num_activity_args = fn_type.__code__.co_argcount

        if num_activity_args == 1:
            errors.append(
                f"No input defined for Activity `{fn_name}`. Activities should take a single argument."
            )
        elif num_activity_args > 2:
            errors.append(
                f"Too many arguments defined for Activity `{fn_name}`. Activities should take a single argument."
            )

        return errors

    def _validate_activity_input_arg_is_pydantic_serializable(
        self,
        _class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        fn_name: str,
        fn_type: FunctionType,
    ) -> list[str]:
        errors = []

        argspec = inspect.getfullargspec(fn_type)
        try:
            input_arg_name = argspec.args[1]
        except IndexError:
            errors.append(
                f"No input defined for Activity `{fn_name}`. Activities should take a single arg inherited from pydantic's basemodel."
            )
        else:
            input_arg_type = argspec.annotations.get(input_arg_name)
            if input_arg_type is None:
                errors.append(
                    f"Activity `{fn_name}` requires a type hint for its input argument."
                )
            elif not issubclass(input_arg_type, BaseModel):
                errors.append(
                    f"Activity `{fn_name}` input argument `{input_arg_name}` must be a child of pydantic's BaseModel."
                )

        return errors

    def _validate_activity_output_is_pydantic_serializable(
        self,
        _class_to_validate: type,  # type: ignore[reportSelfClsParameterName]
        fn_name: str,
        fn_type: FunctionType,
    ) -> list[str]:
        errors = []

        argspec = inspect.getfullargspec(fn_type)

        return_type = argspec.annotations.get("return")

        if return_type is None:
            errors.append(
                f"Activity `{fn_name}` does not have a type hint for its return value. Please add a type hint to the return value."
            )
        elif not issubclass(return_type, BaseModel):
            errors.append(
                f"Activity `{fn_name}` return value is not a child of pydantic's BaseModel. Activities should return a single argument (a dataclass or other json-serializable object that converts to a dictionary)."
            )

        return errors


class TemporalActivityValidators2(_BaseValidator):
    # added by the temporalio `@activity.defn` decorator
    @staticmethod
    def get_search_attribute() -> str:
        return "__temporal_activity_definition"


class TemporalActivityValidators(_BaseValidator):
    """
    The Temporal team and community have discovered a few best practices for defining and calling Temporal Activities,
        and this class is a collection of validator functions that check those practices are followed. When combined
        with the `BaseActivityValidated` class we can provide guardrails that check even before workflows are live.

    If you define activities as methods on a class that inherits from `BaseActivityValidated`, these validation functions
        will run and raise errors automatically at 'file interpret' time, even if the class itself is never initialized. This
        works because the `__init_subclass__` dunder method on `BaseActivityValidated` automatically runs these validators.

    These validators will:
        - Ensure activities expect a _single_ input parameter when being called.
        - Ensure activity input is a JSON dict-like object/class.
            These two validations are recommended for backwards compatibility because th fn signature is unchanged when adding a new input arg via object field.
        - Ensure each activity definition comes with a recommended set of options (retries, etc) when executing it from a workflow.
            This takes the burden off the workflow writer to also be a subject matter expert on each activity, which enables safer usage.

    To add a validator which is automatically run on children of `BaseActivityValidated`, create a new `staticmethod`
    fn with a name starting with `_validate_` and with the same fn signature as the existing validators:
        ```python

        class TemporalActivityValidators:
            @staticmethod
            def _validate_my_new_validator(cls: type, fn_name: str, _fn_type: FunctionType) -> list[str]:
                errors = []
                # do some validation here, and add string to the `errors` list if something is wrong
                return errors
        ```
    """

    @staticmethod
    def get_search_attribute() -> str:
        return "__temporal_activity_definition"


class TemporalWorkflowValidators(_BaseValidator):
    """ """

    def get_search_attribute(self) -> str:
        return "__temporal_workflow_run"
