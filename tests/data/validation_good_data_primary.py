from datetime import timedelta

from pydantic import BaseModel
from temporalio import activity
from temporalio.common import RetryPolicy

from temporal_utils.base_class import BaseActivityValidated

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


class ActivityInput(BaseModel):
    result: str


class ActivityOutput(BaseModel):
    result: str


class GrandParentBase(BaseActivityValidated):
    pass


class ActivityParent(GrandParentBase):
    @activity.defn
    async def parent_activity(self, act_input: ActivityInput) -> ActivityOutput:
        return ActivityOutput(result="success")

    opts_parent_activity = act_options


class ActivityChild(ActivityParent):
    @activity.defn
    async def child_activity(self, act_input: ActivityInput) -> ActivityOutput:
        return ActivityOutput(result="success")

    opts_child_activity = act_options


class ActivityGrandChild(ActivityChild):
    @activity.defn
    async def grandchild_activity(self, act_input: ActivityInput) -> ActivityOutput:
        return ActivityOutput(result="success")

    opts_grandchild_activity = act_options
