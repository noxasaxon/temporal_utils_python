import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from examples.hello_w_pydantic import (
    MyActivities,
    MyDatabaseClient,
    MyWorkflow,
)
from temporal_utils.collectors import (
    get_all_activity_methods_from_object,
)

# used implicity in the workflow (and therefore needed as a sandbox import) \
# because it will be started with this dataconverter passed as an argument
from temporal_utils.converter import (
    pydantic_data_converter,  # noqa: F401 # type: ignore[reportUnusedImport]
    sandbox_runner_compatible_with_pydantic_converter,
)


async def main() -> None:
    # Start client
    client = await Client.connect(
        "localhost:7233", data_converter=pydantic_data_converter
    )

    # Create our database client that can then be used in the activity
    db_client = MyDatabaseClient()
    # Instantiate our class containing state that can be referenced from
    # activity methods
    my_activities = MyActivities(db_client)

    collected_act_fns = get_all_activity_methods_from_object(my_activities)

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-activity-method-task-queue",
        workflows=[MyWorkflow],
        activities=collected_act_fns,
        workflow_runner=sandbox_runner_compatible_with_pydantic_converter(),
    ):
        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        await client.execute_workflow(
            MyWorkflow.run,
            id="hello-activity-method-workflow-id",
            task_queue="hello-activity-method-task-queue",
        )


if __name__ == "__main__":
    asyncio.run(main())
