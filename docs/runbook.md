# Runbook: Prox Execution Framework

## 1. Deployment & Execution

This prototype is built using standard Python `asyncio` libraries. It mocks external network calls to simulate latency, rate limits, and proxy blocks.

### Local Simulation Setup
No external dependencies are required.

1. Clone the repository:
   git clone https://github.com/pnagre05/ProxTakeHomeAssessmentPranavNagre.git
   cd ProxTakeHomeAssessmentPranavNagre

2. Execute the simulation:
   python main.py

### Production Deployment (Future Scope)
To deploy this architecture in a live cloud environment (e.g., Azure or AWS):

* **Workers:** Containerize `worker()` logic using Docker and deploy via Azure Container Apps (with KEDA autoscaling) or AWS ECS.
* **Queue:** Replace `asyncio.Queue` with a distributed message broker like Azure Service Bus or AWS SQS.
* **State Management:** Implement Azure Cache for Redis for the deduplication node and Azure Database for PostgreSQL for persistent storage.
* **Proxy Management:** Introduce an Intelligent Proxy Management Service to handle residential IP rotation, session binding, and header randomization to mitigate `403` errors.

---

## 2. Observability & Monitoring

The simulation uses formatted, timestamped standard logging to track the lifecycle of every request. 

### Reading the Logs
Logs are formatted as: `HH:MM:SS | LEVEL | [Component/Worker-Name] Message`

* **`INFO`:** Standard operations (Queuing, Processing, Success, Cache Updates).
* **`WARNING`:** Retries triggered by `HTTP 403` or `HTTP 429` errors. Indicates the exponential backoff is engaged.
* **`ERROR`:** Terminal failures where a job has exhausted all retries and is moved to the Dead Letter Queue (DLQ).

---

## 3. Incident Response Guide

| Scenario | Symptom | Root Cause | Mitigation |
| :--- | :--- | :--- | :--- |
| **Rate Limiting** | High rate of `HTTP 429` warnings. Throughput crawls. | Target WAF is overwhelmed or internal concurrency is too high. | Decrease the `asyncio.Semaphore()` value or increase the base backoff multiplier. |
| **Proxy Blocks** | Spikes in `HTTP 403` warnings. | IP or browser fingerprint flagged as a bot. | Trigger proxy rotation via the Secret Manager and randomize HTTP headers. |
| **Dead Letter Queue Spikes** | Jobs dropping to `FAILED`. | Extended outage, permanent IP ban, or HTML structure change. | Inspect target endpoint. Deploy parsing patch or rotate master proxy pool. |
