# OpenTelemetry Setup Guide

This project uses OpenTelemetry for distributed tracing with Jaeger as the backend.

## Quick Start

### 1. Start Jaeger

Using Docker Compose (recommended):

```bash
docker-compose up -d jaeger
```

Or using Docker directly:

```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 6831:6831/udp \
  -p 14268:14268 \
  -e COLLECTOR_OTLP_ENABLED=true \
  jaegertracing/all-in-one:latest
```

### 2. Access Jaeger UI

Once Jaeger is running, open your browser to:
- **Jaeger UI**: http://localhost:16686

### 3. Configure Backend (Python)

The backend automatically initializes OpenTelemetry when the Flask app starts. You can configure it using environment variables:

```bash
# Optional: Set Jaeger endpoint (defaults to localhost:6831)
export JAEGER_ENDPOINT=http://localhost:14268/api/traces

# Optional: Use OTLP instead (modern standard)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces

# Optional: Set service name
export OTEL_SERVICE_NAME=trainsign-api

# Optional: Disable tracing
export OTEL_SDK_DISABLED=true
```

### 4. Configure Frontend (React)

The frontend uses environment variables in Vite:

Create a `.env` file in the `ui/` directory:

```bash
# .env
VITE_JAEGER_ENDPOINT=http://localhost:4318/v1/traces
VITE_OTEL_ENABLED=true
```

Or set them when running:

```bash
VITE_JAEGER_ENDPOINT=http://localhost:4318/v1/traces npm run dev
```

## Architecture

### Backend Instrumentation

- **Flask routes**: Automatically instrumented via `FlaskInstrumentor`
- **HTTP requests**: Automatically instrumented via `RequestsInstrumentor`
- **Custom spans**: Added for:
  - Worker refresh cycles
  - GTFS-RT data fetching
  - Buffer updates
  - Broadcast messages

### Frontend Instrumentation

- **Fetch API**: Automatically instrumented
- **XMLHttpRequest**: Automatically instrumented
- **React components**: Can be manually instrumented if needed

## Viewing Traces

1. Start your application (backend and frontend)
2. Make some API calls from the UI
3. Open Jaeger UI at http://localhost:16686
4. Select the service name (`trainsign-api` or `trainsign-ui`)
5. Click "Find Traces"

## Trace Structure

A typical trace will show:

```
HTTP Request (from frontend)
  └─ Flask Route Handler
      └─ Worker Refresh Cycle
          └─ Fetch Arrivals
              ├─ HTTP Request (to MTA API)
              └─ Parse GTFS-RT
                  └─ Update Buffers
```

## Troubleshooting

### No traces appearing in Jaeger

1. Check that Jaeger is running: `docker ps | grep jaeger`
2. Verify endpoints match in your configuration
3. Check browser console for OpenTelemetry errors
4. Check backend logs for OpenTelemetry initialization messages

### Traces not connecting (frontend to backend)

1. Ensure CORS is configured correctly
2. Verify `propagateTraceHeaderCorsUrls` includes your API URL
3. Check that both services are using compatible trace formats

### Performance impact

OpenTelemetry has minimal overhead, but you can disable it:

**Backend:**
```bash
export OTEL_SDK_DISABLED=true
```

**Frontend:**
```bash
VITE_OTEL_ENABLED=false npm run dev
```

## Production Considerations

For production:

1. **Use OTLP exporter** instead of Jaeger-specific exporter (more standard)
2. **Set up a proper Jaeger collector** instead of all-in-one
3. **Configure sampling** to reduce trace volume:
   ```python
   from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
   provider = TracerProvider(
       sampler=TraceIdRatioBased(0.1)  # Sample 10% of traces
   )
   ```
4. **Use environment variables** for all configuration
5. **Monitor trace volume** to avoid overwhelming the collector

## Additional Resources

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry JavaScript Documentation](https://opentelemetry.io/docs/instrumentation/js/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
