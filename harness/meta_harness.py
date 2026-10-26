from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable


QualityScorer = Callable[[str], float]
Agent = Callable[[str], str]


class QualityRegressionError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentExecution:
    agent: str
    output: str
    score: float
    accepted: bool
    reason: str


class MetaHarness:
    """
    Personal workflow harness for cross-platform, parallel agent orchestration
    with quality-protected output selection.
    """

    def __init__(self, scorer: QualityScorer, exploration_weight: float = 0.15):
        self._scorer = scorer
        self._exploration_weight = exploration_weight
        self._history: dict[str, list[float]] = {}
        self._accepted_by_task: dict[str, AgentExecution] = {}

    @property
    def history(self) -> dict[str, list[float]]:
        return {agent: scores[:] for agent, scores in self._history.items()}

    def run(self, task_id: str, prompt: str, agents: dict[str, Agent]) -> AgentExecution:
        if not agents:
            raise ValueError("At least one agent is required")

        raw_results = self._run_parallel(prompt, agents)
        ranked = sorted(raw_results, key=self._rank_score, reverse=True)
        best = ranked[0]
        self._history.setdefault(best.agent, []).append(best.score)

        previous = self._accepted_by_task.get(task_id)
        if previous and best.score < previous.score:
            return AgentExecution(
                agent=previous.agent,
                output=previous.output,
                score=previous.score,
                accepted=False,
                reason="quality_regression_blocked",
            )

        accepted = AgentExecution(
            agent=best.agent,
            output=best.output,
            score=best.score,
            accepted=True,
            reason="accepted",
        )
        self._accepted_by_task[task_id] = accepted
        return accepted

    def _run_parallel(self, prompt: str, agents: dict[str, Agent]) -> list[AgentExecution]:
        results: list[AgentExecution] = []
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            futures = {
                pool.submit(agent_fn, prompt): agent_name
                for agent_name, agent_fn in agents.items()
            }
            for future in as_completed(futures):
                agent_name = futures[future]
                output = future.result()
                score = self._scorer(output)
                results.append(
                    AgentExecution(
                        agent=agent_name,
                        output=output,
                        score=score,
                        accepted=False,
                        reason="candidate",
                    )
                )
        return results

    def _rank_score(self, execution: AgentExecution) -> float:
        prior_scores = self._history.get(execution.agent)
        if not prior_scores:
            return execution.score
        historical_average = sum(prior_scores) / len(prior_scores)
        return execution.score + (self._exploration_weight * historical_average)
