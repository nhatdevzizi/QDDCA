# Code Structure Pattern: `exp1.py` and `exp2.py`

## 1. Overall structure

Both experiments use the same pipeline:

```text
Configure reproducible randomness
        |
        v
Create output directory and CSV file
        |
        v
Sweep experiment parameters
        |
        v
Reset random state for a fair comparison
        |
        v
Create Simulator and Network
        |
        v
Network.install()
  |- build topology
  |- calculate routes
  |- create requests
  `- install links and nodes
        |
        v
Simulator.run()
        |
        v
Collect sent/dropped qubits from every sender
        |
        v
Calculate metrics, write one CSV row, print progress
        |
        v
Close the CSV file
```

The files differ mainly in the parameters they sweep and the metrics they
write. The simulation engine itself is shared through `topo.py`, `entity.py`,
and `qubit.py`.

| Concern | `exp1.py` | `exp2.py` |
|---|---|---|
| Random seed | `120` | `2` |
| Request count | `5` | `1` |
| Memory size | `10` | `20` |
| Outer sweep | max attempts `m = [1, 5, 10]` | window size `w = [10, 20, 30]` |
| Middle sweep | rerouting off/on | rerouting off/on |
| Inner sweep | window size `w = 1..30` | max attempts `m = 1..10` |
| Query interval | `0.5 / m` | `0.5 / m` |
| Random memory | default (`False`) | explicitly `False` |
| Main results | sent, dropped, standard deviation, CV, per-sender sent values | sent, dropped, route count, route frequencies |

## 2. Current `exp1.py` pattern

```text
module setup
  |- seed random generator with 120
  |- save initial random state
  |- create output/exp1/
  `- open CSV file

coefficient_of_variation(data, ddof=0)
  |- calculate mean
  |- calculate standard deviation
  |- return infinity when mean is zero
  `- otherwise return standard deviation / mean

experiment sweep
  for m in [1, 5, 10]
    for reroute in [False, True]
      for w in 1..30
        |- restore initial random state
        |- create a 10-second simulator
        |- create a 50-node, 5-request network
        |- install and run the simulation
        |- collect sent and dropped counts per sender
        |- calculate total sent, total dropped, standard deviation, and CV
        |- write the CSV row
        `- print progress

close output file
```

### `coefficient_of_variation(data, ddof=0)`

Purpose: measure how uneven the successful-send counts are between sender
nodes.

```python
mean = np.mean(data)
std = np.std(data, ddof=ddof)
cv = inf if mean == 0 else std / mean
```

- `data`: per-sender successful-send counts (`ans_list`).
- `ddof=0`: population standard deviation; use `1` for sample standard
  deviation.
- Return: a ratio, not a percentage. For example, `0.25` means 25% relative
  variation.

### `exp1.py` output row

```text
window_size,max_attempts,reroute,total_sent,total_dropped,std_sent,cv,sent_per_sender
```

## 3. Current `exp2.py` pattern

`exp2.py` has no user-defined functions; all behavior runs at module level.

```text
module setup
  |- seed random generator with 2
  |- save initial random state
  |- create output/exp2/
  `- open CSV file

experiment sweep
  for w in [10, 20, 30]
    for reroute in [False, True]
      for m in 1..10
        |- restore initial random state
        |- create a 10-second simulator
        |- create a 50-node, 1-request network
        |- install and run the simulation
        |- collect sent and dropped counts
        |- count successful qubits by complete route
        |- write totals and route frequencies to the CSV row
        `- print progress

close output file
```

### Route counter

```python
c = Counter(tuple(qubit.route) for qubit in sender.sendedList)
```

- Key: one complete route represented as a tuple of nodes.
- Value: number of successfully delivered qubits that used that route.
- `len(c)`: number of distinct successful routes.

Because the experiment uses one request, the final `c` represents that one
sender. If `reqs` is later increased, the current code overwrites `c` for each
sender and writes only the last sender's route counter.

### `exp2.py` output row

```text
window_size,max_attempts,reroute,total_sent,total_dropped,distinct_routes,route_frequencies
```

## 4. Function-level simulation flow shared by both experiments

```text
Network.install(simulator)
  |- Network.build()
  |    |- construct QNNode objects
  |    |- randomly construct Link objects
  |    `- call Network.route() until the graph is connected
  |- Network.get_requests()
  |    `- choose source/destination pairs and mark sender nodes
  |- Link.install() for every link
  `- QNNode.install() for every node
       `- schedule the first QNodeHandleEvent

Simulator.run()
  `- event loop
       |- QNodeHandleEvent -> QNNode.handle() -> QNNode.send()
       |- QNodeQueryBeforeEvent -> QNNode.before_send_attempt()
       |    |- Qubit.attempt()
       |    |- QNNode.route()
       |    |- QNNode.query() and Link.query()
       |    `- reserve resources, retry, or drop
       `- QNodeQueryAfterEvent -> QNNode.after_send_attempt()
            |- release previous-hop memory
            |- Qubit.send()
            `- finish delivery or schedule the next hop
```

### Network functions

- `Network.__init__`: stores topology, request, node, routing, and link
  parameters.
- `Network.install`: builds the complete simulation model and installs it into
  the simulator.
- `Network.build`: creates nodes and probabilistic links, then adds links until
  all node pairs are reachable.
- `Network.route`: builds the all-pairs shortest-path table with repeated
  Dijkstra searches.
- `Network.query_route`: returns a source's candidate next hops sorted by total
  path metric.
- `Network.get_requests`: chooses unique source nodes and destinations and
  configures each sender.
- `Network.get_node`: looks up a node by name.

### Node and event functions

- Event `invoke` methods delegate scheduled work to `QNNode.handle`.
- `QNNode.install`: initializes simulation times and schedules startup.
- `QNNode.handle`: dispatches each event type to its matching node method.
- `QNNode.send`: fills the sending window with new qubits.
- `QNNode.before_send_attempt`: checks retry limit, routing, node memory, and
  link availability; it then sends, retries, or drops the qubit.
- `QNNode.route`: uses the shortest path when rerouting is disabled; otherwise
  scores eligible neighbors using path length and estimated congestion.
- `QNNode.after_send_attempt`: records a hop, frees resources, and either marks
  delivery complete or schedules another hop.
- `QNNode.query`, `use`, and `release`: manage node memory capacity.
- `QNNode.historical_stat2`, `memory_utilization`, `congestion_state`, and
  `stat2`: estimate a neighbor's acceptance probability for rerouting.
- `QNNode.update2`: records the latest success/failure observations per
  neighbor.

### Link and qubit functions

- `Link.install`: initializes transmission timing and rate limits.
- `Link.query`: checks whether a transmission fits within the link buffer.
- `Link.use`: reserves a transmission time slot.
- `Qubit.attempt`: increments the current-hop attempt counter and rejects an
  attempt above `max_try_count`.
- `Qubit.send`: records the next hop and resets the attempt counter.

## 5. Recommended reusable experiment pattern

The current scripts duplicate setup, execution, collection, and output logic.
A clearer structure is:

```python
def build_cases():
    """Yield every (window_size, max_attempts, reroute) case."""


def run_case(case, initial_random_state):
    """Build and run one reproducible simulation case."""


def collect_metrics(network):
    """Convert sender state into experiment-specific metrics."""


def write_result(file, case, metrics):
    """Write exactly one result row."""


def main():
    """Open output safely and execute the complete parameter sweep."""


if __name__ == "__main__":
    main()
```

Recommended call pattern:

```text
main
  |- capture reproducible random state
  |- open CSV with a context manager
  `- for case in build_cases()
       |- run_case()
       |- collect_metrics()
       `- write_result()
```

This separation makes each case testable, prevents an experiment from running
merely because its module was imported, and keeps the differences between
`exp1` and `exp2` inside `build_cases` and `collect_metrics`.

## 6. Current naming details to verify

- `exp1.py` writes to `output/exp1/exp2-7.1.csv`.
- `exp2.py` writes to `output/exp2/exp1-4.csv`.

The directory names match the scripts, but the CSV stems appear swapped. This
document records the code as it currently behaves; renaming those files would
be a separate implementation change.
