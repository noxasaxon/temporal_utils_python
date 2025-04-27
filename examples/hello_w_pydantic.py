from pydantic import BaseModel
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta


class MyDatabaseClient:
    async def run_database_update(self) -> None:
        print("Database update executed")


class ExampleActInput(BaseModel):
    some_field: str


class ExampleActOutput(BaseModel):
    some_field: str


class MyActivities:
    def __init__(self, db_client: MyDatabaseClient) -> None:
        self.db_client = db_client

    opts_do_database_thing = {
        "start_to_close_timeout": timedelta(seconds=10),
        "retry_policy": RetryPolicy(
            backoff_coefficient=2.0,
        ),
        "heartbeat_timeout": timedelta(seconds=10),
    }

    @activity.defn
    async def do_database_thing(self, act_input: ExampleActInput) -> ExampleActOutput:
        await self.db_client.run_database_update()
        return ExampleActOutput(some_field="some_value")


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> None:
        act_input = ExampleActInput(some_field="some_value")
        await workflow.execute_activity_method(
            MyActivities.do_database_thing,
            act_input,
            start_to_close_timeout=timedelta(seconds=10),
        )
