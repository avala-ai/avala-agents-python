# avala-agents

Build custom annotation workflow agents for the [Avala](https://avala.ai) platform.

## Installation

```bash
pip install avala-agents
```

## Quick Start

```python
from avala_agents import TaskAgent

agent = TaskAgent(
    api_key="avk_...",
    name="quality-checker",
    project="proj_uid",  # optional: scope to a single project
)

@agent.on("result.submitted")
def check_quality(context):
    annotations = context.result_data

    if len(annotations) == 0:
        context.reject("No annotations found")
    elif context.result_metadata.get("confidence", 1.0) < 0.5:
        context.flag("Low confidence — needs manual review")
    else:
        context.approve()

agent.run()  # blocks; polls for pending executions
```

## Supported Events

| Event | Context class | Description |
|---|---|---|
| `result.submitted` | `ResultContext` | An annotator submitted a result |
| `result.accepted` | `ResultContext` | A result was accepted by QC |
| `result.rejected` | `ResultContext` | A result was rejected by QC |
| `task.completed` | `TaskContext` | A task reached a terminal state |

## Actions

All context objects expose four action methods:

| Method | Description |
|---|---|
| `context.approve(reason="")` | Accept the result / task |
| `context.reject(reason="")` | Reject with an optional reason |
| `context.flag(reason="")` | Flag for manual review |
| `context.skip()` | Acknowledge without taking action |

## Configuration

| Parameter | Env var | Default |
|---|---|---|
| `api_key` | `AVALA_API_KEY` | required |
| `base_url` | `AVALA_BASE_URL` | `https://api.avala.ai/api/v1` |
| `name` | — | `"default-agent"` |
| `project` | — | `None` (all projects) |
| `task_types` | — | `None` (all types) |
| `poll_interval` | — | `5.0` seconds |

## Processing a single batch (non-blocking)

```python
count = agent.run_once()
print(f"Processed {count} execution(s)")
```

## Error handling

```python
from avala_agents import AgentActionError, AgentRegistrationError

try:
    agent.run()
except AgentRegistrationError as exc:
    print(f"Could not register agent: {exc}")
```

## License

MIT
