from types import FunctionType
from pydantic import BaseModel
import inspect


class TemporalActivityValidators:
    """
    The Temporal team and community have discovered a few best practices for defining and calling Temporal Activities,
        and this class is a collection of validator functions that check those practices are followed. When combined
        with the `BaseTemporalActivity` class we can provide guardrails that check even before workflows are live.

    If you define activities as methods on a class that inherits from `BaseTemporalActivity`, these validation functions
        will run and raise errors automatically at 'file interpret' time, even if the class itself is never initialized. This
        works because the `__init_subclass__` dunder method on `BaseTemporalActivity` automatically runs these validators.

    These validators will:
        - Ensure activities expect a _single_ input parameter when being called.
        - Ensure activity input is a JSON dict-like object/class.
            These two validations are recommended for backwards compatibility because th fn signature is unchanged when adding a new input arg via object field.
        - Ensure each activity definition comes with a recommended set of options (retries, etc) when executing it from a workflow.
            This takes the burden off the workflow writer to also be a subject matter expert on each activity, which enables safer usage.

    To add a validator which is automatically run on children of `BaseTemporalActivity`, create a new `staticmethod`
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
    def run_validators(act_class: type):  # type: ignore[reportSelfClsParameterName]
        """Runs all validators on a class that is a subclass of BaseTemporalActivity."""

        # get all methods from TemporalActivityValidators that begin with "validate_"
        validators = [
            getattr(TemporalActivityValidators, fn_name)
            for fn_name in dir(TemporalActivityValidators)
            if fn_name.startswith("_validate_")
        ]

        # if no validators are found, raise error
        if not validators:
            raise ValueError(
                "No validators found in TemporalActivityValidators. Please add a validator method that begins with `validate_`."
            )

        # run all validators and collect their outputs into a flattened errors list
        errors = []

        for (
            fn_name,
            fn_type,
        ) in TemporalActivityValidators._get_activity_defn_methods(act_class):
            for validator in validators:
                validator_errors = validator(act_class, fn_name, fn_type)

                # add context to errors and add them to the total errors list
                errors.extend(
                    [
                        f"{e} |Reported via {TemporalActivityValidators.__name__}.{validator.__name__}()"
                        for e in validator_errors
                    ]
                )

        if errors:
            raise TypeError(
                f"Validation Errors found in class `{act_class.__name__}`: {errors}"
            )

    @staticmethod
    def _get_activity_defn_methods(act_class: type):  # type: ignore[reportSelfClsParameterName]
        all_class_methods = inspect.getmembers(
            act_class, predicate=lambda x: inspect.isfunction(x)
        )

        temporal_activity_defn_methods = [
            fn_tup
            for fn_tup in all_class_methods
            if hasattr(fn_tup[1], "__temporal_activity_definition")
        ]

        return temporal_activity_defn_methods

    @staticmethod
    def _generate_opts_name(fn_name):
        return f"opts_{fn_name}"

    @staticmethod
    def _validate_activity_has_a_default_ops(
        act_class: type,  # type: ignore[reportSelfClsParameterName]
        fn_name: str,
        _fn_type: FunctionType,
    ) -> list[str]:
        """Ensures activities have a unique execution options property set by the activity writer."""
        errors = []

        opts_name = TemporalActivityValidators._generate_opts_name(fn_name)
        if not hasattr(act_class, opts_name):
            errors.append(
                f"Class `{act_class.__class__.__name__}` created Temporal activity `{fn_name}` without providing default options for executing it. Please add a class attribute `{opts_name}` to the {act_class.__class__.__name__}."
            )

        return errors

    @staticmethod
    def _validate_activity_takes_a_single_arg(
        act_class: type,  # type: ignore[reportSelfClsParameterName]
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

    @staticmethod
    def _validate_activity_input_arg_is_pydantic_serializable(
        act_class: type,  # type: ignore[reportSelfClsParameterName]
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

    @staticmethod
    def _validate_activity_output_is_pydantic_serializable(
        cls: type,  # type: ignore[reportSelfClsParameterName]
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


class BaseTemporalActivity:
    """Create an Activity class that inherits from this class to automatically enforce best practices for Temporal Activities.
    You can learn more about these guardrails by reading the `TemporalActivityValidators` docstring.

    Requires `pydantic` and the `pydantic_data_converter` for Temporal found in `converter.py`.

    What best practices are we trying to follow?:
        1. The Activity's author should be able to provide info on how to call the Activity (retries, timeouts, etc),\
                because they are the subject matter expert on that function's intended usage.
        2. The Activity should take a single input argument, which is a JSON-serializable object (pydantic basemodel) \
                because this provides backwards compatibility by adding new activity params while keepin the fn signature static.
        3. the Activity should return a single output argument for the same reason as #2.
        4. Pydantic is a great way to ensure that the input/output of the Activity is serializable to JSON.

    Other tips for writing activities:
        - If you want to share resources like database clients, you can either add them as an attribute to the class \
            or share them via the contextvars pattern. If you are using class attributes, make sure they are async-safe \
            and that you initialize your class before passing it to the worker constructor.
        - Activities should be idempotent (retried multiple times without side effects) because Temporal guarantees \
            "at least once" execution consistency and your activity may be run multiple times.
        - Idempotency can be achieved by many ways, such as using a unique identifier as one of your input args.
        - If you don't already have an idempotency identifier, you can make one with `workflowRunId + "-" + activityId`
        - If your activity is async, audit it to make sure there aren't any secretly blocking and possibly long-running \
            functions which will clog up the worker.

    How to use `BaseTemporalActivity`:
    ```python
    from pydantic import BaseModel
    from base_class import BaseTemporalActivity
    from execution_options import default_temporal_execute_activity_options

    class MyActivityInput(BaseModel):
        some_field: str

    class MyActivityOutput(BaseModel):
        some_field: str

    class MyActivity(BaseTemporalActivity):
        @activity.defn
        async def my_first_activity(self, input: MyActivityInput) -> MyActivityOutput:
            pass

        # provides the activity caller with recommended params for `workflow.execute_activity`
        # this example uses opinionated defaults, but you can also use the raw TemporalExecActivityOptions typedict
        opts_my_first_activity = default_temporal_execute_activity_options

        @activity.defn
        async def my_second_activity(self, input: MyActivityInput) -> MyActivityOutput:
            pass

        # you can also use the defaults while overriding any field with your own values
        opts_my_second_activity = default_temporal_execute_activity_options | {
            "start_to_close_timeout": timedelta(minutes=60),
            "heartbeat_timeout": timedelta(seconds=30),
            "retry_policy": RetryPolicy(initial_interval=timedelta(seconds=5), backoff_coefficient=2.0, maximum_attempts=5)
        }
    ```
    """

    def __init_subclass__(cls, **kwargs):
        """Automatically runs the `TemporalActivityValidators` validations on all children, even without instantiation."""
        TemporalActivityValidators.run_validators(cls)

        # continue with normal subclass initialization
        super().__init_subclass__(**kwargs)
