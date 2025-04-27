from datetime import timedelta

from temporalio.workflow import ActivityConfig

## Collection of best-practice Temporal Activity execution options from the community
# Temporal @ Stripe learnings: https://www.youtube.com/watch?v=yeoawVIn060
# Temporal Blog Post: https://temporal.io/blog/activity-timeouts
# Interactive Tool - Activity Retry Simulator: https://docs.temporal.io/develop/activity-retry-simulator
# Tales from the Temporal Trenches: https://www.youtube.com/watch?v=sSOjD45Yu7g
default_temporal_execute_activity_options: ActivityConfig = {
    #
    # max time of a single Execution of the Activity (should always be set!)
    "start_to_close_timeout": timedelta(minutes=30),
    #
    # max overrall execution time INCLUDING retries
    "schedule_to_close_timeout": None,
    #
    # Limits the maximum time between Heartbeats. For long running Activities, enables a quicker response when a Heartbeat fails to be recorded.
    "heartbeat_timeout": None,
    #
    # Setting an activity retry policy: https://docs.temporal.io/encyclopedia/retry-policies
    "retry_policy": None,
    #
    # DANGER! Time that the Activity Task can stay in the Task Queue before it is picked up by a Worker.
    # used for queue timeouts and task routing. Not retryable, rarely needs to be used.
    "schedule_to_start_timeout": None,
}
"""Type of options that can be set when running a Temporal Activity from a workflow.
    Use this type to define the default options for each activity in a class that inherits from `BaseActivityValidated`.

    Example:
    ```python

    class MyActivity(BaseActivityValidated):
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


default_temporal_execute_workflow_options = {
    # maximum allowed duration of an entire workflow execution, including retries and any "Continue As New" operations
    "execution_timeout": timedelta(days=3),
    # limits the duration of a single workflow execution (run) within that overall execution chain
    "run_timeout": timedelta(days=3),
    #
    # For string workflows, this can set the specific result type hint to deserialize into.
    # "result_type":
    #
    # Timeout for a single workflow task.
    # "task_timeout":
    #
    # How already-existing IDs are treated.
    # "id_reuse_policy":
    #
    # How already-running workflows of the same ID are treated. Default is unspecified which effectively means fail the
    #     start attempt. This cannot be set if ``id_reuse_policy`` is set
    #     to terminate if running.
    # "id_conflict_policy":
    #
    # Retry policy for the workflow.
    # "retry_policy":
    #
    # See https://docs.temporal.io/docs/content/what-is-a-temporal-cron-job/
    # "cron_schedule":
    #
    # "memo":
    # Memo for the workflow.
    #
    # Search attributes for the workflow. The dictionary form of this is deprecated, use :py:class:`temporalio.common.TypedSearchAttributes`.
    # "search_attributes":
    #
    # Amount of time to wait before starting the workflow. This does not work with `cron_schedule`.
    # "start_delay":
    #
    # If present, this signal is sent as signal-with-start instead of traditional workflow start.
    # "start_signal":
    #
    # "start_signal_args": Arguments for start_signal if start_signal present.
    #
    # Headers used on the RPC call. Keys here override client-level RPC metadata keys.
    # "rpc_metadata":
    #
    # Optional RPC deadline to set for the RPC call.
    # "rpc_timeout":
    #
    # Potentially reduce the latency to start this workflow by encouraging the server to start it on a local worker running with
    #     this same client. THIS IS EXPERIMENTAL.
    # request_eager_start:
}
