from collections import deque
from hashlib import sha1

from utils.utils import log, ensure_contigious


def hash_observation(o):
    """Not the fastest way to do it, but plenty fast enough for our purposes."""
    o = ensure_contigious(o)
    return sha1(o).hexdigest()


class TopologicalMap:
    def __init__(self, initial_obs, directed_graph, verbose=False):
        self._verbose = verbose
        self._directed_graph = directed_graph

        self.landmarks = self.hashes = self.adjacency = None
        self.curr_landmark_idx = 0
        self.reset(initial_obs)

    def reset(self, obs):
        """Create the graph with only one vertex."""
        self.landmarks = [obs]
        self.hashes = [hash_observation(obs)]
        self.adjacency = [[]]  # initial vertex has no neighbors
        self.curr_landmark_idx = 0

    def _log_verbose(self, msg, *args):
        if not self._verbose:
            return
        log.debug(msg, *args)

    @property
    def curr_landmark(self):
        return self.landmarks[self.curr_landmark_idx]

    def neighbor_indices(self):
        neighbors = [self.curr_landmark_idx]
        neighbors.extend(self.adjacency[self.curr_landmark_idx])
        return neighbors

    def reachable_indices(self, start_idx):
        """Run BFS from current landmark to find the list of landmarks reachable from the current landmark."""
        q = deque([])
        q.append(start_idx)
        reachable = {start_idx}  # hash set of visited vertices

        while len(q) > 0:
            curr_idx = q.popleft()
            for adj_idx in self.adjacency[curr_idx]:
                if adj_idx in reachable:
                    continue
                reachable.add(adj_idx)
                q.append(adj_idx)

        return list(reachable)

    def non_neighbor_indices(self):
        neighbors = self.neighbor_indices()
        non_neighbors = [i for i in range(len(self.landmarks)) if i not in neighbors]
        return non_neighbors

    def _add_directed_edge(self, i1, i2):
        self.adjacency[i1].append(i2)
        self._log_verbose('New dir. edge %d-%d', i1, i2)

    def _add_undirected_edge(self, i1, i2):
        self.adjacency[i1].append(i2)
        self.adjacency[i2].append(i1)
        self._log_verbose('New und. edge %d-%d', i1, i2)

    def _add_edge(self, i1, i2):
        if self._directed_graph:
            self._add_directed_edge(i1, i2)
        else:
            self._add_undirected_edge(i1, i2)

    def set_curr_landmark(self, landmark_idx):
        """Replace current landmark with the given landmark. Create necessary edges if needed."""

        if landmark_idx == self.curr_landmark_idx:
            return

        if landmark_idx not in self.adjacency[self.curr_landmark_idx]:
            # create new edges, we found a loop closure!
            self._add_edge(self.curr_landmark_idx, landmark_idx)

        self._log_verbose('Change current landmark to %d', landmark_idx)
        self.curr_landmark_idx = landmark_idx

    def add_landmark(self, obs):
        new_landmark_idx = len(self.landmarks)
        self.landmarks.append(obs)
        self.hashes.append(hash_observation(obs))

        self.adjacency.append([])
        self._add_edge(self.curr_landmark_idx, new_landmark_idx)
        assert len(self.adjacency) == len(self.landmarks)
        self._log_verbose('Added new landmark %d', new_landmark_idx)
        return new_landmark_idx

    def num_edges(self):
        """Helper function for summaries."""
        num_edges = sum([len(adj) for adj in self.adjacency])
        return num_edges

    def shortest_paths(self, idx):
        distances = [float('inf')] * len(self.landmarks)
        distances[idx] = 0
        previous = [None] * len(self.landmarks)
        unvisited = list(range(len(self.landmarks)))

        while unvisited:
            u = min(unvisited, key=lambda node: distances[node])
            unvisited.remove(u)
            for neighbor in self.adjacency[u]:
                this_distance = distances[u] + 1  # distance between each node is 1
                if this_distance < distances[neighbor]:
                    distances[neighbor] = this_distance
                    previous[neighbor] = u

        return distances, previous

    def get_path(self, from_idx, to_idx):
        path_lengths, path_prev = self.shortest_paths(from_idx)
        if path_prev[to_idx] is None:
            return None

        path = [to_idx]
        while path[-1] != from_idx:
            path.append(path_prev[path[-1]])

        return list(reversed(path))

    def to_nx_graph(self):
        import networkx as nx
        graph = nx.DiGraph()
        for i in range(len(self.landmarks)):
            graph.add_node(i)
        for u, edges in enumerate(self.adjacency):
            for v in edges:
                graph.add_edge(u, v)
        return graph
