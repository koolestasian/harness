# harness

Minimal personal workflow/meta-harness for:

- cross-platform operation (pure Python stdlib)
- parallel multi-agent execution
- self-improving agent selection using historical quality
- quality-regression protection so optimization never degrades accepted output

## Usage

```python
from harness import MetaHarness

harness = MetaHarness(scorer=lambda output: float(len(output)))

result = harness.run(
    task_id="draft-email",
    prompt="Write a short update",
    agents={
        "agent_a": lambda p: f"A: {p}",
        "agent_b": lambda p: f"B: {p}!",
    },
)

print(result.agent, result.output, result.score, result.accepted)
```

## Test

```bash
python -m unittest discover -s tests -v
```