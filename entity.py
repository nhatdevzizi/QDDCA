from functools import singledispatch
from typing import List, Optional, Tuple, Any
from qns.simulator.simulator import Simulator
from qns.simulator.event import Event
from qns.entity.node.node import QNode
from qns.entity.qchannel.qchannel import QuantumChannel
from qns.simulator.ts import Time
from qubit import Qubit
import qns.utils.log as log
import random
import util

# Processing step interval
handle_step_time = 0.01000


class QNodeHandleEvent(Event):
    """Generic event that triggers a node's processing logic."""

    def __init__(self, refresh: bool, t: Optional[Time] = None, name: Optional[str] = None, by: Optional[Any] = None):
        super().__init__(t=t, name=name, by=by)
        self.refresh = refresh  # Whether to refresh the sending window

    def invoke(self) -> None:
        """Call the node's handle method when the event fires."""
        if self.by and hasattr(self.by, 'handle'):
            self.by.handle(self.by.simulator, None, self.by, self)


class QNodeQueryBeforeEvent(Event):
    """Event that queries routing and resources before sending a qubit."""

    def __init__(self, qubit: Qubit, t: Optional[Time] = None, name: Optional[str] = None, by: Optional[Any] = None):
        super().__init__(t=t, name=name, by=by)
        self.qubit = qubit  # Qubit to send

    def invoke(self) -> None:
        """Trigger the node's before_send_attempt logic."""
        if self.by and hasattr(self.by, 'handle'):
            self.by.handle(self.by.simulator, self.qubit, None, self)


class QNodeQueryAfterEvent(Event):
    """Event processed after a qubit is sent successfully to the next hop."""

    def __init__(self, qubit: Qubit, currhop, nexthop, t: Optional[Time] = None, name: Optional[str] = None,
                 by: Optional[Any] = None):
        super().__init__(t=t, name=name, by=by)
        self.qubit = qubit  # Qubit in transit
        self.currhop = currhop  # Current node
        self.nexthop = nexthop  # Next-hop node

    def invoke(self) -> None:
        """Trigger the node's after_send_attempt logic."""
        if self.by and hasattr(self.by, 'handle'):
            self.by.handle(self.by.simulator, self.qubit, None, self)


class QNNode(QNode):
    """Quantum network node supporting qubit routing and transmission management."""

    def __init__(self, name: str, isSender=False, dest=None, memorySize=10, windowSize=10, queryTime=0.02,
                 start_time: float = 0, end_time: float = None, send_max_try=100, allow_reroute=False,
                 random_memory=False, predictive=False, utility="ratio", hop_penalty=0.1, blend=0.7,
                 tau=None):
        self.name = name

        # Sender configuration
        self.isSender = isSender  # Whether this is a sender node
        self.dest = dest  # Destination node
        self.send_max_try = send_max_try  # Maximum number of attempts
        self.queryTime = queryTime  # Query interval
        self.start_time = start_time  # Start time
        self.end_time = end_time  # End time

        # Memory management
        self.memorySize = memorySize  # Memory capacity
        self.currentSize = 0  # Current usage
        self.memory = []  # Stored qubits
        self.random_memory = random_memory  # Whether to use a random memory size

        # Window management
        self.windowSize = windowSize  # Sending window size
        self.minhop = 0  # Minimum hop count
        self.currentWindowsSize = 0  # Current window size
        self.sendingList = []  # Qubits being sent
        self.sendedList = []  # Sent qubits
        self.dropList = []  # Dropped qubits
        self.allow_reroute = allow_reroute  # Whether rerouting is allowed

        # Query statistics
        self.query_ans = []  # Query result history
        self.query_ans_max_len = 10  # Maximum history length
        self.query_delta = 0.001  # Random query delay

        # Network state
        self.query_list = {}  # Query records for each node
        self.net = None  # Owning network

        # Predictive congestion avoidance
        self.predictive = predictive  # Predict P_success instead of reacting to failures
        self.utility = utility  # "ratio" -> P/E[hops], "linear" -> P - hop_penalty*E[hops]
        self.hop_penalty = hop_penalty  # The lambda of the linear utility
        self.blend = blend  # Weight of the prediction vs. the observed history
        # Same 10-sample horizon as query_ans_max_len, expressed as a time constant
        self.tau = tau if tau is not None else 10 * queryTime
        self._lam = 0.0  # lambda_v(t): arrivals into memory per second
        self._mu = 0.0  # departures from memory per second
        self._last_t = 0.0  # Timestamp of the last rate update

        if self.random_memory:
            self.memorySize = random.randint(1, self.memorySize)

    def set_net(self, net):
        """Set the network topology that owns this node."""
        self.net = net

    def install(self, simulator: Simulator):
        """Install the node in the simulator and schedule its first processing event."""
        self.simulator = simulator
        self.query_time = simulator.time(sec=self.queryTime)
        self.start_time_obj = simulator.time(sec=self.start_time)
        if self.end_time is not None:
            self.end_time_obj = simulator.time(sec=self.end_time)
        else:
            self.end_time_obj = simulator.te

        self.step_time = simulator.time(sec=handle_step_time)

        # Initialize query records for all nodes
        for n in self.net.nodes:
            self.query_list[n] = []

        # Add the startup event
        event = QNodeHandleEvent(refresh=True, t=self.start_time_obj, name=f"StartEvent_{self.name}", by=self)
        simulator.add_event(event)

    def handle(self, simulator: Simulator, msg: object, source=None, event: Event = None):
        """Dispatch an event to the appropriate processing logic based on its type."""
        if not self.isSender:
            return
        if isinstance(event, QNodeHandleEvent):
            if self.simulator.current_time > self.end_time_obj:
                return
            refresh = event.refresh
            self.send(refresh)
        elif isinstance(event, QNodeQueryAfterEvent):
            qubit = event.qubit
            nexthop = event.nexthop
            currhop = event.currhop
            self.after_send_attempt(qubit, currhop, nexthop)
        elif isinstance(event, QNodeQueryBeforeEvent):
            qubit = event.qubit
            self.before_send_attempt(qubit)

    def send(self, refresh=False):
        """Create and send a new qubit according to the window size."""
        if self.minhop == 0:
            self.minhop = self.net.route_table[self][self.dest][0]

        # Create a new qubit if the sending list is not full
        if len(self.sendingList) < self.windowSize * self.minhop:
            q = Qubit(src=self, dest=self.dest,
                      max_try_count=self.send_max_try, birthday=self.simulator.current_time)
            self.sendingList.append(q)
            log.debug(f"qubit {q} start to transmit from {self} to {self.dest}")

            # Trigger a pre-query event after a random delay
            rt_delay = random.random() * self.query_delta
            rt = self.simulator.time(sec=rt_delay)
            event = QNodeQueryBeforeEvent(
                qubit=q,
                t=self.simulator.current_time + rt,
                name=f"QueryBefore_{q.name}",
                by=self
            )
            self.simulator.add_event(event)

        # Schedule another send if space remains
        if len(self.sendingList) < self.windowSize * self.minhop:
            event = QNodeHandleEvent(
                refresh=True,
                t=self.simulator.current_time + self.step_time,
                name=f"NextSend_{self.name}",
                by=self
            )
            self.simulator.add_event(event)

    def before_send_attempt(self, qubit):
        """Check routing and resource availability before deciding whether to send."""
        retq = qubit.attempt()  # Check the qubit's state

        # Get routing information
        currhop, nexthop, nextlink = self.route(qubit)

        # Check next-hop node and link availability
        if nexthop is None or nextlink is None:
            retn = False
            retl = False
            retq = False
        else:
            retn = nexthop.query(self.simulator)  # Check node memory
            retl, _ = nextlink.query(self.simulator)  # Check link bandwidth

        # Send the qubit if all conditions are satisfied
        if retq and retn and retl:
            self.update2(nexthop, True)  # Update node query statistics
            nexthop.use(qubit)  # Reserve memory on the next-hop node
            retll, st = nextlink.use(self.simulator)  # Reserve link resources
            assert (retll == True)
            log.debug(f"qubit {qubit.name} send from {currhop} to {nexthop} at {st + self.query_time}")

            # Schedule a post-query event
            event = QNodeQueryAfterEvent(
                qubit=qubit,
                currhop=currhop,
                nexthop=nexthop,
                t=st + self.query_time,
                name=f"QueryAfter_{qubit.name}",
                by=self
            )
            self.simulator.add_event(event)
        else:
            # Handle a failed send
            if nexthop is not None:
                self.update2(nexthop, False)  # Update failure statistics

            if retq == False:
                # Drop the qubit after it exceeds the maximum attempt count
                self.sendingList.remove(qubit)
                self.dropList.append(qubit)
                if self != currhop:
                    currhop.release(qubit)
                log.debug(f"qubit {qubit.name} drop on {currhop} nexthop {nexthop} {retn} nextlink {nextlink} {retl}")

                # Trigger a processing event
                event = QNodeHandleEvent(
                    refresh=False,
                    t=self.simulator.current_time + self.query_time,
                    name=f"HandleAfterDrop_{qubit.name}",
                    by=self
                )
                self.simulator.add_event(event)
            else:
                # Resources are insufficient; retry later
                log.debug(f"qubit {qubit.name} retry on {currhop} nexthop {nexthop} {retn} nextlink {nextlink} {retl}")
                rt_delay = random.random() * self.query_delta
                rt = self.simulator.time(sec=rt_delay)
                event = QNodeQueryBeforeEvent(
                    qubit=qubit,
                    t=self.simulator.current_time + self.query_time + rt,
                    name=f"RetryQuery_{qubit.name}",
                    by=self
                )
                self.simulator.add_event(event)

    def route(self, qubit):
        """Select the next-hop node and link according to the routing strategy."""
        currhop = qubit.curr
        rt = self.net.query_route(currhop, self.dest)

        # Use the shortest path if rerouting is disabled
        if not self.allow_reroute:
            nexthop: QNode = rt[0][0]
            nextlink: Link = rt[0][1]
            return currhop, nexthop, nextlink

        # Rerouting logic: select the best path by probability and path quality
        m = qubit.try_count
        M = qubit.max_try_count
        if m > M:
            return currhop, None, None
        metric_drop = self.net.route_table[self.dest][self][0] * 2

        nexthop: QNode = rt[0][0]
        nextlink: Link = rt[0][1]
        INF = 999999

        min_mt = INF
        min_y = INF
        max_u = -INF
        best_y = INF  # Expected cost of the currently selected neighbor

        # Evaluate all possible neighboring nodes
        for neigh in rt:
            nv = neigh[0]
            nl = neigh[1]
            mt = neigh[2]

            Lmax = max(self.net.route_table[self.dest][self][0], 5)
            pce = 1 - self.net.route_table[self.dest][self][0] / Lmax

            # Probabilistic path exploration
            if random.random() < pce:
                lmt = min_mt + 1
            else:
                lmt = min_mt

            if mt > lmt:
                continue
            if len(qubit.route) + mt > Lmax:
                continue

            # Estimate the neighbor's success probability
            p = self.stat2(nv)  # Recent traffic seen by this sender
            if self.predictive:
                # Lead time until the qubit would actually land on nv
                lead = nl.delay + self.queryTime
                p_pred = nv.predict_success(lead) * nl.predict_free(self.simulator, lead)
                # ponytail: fixed blend, make it adaptive only if tuning shows it matters
                p = self.blend * p_pred + (1 - self.blend) * p

            # Calculate the path evaluation metric
            y = (1 - (1 - p) ** (M - m)) * mt + (1 - p) ** (M - m) * metric_drop

            if self.predictive:
                u = util.utility(p, mt, self.utility, self.hop_penalty)
                better = u > max_u
            else:
                u = max_u
                better = y < min_y

            if better:
                nexthop = nv
                nextlink = nl
                min_mt = mt
                min_y = min(min_y, y)
                max_u = u
                best_y = y

        if best_y > metric_drop:
            return currhop, None, None

        if nexthop in qubit.route:
            return currhop, None, None

        return currhop, nexthop, nextlink

    def after_send_attempt(self, qubit: Qubit, currhop, nexthop):
        """Process a qubit after it successfully reaches the next hop."""
        log.debug(f"qubit {qubit.name} ({qubit.src}->{qubit.dest}) recved from {currhop} to {nexthop}")

        # Release resources on the current node
        if self != currhop:
            currhop.release(qubit)

        qubit.send(nexthop)  # Update the qubit's location

        # Complete transmission if the destination has been reached
        if self.dest == nexthop:
            self.sendingList.remove(qubit)
            self.sendedList.append(qubit)
            nexthop.release(qubit)
            log.debug(f"qubit {qubit.name} ({qubit.src}->{qubit.dest}) arrived")

            event = QNodeHandleEvent(
                refresh=False,
                t=self.simulator.current_time,
                name=f"HandleAfterArrival_{qubit.name}",
                by=self
            )
            self.simulator.add_event(event)
        else:
            # Continue transmission to the next hop
            rt_delay = random.random() * self.query_delta
            rt = self.simulator.time(sec=rt_delay)
            event = QNodeQueryBeforeEvent(
                qubit=qubit,
                t=self.simulator.current_time + rt,
                name=f"QueryBeforeNextHop_{qubit.name}",
                by=self
            )
            self.simulator.add_event(event)

    def query(self, simulator: Simulator) -> Tuple[bool, int]:
        """Check whether the node has available memory."""
        ret = self.currentSize < self.memorySize
        return ret

    def use(self, qubit):
        """Reserve node memory by storing the qubit."""
        self.currentSize += 1
        self.memory.append(qubit)
        self._rates()
        self._lam += 1.0 / self.tau  # One arrival, weighted so _lam reads as events/sec

    def release(self, qubit):
        """Release node memory by removing the qubit."""
        self.currentSize -= 1
        self.memory.remove(qubit)
        self._rates()
        self._mu += 1.0 / self.tau

    def _rates(self):
        """Age the arrival/departure rate estimates up to the current time."""
        now = util.sec(self.simulator.current_time)
        dt = now - self._last_t
        self._lam = util.decay(self._lam, dt, self.tau)
        self._mu = util.decay(self._mu, dt, self.tau)
        self._last_t = now

    def predict_success(self, delta):
        """P_success(v, t+delta) from M_v(t), Q_v(t) and lambda_v(t)."""
        self._rates()
        return util.p_success(self.currentSize, self.memorySize, self._lam, self._mu, delta)

    def stat(self):
        """Calculate the historical query success rate."""
        delta = 0.5
        nt = 0
        na = len(self.query_ans)
        for ans in self.query_ans:
            if ans:
                nt += 1
        return (nt + delta) / (na + delta)

    def update(self, ret):
        """Update the query result history."""
        self.query_ans.append(ret)
        if len(self.query_ans) > self.query_ans_max_len:
            del self.query_ans[0]

    def stat2(self, node):
        """Calculate the query success rate for a specific node."""
        delta = 0.5
        nt = 0
        na = len(self.query_list[node])
        for ans in self.query_list[node]:
            if ans:
                nt += 1
        return (nt + delta) / (na + delta)

    def update2(self, node, result):
        """Update query records for a specific node."""
        self.query_list[node].append(result)
        if len(self.query_list[node]) > self.query_ans_max_len:
            del self.query_list[node][0]

    def __repr__(self):
        """Return the node name as its string representation."""
        return self.name


class Link(QuantumChannel):
    """Manage connectivity and bandwidth resources between two quantum nodes."""

    def __init__(self, name: str, nodes: List[QNode], metric=1, rate=1, delay=0.2, buffer=None):
        self.name = name  # Link name
        self.nodes = nodes  # Connected nodes
        self.rate = rate  # Transmission rate
        self.delay = delay  # Transmission delay
        self.buffer = buffer  # Buffer size
        self.metric = metric  # Link metric

        self.current_send_time = None  # Current send time

    def install(self, simulator: Simulator):
        """Install the link in the simulator and initialize timing parameters."""
        self.current_send_time = simulator.time(sec=simulator.ts.sec)
        send_interval_sec = 1.0 / self.rate
        self.step_send_time = simulator.time(sec=send_interval_sec)  # Send interval
        self.delay_time = simulator.time(sec=self.delay)  # Transmission delay

    def query(self, simulator: Simulator) -> Tuple[bool, Optional[int]]:
        """Check whether the link can be used immediately."""
        if self.current_send_time < simulator.current_time:
            send_time_slice = self.current_send_time + self.delay_time
            return True, send_time_slice

        if self.buffer is None:
            send_time_slice = self.current_send_time + self.delay_time
            return True, send_time_slice

        # Check the buffer limit
        buffer_time_slots = self.step_send_time.time_slot * self.buffer
        buffer_time = simulator.time(time_slot=buffer_time_slots)

        if self.current_send_time > simulator.current_time + buffer_time:
            return False, None
        else:
            send_time_slice = self.current_send_time + self.delay_time
            return True, send_time_slice

    def predict_free(self, simulator: Simulator, delta) -> float:
        """q_v(t): probability the link is not blocked at t+delta, from its booking backlog."""
        backlog = util.sec(self.current_send_time) - util.sec(simulator.current_time)
        horizon = delta + (self.buffer or 1) / self.rate
        return min(max(1.0 - max(backlog, 0.0) / horizon, 0.0), 1.0)

    def use(self, simulator: Simulator):
        """Reserve link resources and return the allocated send timeslot."""
        if self.current_send_time < simulator.current_time:
            send_time_slice = simulator.current_time + self.delay_time
            self.current_send_time = simulator.current_time + self.step_send_time
            return True, send_time_slice

        if self.buffer is None:
            send_time_slice = self.current_send_time + self.delay_time
            self.current_send_time += self.step_send_time
            return True, send_time_slice

        # Check the buffer limit
        buffer_time_slots = self.step_send_time.time_slot * self.buffer
        buffer_time = simulator.time(time_slot=buffer_time_slots)

        if self.current_send_time > simulator.current_time + buffer_time:
            return False, None
        else:
            send_time_slice = self.current_send_time + self.delay_time
            self.current_send_time += self.step_send_time
            return True, send_time_slice

    def __repr__(self):
        """Return the link name as its string representation."""
        return self.name
