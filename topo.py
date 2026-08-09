from qns.entity.entity import Entity
from qns.simulator.simulator import Simulator
from entity import QNNode, Link
import random

INF = 9999999  # Infinity constant used in route calculations


class Network(Entity):
    """Manage the quantum network topology, routing table, and communication requests."""

    def __init__(self, n=10, p=0.5, reqs=3, memorySize=30, windowSize=100, queryTime=0.02, send_max_try=10,
                 allow_reroute=False, rate=3, delay=0.2, buffer=1, random_memory=False,
                 congestion_history_weight=0.5):
        if not 0.0 <= congestion_history_weight <= 1.0:
            raise ValueError("congestion_history_weight must be between 0 and 1")

        # Basic network attributes
        self.nodes = []  # Node list
        self.links = {}  # Link relationships represented as an adjacency list
        self.route_table = {}  # Routing table

        # Topology parameters
        self.n = n  # Number of nodes
        self.p = p  # Link generation probability
        self.reqs = reqs  # Number of communication requests

        # Communication requests
        self.s = []  # Source node list
        self.d = []  # Destination node list

        # Node configuration parameters
        self.memorySize = memorySize
        self.random_memory = random_memory
        self.windowSize = windowSize
        self.queryTime = queryTime
        self.send_max_try = send_max_try
        self.allow_reroute = allow_reroute
        self.congestion_history_weight = congestion_history_weight

        # Link configuration parameters
        self.rate = rate
        self.buffer = buffer
        self.delay = delay

    def install(self, simulator: Simulator):
        """Install the network in the simulator and initialize all components."""
        self.build()  # Build the network topology
        self.get_requests()  # Generate communication requests

        # Install all links
        for rl in self.links.values():
            for _, l in rl:
                l.install(simulator)

        # Install all nodes
        for n in self.nodes:
            n.install(simulator)

    def build(self):
        """Build the topology, generate random links, and ensure network connectivity."""
        self.nodes = []
        self.links = {}
        self.route_table = {}

        # Create all nodes
        for i in range(self.n):
            n: QNNode = QNNode("n" + str(i + 1), memorySize=self.memorySize, windowSize=self.windowSize,
                               queryTime=self.queryTime, send_max_try=self.send_max_try,
                               allow_reroute=self.allow_reroute, random_memory=self.random_memory,
                               congestion_history_weight=self.congestion_history_weight)
            n.set_net(self)  # Set the network that owns the node
            self.nodes.append(n)
            self.links[n] = []  # Initialize the node's adjacency list

        # Generate links randomly
        for i1 in range(self.n):
            for i2 in range(i1 + 1, self.n):
                n1 = self.nodes[i1]
                n2 = self.nodes[i2]

                if random.random() < self.p:  # Create a link with probability p
                    l = Link(name=n1.name + "-" + n2.name,
                             nodes=[n1, n2], rate=self.rate, delay=self.delay, buffer=self.buffer)
                    self.links[n1].append((n2, l))
                    self.links[n2].append((n1, l))

        # Ensure connectivity by adding links until every node is reachable
        while True:
            self.route()  # Calculate the routing table
            tmplist = []
            flag = False

            # Check for unreachable node pairs
            for n1, vl in self.route_table.items():
                for n2, metric in vl.items():
                    if metric[0] == INF:  # An infinite distance means the node is unreachable
                        tmplist.append((n1, n2))
                        flag = True

            if flag:
                # Add a link between a randomly selected unreachable node pair
                idx = random.randint(0, len(tmplist) - 1)
                n1, n2 = tmplist[idx]
                l = Link(name=n1.name + "-" + n2.name,
                         nodes=[n1, n2], rate=self.rate, delay=self.delay, buffer=self.buffer)
                self.links[n1].append((n2, l))
                self.links[n2].append((n1, l))
            else:
                break  # All nodes are connected; exit the loop

    def route(self):
        """Calculate shortest paths between all node pairs using Dijkstra's algorithm."""
        for n in self.nodes:
            selected = []  # Selected nodes
            unselected = self.nodes.copy()  # Unselected nodes
            d = {}  # Distance map: node -> [shortest distance, path]

            # Initialize distances
            for nn in self.nodes:
                if nn == n:
                    d[nn] = [0, []]  # Distance to itself is zero
                else:
                    d[nn] = [INF, [nn]]  # Initial distance to other nodes is infinite

            # Main Dijkstra loop
            while len(unselected) != 0:
                # Select the node with the smallest current distance
                ms = unselected[0]
                mi = d[ms][0]
                for s in unselected:
                    if d[s][0] < mi:
                        ms = s
                        mi = d[s][0]

                # Mark the current node as processed
                selected.append(ms)
                unselected.remove(ms)

                # Update distances to neighboring nodes
                for (s, l) in self.links[ms]:
                    if s in unselected and d[s][0] > d[ms][0] + l.metric:
                        # A shorter path was found; update its distance and path
                        d[s] = [d[ms][0] + l.metric, [ms] + d[ms][1]]

            # Complete path information by adding the destination node
            for nn in self.nodes:
                d[nn][1] = [nn] + d[nn][1]

            self.route_table[n] = d  # Store routing information for this node

    def print_route_table(self):
        """Print the routing table as a matrix of distances between node pairs."""
        for i1 in range(self.n):
            for i2 in range(self.n):
                print(self.route_table[self.nodes[i1]][self.nodes[i2]][0], end="\t")
            print()

    def query_route(self, src, dest):
        """Return every possible next hop and metric from the source to the destination."""
        assert (src in self.nodes and dest in self.nodes)

        ret = []

        # Iterate over all neighbors of the source node
        for neighbour, l in self.links[src]:
            # Calculate the total metric to the destination through this neighbor
            total_metric = l.metric + self.route_table[dest][neighbour][0]
            ret.append((neighbour, l, total_metric))

        # Return results sorted by total metric
        return sorted(ret, key=lambda x: x[2])

    def get_requests(self):
        """Generate communication requests and configure their sender nodes."""
        self.s = []
        self.d = []

        # Reset the sending state of all nodes
        for n in self.nodes:
            n.isSender = False

        # Generate the requested number of communication requests
        for _ in range(self.reqs):
            # Select a unique source node
            s = None
            while s is None or s in self.s:
                si = random.randint(0, self.n - 1)
                s = self.nodes[si]
            self.s.append(s)

            # Select a destination node different from the source
            d = None
            while d is None or d == s:
                di = random.randint(0, self.n - 1)
                d = self.nodes[di]
            self.d.append(d)

        # Configure sender nodes
        for i in range(self.reqs):
            s = self.s[i]
            d = self.d[i]
            s.isSender = True
            s.dest = d

    def get_node(self, name):
        """Find a node by name."""
        for n in self.nodes:
            if n.name == name:
                return n
        return None
