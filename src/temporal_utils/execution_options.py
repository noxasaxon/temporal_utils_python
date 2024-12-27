from typing import TypedDict
from temporalio.common import RetryPolicy
from datetime import timedelta


class TemporalExecActivityOptions(TypedDict, total=False):
    """Type of options that can be set when running a Temporal Activity from a workflow.
    Use this type to define the default options for each activity in a class that inherits from `BaseTemporalActivity`.

    Example:
    ```python

    class MyActivity(BaseTemporalActivity):
        @activity.defn
        async def my_activity(self, input: MyInputType) -> MyOutputType:
            pass

        opts_my_activity = TemporalExecActivityOptions = {
            "retry_policy": RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(minutes=1),
                maximum_attempts=5,
                non_retryable_error_types=[MyNonRetryableError],
            )
        }
    """

    start_to_close_timeout: timedelta | None
    """max time of a single Execution of the Activity (should always be set!)"""
    heartbeat_timeout: timedelta | None
    """Limits the maximum time between Heartbeats. For long running Activities, enables a quicker response when a Heartbeat fails to be recorded."""
    retry_policy: RetryPolicy | None
    """Setting an activity retry policy: https://docs.temporal.io/encyclopedia/retry-policies"""
    schedule_to_close_timeout: timedelta | None
    """max overrall execution time INCLUDING retries"""
    schedule_to_start_timeout: timedelta | None
    """Time that the Activity Task can stay in the Task Queue before it is picked up  by a Worker.
    used for queue timeouts and task routing. Not retryable, rarely needs to be used!"""


"""max time of a single Execution of the Activity (should always be set!)"""


## Collection of best-practice Temporal Activity execution options from the community
# Temporal @ Stripe learnings: https://www.youtube.com/watch?v=yeoawVIn060
# Temporal Blog Post: https://temporal.io/blog/activity-timeouts
# Interactive Tool - Activity Retry Simulator: https://docs.temporal.io/develop/activity-retry-simulator
# Tales from the Temporal Trenches: https://www.youtube.com/watch?v=sSOjD45Yu7g
default_temporal_execute_activity_options: TemporalExecActivityOptions = {
    ## max overrall execution time INCLUDING retries
    "schedule_to_close_timeout": None,
    ## max time of a single Execution of the Activity (should always be set!)
    "start_to_close_timeout": timedelta(minutes=30),
    ## Limits the maximum time between Heartbeats. For long running Activities, enables a quicker response when a Heartbeat fails to be recorded.
    # "heartbeat_timeout": None
    #
    ## Setting an activity retry policy: https://docs.temporal.io/encyclopedia/retry-policies
    # retry_policy: Optional[temporalio.common.RetryPolicy] = None,
    #
    "schedule_to_start_timeout": None,
}


DEFAULT_WF_EXECUTION_TIMEOUT = timedelta(days=3)
DEFAULT_WF_RUN_TIMEOUT = timedelta(days=3)

default_temporal_execute_workflow_options = {
    # maximum allowed duration of an entire workflow execution, including retries and any "Continue As New" operations
    "execution_timeout": DEFAULT_WF_EXECUTION_TIMEOUT,
    # limits the duration of a single workflow execution (run) within that overall execution chain
    "run_timeout": DEFAULT_WF_RUN_TIMEOUT,
    # task_timeout: Optional[timedelta] = None,
    # id_reuse_policy: temporalio.common.WorkflowIDReusePolicy = temporalio.common.WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    # id_conflict_policy: temporalio.common.WorkflowIDConflictPolicy = temporalio.common.WorkflowIDConflictPolicy.UNSPECIFIED,
    # retry_policy: Optional[temporalio.common.RetryPolicy] = None,
    # cron_schedule: str = "",
    # memo: Optional[Mapping[str, Any]] = None,
    # search_attributes: Optional[
    #     Union[
    #         temporalio.common.TypedSearchAttributes,
    #         temporalio.common.SearchAttributes,
    #     ]
    # ] = None,
    # start_delay: Optional[timedelta] = None,
    # start_signal: Optional[str] = None,
    # start_signal_args: Sequence[Any] = [],
    # rpc_metadata: Mapping[str, str] = {},
    # rpc_timeout: Optional[timedelta] = None,
    # request_eager_start: bool = False,
}
