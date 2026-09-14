"""Sweep the prediction weight beta at the pilot operating point.

beta (`blend` in the code) decides how much of the per-neighbour success
estimate comes from the forecast and how much from the observed query history:
`p = beta * p_pred + (1 - beta) * stat2(v)` (entity.py:311).  The 0.7 used
everywhere else was picked by hand and never swept, so this file exists only to
answer "why 0.7?" with a measurement instead of an assertion.

The fixed grid below is exactly the pilot point behind the paper's headline
tables: n=50, memorySize=10, w=12, M=10, queryTime=0.05 s -- the same numbers
exp2.py runs at m=10, since it sets queryTime=0.5/m.  Only beta changes.

`shortest` and `reactive` never read `blend` (entity.py:306), so they are swept
too at no extra code cost and act as invariants on the plumbing; see the asserts
at the bottom.
"""

from topo import Network
import random
from qns.simulator.simulator import Simulator
import qns.utils.log as log
import os
from collections import Counter
from util import MODES, coefficient_of_variation
import numpy as np

# The three pilot seeds come first so the beta=0.7 row stays comparable with
# Tables II/III; the rest are extra topologies.  Three was far too few here --
# seeds disagree on the *sign* of the drop-vs-beta trend, so a 3-seed mean
# describes no actual network.
SEEDS = (101, 202, 303) + tuple(range(404, 416))

# 0.0 = history only, 1.0 = forecast only, 0.7 = the untuned default.
BLENDS = (0.0, 0.3, 0.5, 0.7, 1.0)

os.makedirs("output", exist_ok=True)
f = open("output/exp5_blend.csv", "w", buffering=1)

results = {}  # (seed, blend, mode) -> (completed, dropped), checked at the end

# Pilot grid: n=50, reqs=5, memorySize=10, w=12, M=10, queryTime=0.05 s.
# Only the prediction weight is swept here.
for seed in SEEDS:
    random.seed(seed)
    randomstate = random.getstate()  # one topology and request set per seed
    for blend in BLENDS:
        for mode, reroute, predictive, utility in MODES:
            random.setstate(randomstate)

            s = Simulator(0, 10, 1000)
            log.install(s)
            net = Network(n=50, p = 0.1, reqs = 5, memorySize=10, windowSize = 12, queryTime= 0.05, send_max_try= 10, rate = 1000, delay = 0.001, allow_reroute=reroute, random_memory=False, predictive=predictive, utility=utility, blend=blend)

            net.install(s)
            s.run()

            ans_list = []
            drop_list = []
            for req in net.s:
                c = Counter([tuple(x.route) for x in req.sendedList])
                ans_list.append(len(req.sendedList))
                drop_list.append(len(req.dropList))

            completed, dropped = sum(ans_list), sum(drop_list)
            cv = coefficient_of_variation(ans_list)
            results[(seed, blend, mode)] = (completed, dropped)
            f.write(f"{seed},{blend},12,10,{mode},{completed},{dropped},{np.std(ans_list)},{cv:.4f},{ans_list}\n")

            print(seed, mode, blend, completed, dropped, sep=",")
f.close()

# Invariants: these are what fail if beta stops reaching the nodes.
for seed in SEEDS:
    for mode in ("shortest", "reactive"):
        # Neither arm consults self.blend (entity.py:306), so beta cannot move them.
        values = {results[(seed, blend, mode)] for blend in BLENDS}
        assert len(values) == 1, f"{mode} moved with beta on seed {seed}: {values}"
    if 0.0 in BLENDS:
        # At beta=0 the blend collapses to stat2(v) and the "cost" arm still ranks
        # by y, which is the reactive baseline exactly (entity.py:311, 319-323).
        assert results[(seed, 0.0, "predictive_cost")] == results[(seed, 0.0, "reactive")], (
            f"predictive_cost at beta=0 differs from reactive on seed {seed}")
print("invariants OK")
