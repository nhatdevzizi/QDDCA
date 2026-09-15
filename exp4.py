"""Sweep the topology size with the offered load scaled to match it.

Requests grow as n // REQUEST_DENSITY, so every network carries the same load
per node and what the sweep varies is the size of the network -- longer paths,
more competing flows -- rather than the pressure applied to a fixed one.

Note when reading the results: p stays at 0.1 as in exp1/exp2, so a larger n is
also a denser graph (n=200 gives roughly 20 neighbours per node).  "Bigger" and
"better connected" move together here.

Speed: each seed is fully independent, so all seeds run in parallel via
multiprocessing. The `if __name__ == "__main__"` guard is required on Windows
(spawn start method).
"""

from topo import Network
import random
from qns.simulator.simulator import Simulator
import qns.utils.log as log
import os
from util import MODES, coefficient_of_variation
import numpy as np
from multiprocessing import Pool, cpu_count

SEEDS = list(range(101, 116))
NODE_COUNTS = (50, 100, 150, 200)
REQUEST_DENSITY = 10  # reqs = n // REQUEST_DENSITY, i.e. one flow per 10 nodes


def run_seed(seed):
    """Run all (n, mode) combinations for one seed; return list of CSV lines."""
    rows = []
    random.seed(seed)
    randomstate = random.getstate()  # one topology and request set per seed

    for n in NODE_COUNTS:
        reqs = n // REQUEST_DENSITY
        for mode, reroute, predictive, utility in MODES:
            random.setstate(randomstate)

            s = Simulator(0, 10, 1000)
            log.install(s)
            net = Network(n=n, p = 0.1, reqs = reqs, memorySize=10, windowSize = 12, queryTime= 0.05, send_max_try= 10, rate = 1000, delay = 0.001, allow_reroute=reroute, random_memory=False, predictive=predictive, utility=utility)

            net.install(s)
            s.run()

            ans_list, drop_list = [], []
            for s in net.s:
                ans_list.append(len(s.sendedList))
                drop_list.append(len(s.dropList))

            cv = coefficient_of_variation(ans_list)
            rows.append(
                f"{seed},{n},{reqs},30,10,{mode},"
                f"{sum(ans_list)},{sum(drop_list)},"
                f"{np.std(ans_list)},{cv:.4f},{ans_list}\n"
            )
            print(f"seed={seed} n={n:3d} ans={sum(ans_list)}", flush=True)

    return rows


if __name__ == "__main__":
    os.makedirs("result", exist_ok=True)

    workers = min(len(SEEDS), cpu_count())
    print(f"Running {len(SEEDS)} seeds across {workers} parallel workers ...")

    # pool.map preserves seed order: results[i] corresponds to SEEDS[i]
    with Pool(processes=workers) as pool:
        results = pool.map(run_seed, SEEDS)

    with open("result/15-seed/exp4_scale.csv", "w") as f:
        for seed_rows in results:
            f.writelines(seed_rows)

