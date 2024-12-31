import asyncio
import inspect
import logging
from types import FunctionType, MethodType
from typing import Callable, Sequence, Type

from temporalio.client import Client
from temporalio.worker import Worker

from temporal_utils.converter import sandbox_runner_compatible_with_pydantic_converter
from temporal_utils.validation import TemporalActivityValidators


def _get_all_callables_from_object(module: object) -> list[object]:
    """Get all classes from a module."""
    all_callables = inspect.getmembers(module, callable)
    return [callable_tuple[1] for callable_tuple in all_callables]


def get_all_activity_methods_from_object(
    instance_or_class_type: object,
) -> list[MethodType | FunctionType]:
    """A helper for getting every @activity.defn method in a class to pass to a Worker.
    This means you don't need to remember to add it to the worker every time you add an activity, and
    you don't need to list them out manually.
    """

    all_methods = inspect.getmembers(
        instance_or_class_type,
        predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x),
    )

    activity_methods_tup = [
        method_tuple
        for method_tuple in all_methods
        # only use methods that are decorated with temporalio's @activity.defn
        if hasattr(method_tuple[1], TemporalActivityValidators.get_search_attribute())
    ]

    activity_methods = [method_tuple[1] for method_tuple in activity_methods_tup]

    return activity_methods  # type: ignore[no-any-return]


# used for interrupting the worker, do not delete
interrupt_event = asyncio.Event()


async def _init_worker_with_pydantic_sandbox(
    client_with_pydantic_converter: Client,
    worker_task_queue: str,
    workflows: Sequence[Type],
    activities: Sequence[Callable],
    **worker_init_kwargs,  # type: ignore[reportMissingParameterType] # noqa: no-untyped-def
) -> None:
    logging.basicConfig(level=logging.INFO)

    async with Worker(
        client_with_pydantic_converter,
        workflow_runner=sandbox_runner_compatible_with_pydantic_converter(),
        task_queue=worker_task_queue,
        workflows=workflows,
        activities=activities,
        **worker_init_kwargs,
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


def run_pydantic_worker_until_complete_in_new_asyncio_loop(
    client_with_pydantic_converter: Client,
    worker_task_queue: str,
    workflows: list,
    activities: list,
    **worker_init_kwargs,  # type: ignore[reportMissingParameterType]
):
    loop = asyncio.new_event_loop()

    try:
        loop.run_until_complete(
            _init_worker_with_pydantic_sandbox(
                client_with_pydantic_converter=client_with_pydantic_converter,
                worker_task_queue=worker_task_queue,
                workflows=workflows,
                activities=activities,
                **worker_init_kwargs,
            )
        )
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
