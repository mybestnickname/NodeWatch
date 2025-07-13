# NodeWatch

NodeWatch is a lightweight FastAPI-based service for monitoring file integrity, disk space, and physical tampering on Linux servers.

Checks can be executed in two modes:
- **Asynchronously**, via a background task queue with throttling support, allowing the system to schedule and limit concurrent load.
- **Synchronously**, when an immediate response is needed — the result is returned directly in the API call.

Checks can also be triggered on a schedule or on demand.