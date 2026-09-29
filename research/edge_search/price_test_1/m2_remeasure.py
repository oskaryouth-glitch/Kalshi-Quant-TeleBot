"""M2-NO re-measurement after the candlestick parsing fix (RESULTS.md, post-freeze change 5).

Re-runs the FROZEN m2_no.measure() and m2_no.summarize() over EXACTLY the frozen universe saved by the
original run (outputs/m2_universe.json, identical to outputs/asrun_bug_m2_universe.json). Rebuilding the
universe would add markets settled after the original run and change the sample."""
import json

import pt1_common as P
from m2_no import measure, summarize

u = json.loads((P.OUT / "m2_universe.json").read_text())
fees, results = {}, []
for row in u["rows"]:
    if row["series"] not in fees:
        fees[row["series"]] = P.SeriesFees(row["series"])
    results.append(measure(row, fees[row["series"]]))
P.save("m2_results.json", results)
summarize(results)
