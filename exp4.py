"""Sweep the topology size with the offered load scaled to match it.

Requests grow as n // REQUEST_DENSITY, so every network carries the same load
per node and what the sweep varies is the size of the network -- longer paths,
more competing flows -- rather than the pressure applied to a fixed one.

Note when reading the results: p stays at 0.1 as in exp1/exp2, so a larger n is
also a denser graph (n=200 gives roughly 20 neighbours per node).  "Bigger" and
"better connected" move together here.
"""

from topo import Network
import random
from qns.simulator.simulator import Simulator
import qns.utils.log as log
import os
from collections import Counter
from util import MODES, coefficient_of_variation
import numpy as np

# Every point plotted from this CSV is the mean over these paired scenarios.
SEEDS = (101, 202, 303)

NODE_COUNTS = (25, 50, 100, 150, 200)
REQUEST_DENSITY = 10  # reqs = n // REQUEST_DENSITY, i.e. one flow per 10 nodes

os.makedirs("output", exist_ok=True)
f = open("output/exp4_scale.csv", "w", buffering=1)

# Fixed grid shared by every experiment: M=10, memorySize=20, w=12.
# Only the node count -- and the request count tied to it -- is swept here.
for seed in SEEDS:
    random.seed(seed)
    randomstate = random.getstate()  # one topology and request set per seed
    for n in NODE_COUNTS:
        reqs = max(2, n // REQUEST_DENSITY)  # CV needs at least two requests
        for mode, reroute, predictive, utility in MODES:
            random.setstate(randomstate)

            s = Simulator(0, 10, 1000)
            log.install(s)
            net = Network(n=n, p = 0.1, reqs = reqs, memorySize=20, windowSize = 12, queryTime= 0.05, send_max_try= 10, rate = 1000, delay = 0.001, allow_reroute=reroute, random_memory=False, predictive=predictive, utility=utility)

            net.install(s)
            s.run()

            ans_list = []
            drop_list = []
            for s in net.s:
                c = Counter([tuple(x.route) for x in s.sendedList])
                ans_list.append(len(s.sendedList))
                drop_list.append(len(s.dropList))

            cv = coefficient_of_variation(ans_list)
            f.write(f"{seed},{n},{reqs},12,10,{mode},{sum(ans_list)},{sum(drop_list)},{np.std(ans_list)},{cv:.4f},{ans_list}\n")

            print(seed, mode, n, reqs, sum(ans_list), sep=",")
f.close()
