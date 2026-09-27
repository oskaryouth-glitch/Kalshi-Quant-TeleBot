from decimal import Decimal as D
from sarb.research_log import ResearchLog, CandidateRecord, LegRecord, read, REJECTED, NOT_EXECUTABLE, GUARANTEED
from sarb.report import summarize


def leg(t):
    return LegRecord(t, "buy", "yes", "1", "0.40", "0.40", "0.40", "5", "1", "0.02", "0.0168", 1, 2)


def test_roundtrip_and_summary(tmp_path):
    for suffix in (".jsonl", ".jsonl.gz"):
        p = str(tmp_path / f"log{suffix}")
        lg = ResearchLog(p)
        lg.write(CandidateRecord("R2_MONOTONE", GUARANTEED, NOT_EXECUTABLE, ["EDGE_NONPOSITIVE_AFTER_FEES"],
                                 ["EV"], "1", [leg("A"), leg("B")], raw_inconsistency=D("0.01"), edge=D("-0.03"),
                                 locked_payoff=D(1)))
        lg.write(CandidateRecord("R1_MEE_LONG", GUARANTEED, REJECTED, ["SKEW"], ["EV"], "1", [leg("A")]))
        recs = list(read(p))
        assert len(recs) == 2 and recs[0]["edge"] == "-0.03" and recs[0]["legs"][1]["ticker"] == "B"
        assert recs[0]["candidate_id"] != recs[1]["candidate_id"]
        s = summarize(recs)
        assert s["by_status"] == {NOT_EXECUTABLE: 1, REJECTED: 1}
        assert s["raw_positive_but_edge_nonpositive"] == {"R2_MONOTONE": 1}
