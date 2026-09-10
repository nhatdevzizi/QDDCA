from topo import Network
import random
from qns.simulator.simulator import Simulator
import qns.utils.log as log
import os
import sys
from collections import Counter
from util import MODES
# import numpy as np

# log.set_debug(True)
# Every point plotted from this CSV is the mean over these paired scenarios.
SEEDS = (101, 202, 303)

os.makedirs("output", exist_ok=True)
f = open("output/exp1-4.csv","w", buffering=1)

# Fixed grid shared by every experiment: n=50, M=10, memorySize=20, reqs=5.
# Only the attempt budget M is swept here; w stays at the 12 used by the paper.
for seed in SEEDS:
    random.seed(seed)
    randomstate = random.getstate()  # one topology and request set per seed
    for w in [12]:
        for mode, reroute, predictive, utility in MODES:
            for m in range(1, 11):
                random.setstate(randomstate)

                s = Simulator(0, 10, 1000)
                log.install(s)
                net = Network(n=50, p = 0.1, reqs = 5, memorySize=10, windowSize = w, queryTime= 0.5/m, send_max_try= m, rate = 1000, delay = 0.001, allow_reroute=reroute, random_memory=False, predictive=predictive, utility=utility)

                net.install(s)
                s.run()

                ans_list = []
                drop_list = []
                for s in net.s:
                    # c ends up holding the last request's routes only, as in QDDCA-main.
                    c = Counter([tuple(x.route) for x in s.sendedList])
                    ans_list.append(len(s.sendedList))
                    drop_list.append(len(s.dropList))

                f.write(f"{seed},{w},{m},{mode},{sum(ans_list)},{sum(drop_list)},{len(c)},\"{c}\"\n")

                print(seed, mode, w, m, sum(ans_list), sep=",")
f.close()
