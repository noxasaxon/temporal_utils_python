import asyncio
import concurrent.futures
from datetime import timedelta
from typing import Awaitable, Callable, Optional, Sequence, Type, TypedDict

from temporalio.client import Client
from temporalio.worker import SharedStateManager, Worker, WorkerTuner
from temporalio.worker._interceptor import Interceptor
from temporalio.worker._workflow_instance import WorkflowRunner
from typing_extensions import Unpack

from temporal_utils.converter import sandbox_runner_compatible_with_pydantic_converter


# create a typed dict of the Worker's init parameters
class WorkerRequiredParams(TypedDict):
    client: Client
    task_queue: str
    activities: Sequence[Callable]
    workflows: Sequence[Type]


class WorkerOptionalParams(TypedDict, total=False):
    activity_executor: Optional[concurrent.futures.Executor]
    workflow_task_executor: Optional[concurrent.futures.ThreadPoolExecutor]
    workflow_runner: WorkflowRunner
    unsandboxed_workflow_runner: WorkflowRunner
    interceptors: Sequence[Interceptor]
    build_id: Optional[str]
    identity: Optional[str]
    max_cached_workflows: int
    max_concurrent_workflow_tasks: Optional[int]
    max_concurrent_activities: Optional[int]
    max_concurrent_local_activities: Optional[int]
    tuner: Optional[WorkerTuner]
    max_concurrent_workflow_task_polls: int
    nonsticky_to_sticky_poll_ratio: float
    max_concurrent_activity_task_polls: int
    no_remote_activities: bool
    sticky_queue_schedule_to_start_timeout: timedelta
    max_heartbeat_throttle_interval: timedelta
    default_heartbeat_throttle_interval: timedelta
    max_activities_per_second: Optional[float]
    max_task_queue_activities_per_second: Optional[float]
    graceful_shutdown_timeout: timedelta
    workflow_failure_exception_types: Sequence[Type[BaseException]]
    shared_state_manager: Optional[SharedStateManager]
    debug_mode: bool
    disable_eager_activity_execution: bool
    on_fatal_error: Optional[Callable[[BaseException], Awaitable[None]]]
    use_worker_versioning: bool
    disable_safe_workflow_eviction: bool


class AllWorkerParams(WorkerRequiredParams, WorkerOptionalParams):
    """See `temporalio.worker.Worker` for more details"""

    pass


def build_worker_params(
    worker_required_params: WorkerRequiredParams,
    rest_of_params: WorkerOptionalParams,
) -> AllWorkerParams:
    return AllWorkerParams(**worker_required_params, **rest_of_params)


# used for interrupting the worker, do not delete
interrupt_event = asyncio.Event()


def run_pydantic_worker_until_complete(
    client_with_pydantic_converter: Client,
    worker_task_queue: str,
    workflows: list,
    activities: list,
    **worker_params: Unpack[WorkerOptionalParams],
):
    # TODO: enforce that the client has a pydantic compatible data converter via static typing

    required_params: WorkerRequiredParams = {
        "client": client_with_pydantic_converter,
        "task_queue": worker_task_queue,
        "workflows": workflows,
        "activities": activities,
    }

    # set up the worker with the pydantic compatible workflow runner
    worker_params["workflow_runner"] = (
        sandbox_runner_compatible_with_pydantic_converter()
    )

    async def init_worker():
        async with Worker(**required_params, **worker_params):
            # Wait until interrupted
            print("Worker started, ctrl+c to exit")
            await interrupt_event.wait()
            print("Shutting down")

    loop = asyncio.new_event_loop()

    try:
        loop.run_until_complete(init_worker())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
