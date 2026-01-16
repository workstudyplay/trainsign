#!/usr/bin/env python3
"""
OpenTelemetry instrumentation setup for TRAINSIGN.

This module initializes OpenTelemetry tracing and exports traces to Jaeger.
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)


def setup_telemetry(
    service_name: str = "trainsign",
    jaeger_endpoint: Optional[str] = None,
    otlp_endpoint: Optional[str] = None,
    enabled: bool = True,
) -> Optional[trace.Tracer]:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service for tracing
        jaeger_endpoint: Jaeger collector endpoint (e.g., "http://localhost:14268/api/traces")
                        If None, reads from JAEGER_ENDPOINT env var
        otlp_endpoint: OTLP HTTP endpoint (alternative to Jaeger)
                      If None, reads from OTEL_EXPORTER_OTLP_ENDPOINT env var
        enabled: Whether to enable tracing (can be disabled via OTEL_SDK_DISABLED env var)

    Returns:
        Tracer instance if enabled, None otherwise
    """
    # Check if tracing is disabled
    if not enabled or os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        logger.info("OpenTelemetry tracing is disabled")
        return None

    # Get configuration from environment variables if not provided
    jaeger_endpoint = jaeger_endpoint or os.getenv("JAEGER_ENDPOINT")
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name = os.getenv("OTEL_SERVICE_NAME", service_name)

    # Create resource with service name
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Set up exporter(s)
    span_processor = None

    # Prefer OTLP if available (modern standard)
    if otlp_endpoint:
        logger.info(f"Setting up OTLP exporter to {otlp_endpoint}")
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        span_processor = BatchSpanProcessor(otlp_exporter)
    elif jaeger_endpoint:
        logger.info(f"Setting up Jaeger exporter to {jaeger_endpoint}")
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
            collector_endpoint=jaeger_endpoint,
        )
        span_processor = BatchSpanProcessor(jaeger_exporter)
    else:
        # Default: try local Jaeger
        logger.info("No endpoint specified, using default Jaeger localhost:6831")
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        span_processor = BatchSpanProcessor(jaeger_exporter)

    if span_processor:
        provider.add_span_processor(span_processor)
        logger.info(f"OpenTelemetry tracing initialized for service: {service_name}")
        return trace.get_tracer(__name__)
    else:
        logger.warning("No span processor configured, tracing disabled")
        return None


def get_tracer(name: str = __name__) -> trace.Tracer:
    """
    Get a tracer instance.

    Args:
        name: Name for the tracer (typically __name__)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
