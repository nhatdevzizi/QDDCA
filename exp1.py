from topo import Network
import random
from qns.simulator.simulator import Simulator
import qns.utils.log as log
import os
import sys
from collections import Counter
from util import MODES, coefficient_of_variation
import numpy as np

# Every point plotted from this CSV is the mean over these paired scenarios.
SEEDS = (101, 202, 303)

os.makedirs("output", exist_ok=True)
f = open("output/exp2-7.1.csv","w", buffering=1)

# Fixed grid shared by every experiment: n=50, M=10, memorySize=20, reqs=5.
# Only the sending window w is swept here.
for seed in SEEDS:
    random.seed(seed)
    randomstate = random.getstate()  # one topology and request set per seed
    for m in [10]:
        for mode, reroute, predictive, utility in MODES:
            for w in range(1,31):
                random.setstate(randomstate)

                s = Simulator(0, 10, 1000)
                log.install(s)
                net = Network(n=50, p = 0.1, reqs = 5, memorySize=10, windowSize = w, queryTime= 0.5/m, send_max_try= m, rate = 1000, delay = 0.001, allow_reroute=reroute, predictive=predictive, utility=utility)

                net.install(s)
                s.run()

                ans_list = []
                drop_list = []
                for s in net.s:
                    c = Counter([tuple(x.route) for x in s.sendedList])
                    ans_list.append(len(s.sendedList))
                    drop_list.append(len(s.dropList))

                cv = coefficient_of_variation(ans_list)
                f.write(f"{seed},{w},{m},{mode},{sum(ans_list)},{sum(drop_list)},{np.std(ans_list)},{cv:.4f},{ans_list}\n")

                print(seed, mode, w, m, sum(ans_list), sep=",")
f.close()
