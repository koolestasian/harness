import time
import unittest

from harness.meta_harness import MetaHarness


class MetaHarnessTests(unittest.TestCase):
    def test_runs_agents_in_parallel(self):
        harness = MetaHarness(scorer=lambda output: float(len(output)))

        def slow_agent(_: str) -> str:
            time.sleep(0.2)
            return "slow-output"

        start = time.perf_counter()
        result = harness.run(
            task_id="parallel",
            prompt="go",
            agents={"one": slow_agent, "two": slow_agent},
        )
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.35)
        self.assertTrue(result.accepted)

    def test_self_improving_prefers_consistent_agent(self):
        harness = MetaHarness(scorer=lambda output: float(len(output)), exploration_weight=0.4)
        harness.run(
            task_id="warmup-a",
            prompt="go",
            agents={"alpha": lambda _: "high-quality", "beta": lambda _: "low"},
        )
        harness.run(
            task_id="warmup-b",
            prompt="go",
            agents={"alpha": lambda _: "high-quality", "beta": lambda _: "low"},
        )

        result = harness.run(
            task_id="decision",
            prompt="go",
            agents={"alpha": lambda _: "123456", "beta": lambda _: "1234567"},
        )

        self.assertEqual(result.agent, "alpha")
        self.assertTrue(result.accepted)

    def test_blocks_quality_regressions(self):
        harness = MetaHarness(scorer=lambda output: float(len(output)))
        initial = harness.run(
            task_id="quality",
            prompt="go",
            agents={"agent": lambda _: "excellent"},
        )
        regressed = harness.run(
            task_id="quality",
            prompt="go",
            agents={"agent": lambda _: "poor"},
        )

        self.assertTrue(initial.accepted)
        self.assertFalse(regressed.accepted)
        self.assertEqual(regressed.output, "excellent")
        self.assertEqual(regressed.reason, "quality_regression_blocked")


if __name__ == "__main__":
    unittest.main()
