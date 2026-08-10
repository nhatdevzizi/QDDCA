from topo import Network
import random
from qns.simulator.simulator import Simulator
import qns.utils.log as log
import os
import sys
from collections import Counter
from util import MODES
import numpy as np

# random.seed(0)
# log.set_debug(True)
random.seed(120)
randomstate = random.getstate()

os.makedirs("output", exist_ok=True)
f = open("output/exp2-7.1.csv","w", buffering=1)





def coefficient_of_variation(data, ddof=0):
    """
    Calculate the coefficient of variation.

    Parameters:
    data: Data list or array
    ddof: Degrees-of-freedom adjustment (0=population, 1=sample)

    Returns:
    cv: Coefficient of variation (percentage)
    """
    mean_val = np.mean(data)
    std_val = np.std(data, ddof=ddof)

    # Avoid division by zero
    if mean_val == 0:
        return float('inf')  # Return infinity

    cv = std_val / mean_val
    return cv

for m in [1, 5, 10]:
    for mode, reroute, predictive in MODES:
        for w in range(1,31):
            # random.seed(1)
            random.setstate(randomstate)

            s = Simulator(0, 10, 1000)
            log.install(s)
            net = Network(n=50, p = 0.1, reqs = 5, memorySize=10, windowSize = w, queryTime= 0.5/m, send_max_try= m, rate = 1000, delay = 0.001, allow_reroute=reroute, predictive=predictive)
            # net = Network(n=50, p = 0.05, reqs = 5, memorySize=10, windowSize = w, queryTime= 0.05, send_max_try= m, rate = 1000, delay = 0.001, allow_reroute=reroute)

            net.install(s)
            s.run()

            ans_list = []
            drop_list = []
            # print(net.s, net.d)
            for s in net.s:
                c = Counter([tuple(x.route) for x in s.sendedList])
                # print(f"result on {s}->{s.dest}: sended {len(s.sendedList)} drop {len(s.dropList)} sending {len(s.sendingList)}", end=" ")
                # print(c)
                ans_list.append(len(s.sendedList))
                drop_list.append(len(s.dropList))

            cv = coefficient_of_variation(ans_list)
            f.write(f"{w},{m},{mode},{sum(ans_list)},{sum(drop_list)},{np.std(ans_list)},{cv:.4f},{ans_list}\n")

            print(mode, w, m , sum(ans_list) , sep=",")
f.close()
