from types import FunctionType
from pydantic import BaseModel
import inspect


class _BaseValidator:
    """Collection of class validation utilities that are generic for use on workflows and activities."""

    def get_search_attribute(self) -> str:
        """Must be implemented in subclass before use. This attribute is used to find the methods to validate, and have been decorated by temporal."""
        raise NotImplementedError

    def get_opts_keys_that_must_be_set(self) -> list[str]:
        """list of dict keys required to exist in the opts dict for each method we validate."""
        raise NotImplementedError

    def run_validators(self, class_to_validate: type) -> None:  # type: ignore[reportSelfClsParameterName]
        """Runs all validators on the input class."""

        validation_fn_prefix = "_validate_"

        # get all methods from Self that begin with "validate_"
        validators = [
            getattr(self, method_name)
            for method_name in dir(self)
            if method_name.startswith(validation_fn_prefix)
        ]

        # if no validators are found, raise error
        if not validators:
            raise ValueError(
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
                        f"{e} |Reported via {self.__str__()}.{validator.__name__}()"
                        for e in validator_errors
                    ]
                )

        if errors:
            raise TypeError(
                f"Validation Errors found in class `{class_to_validate.__name__}`: {errors}"
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
            raise ValueError(
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
            input_arg_annotation = input_arg_param.annotation

            if input_arg_annotation is None:
                errors.append(
                    f"Activity `{method_name}` requires a type hint for its input argument."
                )
            elif not issubclass(input_arg_annotation, BaseModel):
                errors.append(
                    f"Activity `{method_name}` input argument `{input_arg_name}` must be a child of pydantic's BaseModel."
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

        return_type = argspec.annotations.get("return")

        if return_type is None:
            errors.append(
                f"Activity `{method_name}` does not have a type hint for its return value. Please add a type hint to the return value."
            )
        elif not issubclass(return_type, BaseModel):
            errors.append(
                f"Activity `{method_name}` return value is not a child of pydantic's BaseModel. Activities should return a single argument (a dataclass or other json-serializable object that converts to a dictionary)."
            )

        return errors


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
            def _validate_my_new_validator(cls: type, method_name: str, _method_type: FunctionType) -> list[str]:
                errors = []
                # do some validation here, and add string to the `errors` list if something is wrong
                return errors
        ```
    """

    @staticmethod
    def get_search_attribute() -> str:
        return "__temporal_activity_definition"

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

    def get_search_attribute(self) -> str:
        return "__temporal_workflow_run"

    def get_opts_keys_that_must_be_set(self) -> list[str]:
        return [
            "execution_timeout",
            "run_timeout",
        ]
