"""Inspired by https://github.com/temporalio/samples-python/blob/main/pydantic_converter/converter.py

When using pydantic, we also need to pass through the data_converter via the sandbox to the workflow

We always want to pass through external modules to the sandbox that we know
are safe for workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

    from pydantic_converter.converter import pydantic_data_converter
"""

import dataclasses
import json
from typing import Any, Mapping, Optional, Sequence, TypedDict, Union

import temporalio.client
import temporalio.common
import temporalio.converter
import temporalio.runtime
import temporalio.service
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
from typing_extensions import Unpack


# https://github.com/temporalio/samples-python/blob/main/pydantic_converter/converter.py
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


# https://github.com/temporalio/samples-python/blob/main/pydantic_converter/converter.py
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
"""Pass this into the Temporal Client and the Worker to ensure that
    the workflow input is converted using Pydantic's JSON encoder.
"""


class ClientConnectArgsRequired(TypedDict):
    target_host: str
    namespace: str


class ClientConnectArgsOptional(TypedDict, total=False):
    api_key: Optional[str]
    data_converter: temporalio.converter.DataConverter
    interceptors: Sequence[temporalio.client.Interceptor]
    default_workflow_query_reject_condition: Optional[
        temporalio.common.QueryRejectCondition
    ]
    tls: Union[bool, temporalio.service.TLSConfig]
    retry_config: Optional[temporalio.service.RetryConfig]
    keep_alive_config: Optional[temporalio.service.KeepAliveConfig]
    rpc_metadata: Mapping[str, str]
    identity: Optional[str]
    lazy: bool
    runtime: Optional[temporalio.runtime.Runtime]
    http_connect_proxy_config: Optional[temporalio.service.HttpConnectProxyConfig]


class ClientConnectArgs(ClientConnectArgsRequired, ClientConnectArgsOptional):
    """See `temporalio.client.Client.connect()` for more details"""

    pass


async def create_client_with_pydantic_converter(
    **client_connect_kwargs: Unpack[ClientConnectArgs],
) -> Client:
    """When executing a workflow via a temporal Client, you must pass in the `pydantic_data_converter` instance
    as the `data_converter` argument for the `start_workflow()` or execute_workflow() methods. This will ensure
    that the workflow input is converted using Pydantic's JSON encoder.
    """
    client_connect_kwargs["data_converter"] = pydantic_data_converter

    pydantic_compatible_temporal_client = await Client.connect(**client_connect_kwargs)
    return pydantic_compatible_temporal_client


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
