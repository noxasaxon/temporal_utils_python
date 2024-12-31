import dataclasses
import json
from typing import Any, Optional

from pydantic_core import to_jsonable_python
from temporalio.api.common.v1 import Payload
from temporalio.client import Client
from temporalio.converter import (
    CompositePayloadConverter,
    DataConverter,
    DefaultPayloadConverter,
    JSONPlainPayloadConverter,
)
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)


class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """

    def to_payload(self, value: Any) -> Optional[Payload]:
        """Convert all values with Pydantic encoder or fail.

        Like the base class, we fail if we cannot convert. This payload
        converter is expected to be the last in the chain, so it can fail if
        unable to convert.
        """
        # We let JSON conversion errors be thrown to caller
        return Payload(
            metadata={"encoding": self.encoding.encode()},
            data=json.dumps(
                value, separators=(",", ":"), sort_keys=True, default=to_jsonable_python
            ).encode(),
        )


class PydanticPayloadConverter(CompositePayloadConverter):
    """Payload converter that replaces Temporal JSON conversion with Pydantic
    JSON conversion.
    """

    def __init__(self) -> None:
        super().__init__(
            *(
                c
                if not isinstance(c, JSONPlainPayloadConverter)
                else PydanticJSONPayloadConverter()
                for c in DefaultPayloadConverter.default_encoding_payload_converters
            )
        )


pydantic_data_converter = DataConverter(
    payload_converter_class=PydanticPayloadConverter
)
"""Data converter using Pydantic JSON conversion."""


# we also need to pass through the data_converter via the sandbox to the workflow

# We always want to pass through external modules to the sandbox that we know
# are safe for workflow use
# with workflow.unsafe.imports_passed_through():
#     from pydantic import BaseModel

#     from pydantic_converter.converter import pydantic_data_converter


async def create_client_with_pydantic_converter(
    host_url: str, **client_kwargs
) -> Client:
    """When executing a workflow via a temporal Client, you must pass in the `pydantic_data_converter` instance
    as the `data_converter` argument for the `start_workflow()` or execute_workflow() methods. This will ensure
    that the workflow input is converted using Pydantic's JSON encoder.
    """
    client = await Client.connect(
        target_host=host_url, data_converter=pydantic_data_converter, **client_kwargs
    )
    return client


# Due to known issues with Pydantic's use of issubclass and our inability to
# override the check in sandbox, Pydantic will think datetime is actually date
# in the sandbox. At the expense of protecting against datetime.now() use in
# workflows, we're going to remove datetime module restrictions. See sdk-python
# README's discussion of known sandbox issues for more details.
def sandbox_runner_compatible_with_pydantic_converter() -> SandboxedWorkflowRunner:
    return SandboxedWorkflowRunner(
        restrictions=dataclasses.replace(
            SandboxRestrictions.default,
            invalid_module_members=SandboxRestrictions.invalid_module_members_default.with_child_unrestricted(
                "datetime"
            ),
        )
    )
