from typing import Any
from temporal_utils.validation import TemporalActivityValidators


class BaseActivityValidated:
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

    How to use `BaseActivityValidated`:
    ```python
    from pydantic import BaseModel
    from base_class import BaseActivityValidated
    from execution_options import default_temporal_execute_activity_options

    class MyActivityInput(BaseModel):
        some_field: str

    class MyActivityOutput(BaseModel):
        some_field: str

    class MyActivity(BaseActivityValidated):
        # if you want to share resources like database clients, you can add them as an attribute to the class
        # and initialize them in the class's __init__ method. Make sure you pass the instance to the worker constructor.
        def __init__(self, some_db_client: SomeDbClient):
            self.some_db_client = some

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

    def __init_subclass__(cls: type, **kwargs: dict[str, Any]) -> None:
        """Automatically runs the `TemporalActivityValidators` validations on all children, even without instantiation."""
        TemporalActivityValidators.run_validators(cls)

        # continue with normal subclass initialization
        super().__init_subclass__(**kwargs)  # type: ignore[misc]
