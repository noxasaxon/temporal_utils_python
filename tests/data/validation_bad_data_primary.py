from datetime import timedelta

from pydantic import BaseModel
from temporalio import activity
from temporalio.common import RetryPolicy


class ActivityInput(BaseModel):
    operation: str


class ActivityOutput(BaseModel):
    result: str


act_options = {
    "start_to_close_timeout": timedelta(minutes=30),
    "retry_policy": RetryPolicy(
        initial_interval=timedelta(seconds=5),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=1),
        maximum_attempts=5,
        non_retryable_error_types=[],
    ),
}


class ActivityWithoutOptions:
    @activity.defn
    async def activity_from_class_without_call_options_property(
        self,
        act_input: ActivityInput,
    ) -> ActivityOutput:
        return ActivityOutput(result="success")
