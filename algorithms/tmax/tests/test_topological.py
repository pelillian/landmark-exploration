import math
import random
from string import ascii_lowercase
from unittest import TestCase

import numpy as np
import networkx as nx

from algorithms.tests.test_wrappers import TEST_ENV_NAME
from algorithms.tmax.topological_map import TopologicalMap
from utils.envs.doom.doom_utils import doom_env_by_name, make_doom_env
from utils.graph import plot_graph
from utils.utils import log


class TestGraph(TestCase):
    def test_topological_graph(self):
        env = make_doom_env(doom_env_by_name(TEST_ENV_NAME))
        initial_obs = env.reset()

        m = TopologicalMap(initial_obs, directed_graph=True)
        self.assertEqual(len(m.landmarks), 1)
        self.assertEqual(len(m.adjacency), 1)
        self.assertEqual(len(m.adjacency[m.curr_landmark_idx]), 0)
        self.assertTrue(np.array_equal(initial_obs, m.curr_landmark))

        obs, _, _, _ = env.step(0)
        new_landmark_idx = m.add_landmark(obs)
        self.assertEqual(new_landmark_idx, 1)

        m.set_curr_landmark(new_landmark_idx)

        self.assertEqual(len(m.landmarks), 2)
        self.assertEqual(len(m.adjacency), 2)
        self.assertEqual(len(m.adjacency[m.curr_landmark_idx]), 0)  # directed edge
        self.assertIn(1, m.adjacency[0])
        self.assertTrue(np.array_equal(obs, m.curr_landmark))

        self.assertEqual(len(m.neighbor_indices()), 1)
        self.assertEqual(len(m.non_neighbor_indices()), 1)

        self.assertEqual(sorted(m.reachable_indices(1)), [1])
        self.assertEqual(sorted(m.reachable_indices(0)), [0, 1])

        path = m.get_path(0, 1)
        self.assertEqual(path, [0, 1])

    def test_shortest(self):
        m = TopologicalMap(np.array(0), directed_graph=False)
        for i in range(4):
            idx = m.add_landmark(np.array(0))
            m.adjacency[idx] = []

        m.adjacency[0] = []

        m._add_edge(0, 1)
        m._add_edge(0, 2)
        m._add_edge(1, 3)
        m._add_edge(2, 3)

        path = m.get_path(0, 3)
        log.debug('Path from 0 to 3 is %r', path)

        m.update_edge_traversal(0, 1, 0)

        path = m.get_path(0, 3)
        log.debug('Path from 0 to 3 is %r', path)
        self.assertEqual(path, [0, 2, 3])

        m.update_edge_traversal(2, 3, 0)
        m.update_edge_traversal(2, 3, 0)

        path = m.get_path(0, 3)
        log.debug('Path from 0 to 3 is %r', path)
        self.assertEqual(path, [0, 1, 3])

        m.update_edge_traversal(2, 3, 1)
        m.update_edge_traversal(2, 3, 1)
        m.update_edge_traversal(0, 2, 1)

        path = m.get_path(0, 3)
        log.debug('Path from 0 to 3 is %r', path)
        self.assertEqual(path, [0, 2, 3])

        m.remove_edge(2, 3)

        path = m.get_path(0, 3)
        log.debug('Path from 0 to 3 is %r', path)
        self.assertEqual(path, [0, 1, 3])

        for i in range(5):
            m.update_edge_traversal(0, 1, 0)

        m._prune(threshold=0.05)

        path = m.get_path(0, 3)
        log.debug('Path from 0 to 3 is %r', path)
        self.assertIs(path, None)

        m._prune_vertices(chance=0.1)
        m._prune_vertices(chance=0.2)
        m._prune_vertices(chance=0.3)
        m._prune_vertices(chance=0.4)

        m._prune_vertices(chance=1.0)
        self.assertEqual(len(m.landmarks), 1)

    def test_paths(self):
        m = TopologicalMap(np.array(0), directed_graph=True)

        for i in range(20):
            m.add_landmark(np.array(0))

        m.adjacency[0] = []

        for i, adj in enumerate(m.adjacency):
            if i > len(m.adjacency) - 3:
                continue

            if random.random() < 0.9:
                for j in range(random.randint(1, 3)):
                    rand = random.randint(0, len(m.adjacency) - 1)
                    if rand != 0 and rand != i and rand not in adj:
                        m._add_edge(i, rand)

        shortest, _ = m.shortest_paths(0)
        m._prune_vertices(chance=0.1)
        reachable = m.reachable_indices(0)
        self.assertGreaterEqual(len(reachable), 1)
        log.debug('Reachable vertices: %r', reachable)

        max_path_idx = -1
        max_path_length = -1
        for i, path_length in enumerate(shortest):
            if path_length == math.inf:
                continue
            if path_length > max_path_length:
                max_path_length = path_length
                max_path_idx = i

        path = m.get_path(0, max_path_idx)
        log.debug('Shortest path from %d to %d is %r', 0, max_path_idx, path)

        relabeling = {}
        for i, s in enumerate(shortest):
            if i != 0:
                for c in ascii_lowercase:
                    new_s = str(s) + c
                    if new_s not in relabeling.values():
                        relabeling[i] = new_s
                        break
            else:
                relabeling[i] = s

        graph = m.to_nx_graph()
        new_graph = nx.relabel_nodes(graph, relabeling)

        figure = plot_graph(new_graph, layout='kamada_kawai')
        # from matplotlib import pyplot as plt
        # plt.show()
        figure.clear()

    def test_plot_coordinates(self):
        m = TopologicalMap(np.array(0), directed_graph=True, initial_pos=[300, 400, 0])

        for i in range(1, 4):
            for j in range(1, 4):
                m.add_landmark(np.array(0), pos=[300 + i, 400 + j, 10])

        graph = m.to_nx_graph()
        figure = plot_graph(graph, layout='pos')
        # from matplotlib import pyplot as plt
        # plt.show()
        figure.clear()
