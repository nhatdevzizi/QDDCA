from topo import Network
import random
from qns.simulator.simulator import Simulator
import qns.utils.log as log
import os
from collections import Counter
from util import MODES
from multiprocessing import Pool, cpu_count

# Every point plotted from this CSV is the mean over these paired scenarios.
SEEDS = list(range(101, 116))

W_VALUES = [12]
M_RANGE = range(1, 11)


def run_seed(seed):
    """Run all (w, mode, m) combinations for one seed; return list of CSV lines."""
    rows = []
    random.seed(seed)
    randomstate = random.getstate()  # one topology and request set per seed

    for w in W_VALUES:
        for mode, reroute, predictive, utility in MODES:
            for m in M_RANGE:
                random.setstate(randomstate)

                s = Simulator(0, 10, 1000)
                log.install(s)
                net = Network(n=50, p = 0.1, reqs = 5, memorySize=10, windowSize = w, queryTime= 0.5/m, send_max_try= m, rate = 1000, delay = 0.001, allow_reroute=reroute, random_memory=False, predictive=predictive, utility=utility)

                net.install(s)
                s.run()

                ans_list = []
                drop_list = []
                for s in net.s:
                    c = Counter([tuple(x.route) for x in s.sendedList])
                    ans_list.append(len(s.sendedList))
                    drop_list.append(len(s.dropList))

                rows.append(f"{seed},{w},{m},{mode},{sum(ans_list)},{sum(drop_list)},{len(c)},\"{c}\"\n")
                print(f"seed={seed} w={w} m={m:2d} mode={mode} ans={sum(ans_list)}", flush=True)

    return rows


if __name__ == "__main__":
    os.makedirs("result/15-seed", exist_ok=True)

    workers = min(len(SEEDS), cpu_count())

    # pool.map preserves seed order: results[i] corresponds to SEEDS[i]
    with Pool(processes=workers) as pool:
        results = pool.map(run_seed, SEEDS)

    with open("result/15-seed/exp1-4.csv", "w") as f:
        for seed_rows in results:
            f.writelines(seed_rows)
