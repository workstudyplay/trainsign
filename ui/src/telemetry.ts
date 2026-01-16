/**
 * OpenTelemetry instrumentation for the frontend
 */

import { WebSDK } from '@opentelemetry/sdk-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-otlp-http';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';

const SERVICE_NAME = 'trainsign-ui';
const JAEGER_ENDPOINT = import.meta.env.VITE_JAEGER_ENDPOINT || 'http://localhost:4318/v1/traces';
const OTEL_ENABLED = import.meta.env.VITE_OTEL_ENABLED !== 'false';

let sdk: WebSDK | null = null;

export function initTelemetry(): void {
  if (!OTEL_ENABLED) {
    console.log('OpenTelemetry is disabled');
    return;
  }

  try {
    const traceExporter = new OTLPTraceExporter({
      url: JAEGER_ENDPOINT,
      headers: {},
    });

    sdk = new WebSDK({
      serviceName: SERVICE_NAME,
      traceExporter,
      instrumentations: [
        getWebAutoInstrumentations({
          // Enable fetch instrumentation
          '@opentelemetry/instrumentation-fetch': {
            propagateTraceHeaderCorsUrls: [
              /http:\/\/localhost:5002/,
              /http:\/\/127\.0\.0\.1:5002/,
            ],
            clearTimingResources: true,
          },
          // Enable XMLHttpRequest instrumentation
          '@opentelemetry/instrumentation-xml-http-request': {
            propagateTraceHeaderCorsUrls: [
              /http:\/\/localhost:5002/,
              /http:\/\/127\.0\.0\.1:5002/,
            ],
          },
        }),
      ],
    });

    sdk.start();
    console.log(`OpenTelemetry initialized for ${SERVICE_NAME}`);
    console.log(`Exporting traces to: ${JAEGER_ENDPOINT}`);
  } catch (error) {
    console.error('Failed to initialize OpenTelemetry:', error);
  }
}

export function shutdownTelemetry(): Promise<void> {
  if (sdk) {
    return sdk.shutdown();
  }
  return Promise.resolve();
}
