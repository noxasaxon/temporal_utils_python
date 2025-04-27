import asyncio
import os
from datetime import timedelta
from typing import Dict, Optional

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.runtime import OpenTelemetryConfig, Runtime, TelemetryConfig

runtime_with_telemetry: Optional[Runtime] = None


def get_runtime_with_telemetry() -> Optional[Runtime]:
    global runtime_with_telemetry
    if runtime_with_telemetry is None:
        runtime_with_telemetry = Runtime(
            telemetry=TelemetryConfig(
                metrics=OpenTelemetryConfig(
                    url=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://0.0.0.0:4317"),
                    metric_periodicity=timedelta(seconds=60),
                )
            )
        )
    return runtime_with_telemetry


class _TemporalClientManager:
    _instance = None
    _lock = asyncio.Lock()
    _clients: Dict[str, Client] = {}
    _tracing_interceptor = TracingInterceptor()  # We need to initialize this here so that it will be created after the trace is initialized

    def __new__(cls) -> "_TemporalClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_client(
        self,
        use_tls: bool,
        temporal_namespace: str,
        temporal_host: str,
        temporal_api_key: str,
    ) -> Client:
        async with self._lock:
            if temporal_namespace not in self._clients:
                telemetry_enabled = (
                    str(os.getenv("TELEMETRY_ENABLED", "")).lower() == "true"
                )
                interceptors = [self._tracing_interceptor] if telemetry_enabled else []

                client = await Client.connect(
                    target_host=temporal_host,
                    namespace=temporal_namespace,
                    api_key=temporal_api_key,
                    rpc_metadata={"temporal-namespace": temporal_namespace},
                    tls=use_tls,
                    runtime=get_runtime_with_telemetry() if telemetry_enabled else None,
                    interceptors=interceptors,
                    data_converter=pydantic_data_converter,
                )
                self._clients[temporal_namespace] = client
            return self._clients[temporal_namespace]


async def get_or_init_temporal_client(
    use_tls: bool,
    temporal_namespace: str,
    temporal_host: str,
    temporal_api_key: str,
) -> Client:
    manager = _TemporalClientManager()
    return await manager.get_client(
        use_tls, temporal_namespace, temporal_host, temporal_api_key
    )


def get_or_init_temporal_client_sync(
    use_tls: bool,
    temporal_namespace: str,
    temporal_host: str,
    temporal_api_key: str,
) -> Client:
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        get_or_init_temporal_client(
            use_tls, temporal_namespace, temporal_host, temporal_api_key
        )
    )
