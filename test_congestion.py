"""Unit tests for the real-time congestion estimator.

The small qns fallback makes these algorithm tests runnable even when SimQN is
not installed; production imports are used unchanged when it is available.
"""

import sys
import types
import unittest
from unittest.mock import patch


try:
    import qns  # noqa: F401
except ImportError:
    qns = types.ModuleType("qns")
    simulator_package = types.ModuleType("qns.simulator")
    simulator_module = types.ModuleType("qns.simulator.simulator")
    event_module = types.ModuleType("qns.simulator.event")
    ts_module = types.ModuleType("qns.simulator.ts")
    entity_package = types.ModuleType("qns.entity")
    entity_module = types.ModuleType("qns.entity.entity")
    node_package = types.ModuleType("qns.entity.node")
    node_module = types.ModuleType("qns.entity.node.node")
    channel_package = types.ModuleType("qns.entity.qchannel")
    channel_module = types.ModuleType("qns.entity.qchannel.qchannel")
    utils_package = types.ModuleType("qns.utils")
    log_module = types.ModuleType("qns.utils.log")

    class Simulator:
        pass

    class Event:
        def __init__(self, t=None, name=None, by=None):
            self.t = t
            self.name = name
            self.by = by

    class Time:
        pass

    class QNode:
        pass

    class Entity:
        pass

    class QuantumChannel:
        pass

    simulator_module.Simulator = Simulator
    event_module.Event = Event
    ts_module.Time = Time
    node_module.QNode = QNode
    entity_module.Entity = Entity
    channel_module.QuantumChannel = QuantumChannel
    log_module.debug = lambda *args, **kwargs: None

    modules = {
        "qns": qns,
        "qns.simulator": simulator_package,
        "qns.simulator.simulator": simulator_module,
        "qns.simulator.event": event_module,
        "qns.simulator.ts": ts_module,
        "qns.entity": entity_package,
        "qns.entity.entity": entity_module,
        "qns.entity.node": node_package,
        "qns.entity.node.node": node_module,
        "qns.entity.qchannel": channel_package,
        "qns.entity.qchannel.qchannel": channel_module,
        "qns.utils": utils_package,
        "qns.utils.log": log_module,
    }
    sys.modules.update(modules)


from entity import QNNode
from topo import Network


class FakeNetwork:
    def __init__(self, sender, destination, candidates):
        self.route_table = {destination: {sender: [2, []]}}
        self._candidates = candidates

    def query_route(self, src, dest):
        return self._candidates


class FakeQubit:
    def __init__(self, sender):
        self.curr = sender
        self.try_count = 1
        self.max_try_count = 3
        self.route = [sender]


class RealTimeCongestionTests(unittest.TestCase):
    def setUp(self):
        self.sender = QNNode("sender", allow_reroute=True)
        self.neighbor = QNNode("neighbor", memorySize=10)
        self.sender.query_list[self.neighbor] = [True] * 9 + [False]

    def test_estimator_blends_history_and_live_memory(self):
        self.neighbor.currentSize = 8
        state = self.sender.congestion_state(self.neighbor)

        expected_history = 9.5 / 10.5
        expected = 0.5 * expected_history + 0.5 * 0.2
        self.assertAlmostEqual(state.historical_acceptance, expected_history)
        self.assertEqual(state.memory_utilization, 0.8)
        self.assertAlmostEqual(state.estimated_acceptance, expected)

    def test_sudden_saturation_changes_estimate_without_new_history(self):
        self.neighbor.currentSize = 0
        uncongested = self.sender.stat2(self.neighbor)

        self.neighbor.currentSize = self.neighbor.memorySize
        congested = self.sender.stat2(self.neighbor)

        self.assertAlmostEqual(uncongested - congested, 0.5)
        self.assertEqual(self.sender.query_list[self.neighbor], [True] * 9 + [False])

    def test_history_weight_is_validated(self):
        with self.assertRaises(ValueError):
            QNNode("invalid", congestion_history_weight=1.1)

        with self.assertRaises(ValueError):
            Network(congestion_history_weight=-0.1)

    def test_weight_extremes_select_one_signal(self):
        self.neighbor.currentSize = self.neighbor.memorySize
        history_only = QNNode("history-only", congestion_history_weight=1.0)
        memory_only = QNNode("memory-only", congestion_history_weight=0.0)
        history_only.query_list[self.neighbor] = [True, False]

        self.assertEqual(
            history_only.stat2(self.neighbor),
            history_only.historical_stat2(self.neighbor),
        )
        self.assertEqual(memory_only.stat2(self.neighbor), 0.0)

    def test_network_propagates_history_weight_to_every_node(self):
        network = Network(n=2, p=1.0, congestion_history_weight=0.25)
        network.build()

        self.assertEqual(
            [node.congestion_history_weight for node in network.nodes],
            [0.25, 0.25],
        )

    def test_routing_avoids_a_neighbor_that_is_currently_full(self):
        destination = QNNode("destination")
        full = QNNode("full", memorySize=10)
        free = QNNode("free", memorySize=10)
        full.currentSize = full.memorySize
        full_link = object()
        free_link = object()
        candidates = [(full, full_link, 2), (free, free_link, 2)]
        self.sender.dest = destination
        self.sender.net = FakeNetwork(self.sender, destination, candidates)
        self.sender.query_list = {full: [True] * 10, free: [True] * 10}

        with patch("entity.random.random", return_value=1.0):
            _, selected, selected_link = self.sender.route(FakeQubit(self.sender))

        self.assertIs(selected, free)
        self.assertIs(selected_link, free_link)


if __name__ == "__main__":
    unittest.main()
