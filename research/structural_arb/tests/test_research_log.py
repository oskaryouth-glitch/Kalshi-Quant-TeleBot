from decimal import Decimal as D

from sarb.research_log import CandidateRecord, LegRecord, ResearchLog, read


def leg(t):
    return LegRecord(t, "buy", "yes", "1", "0.40", "0.40", "0.40", "5", "1", None, None, 1, 2)


def test_roundtrip_plain_and_gz(tmp_path):
    for suffix in (".jsonl", ".jsonl.gz"):
        p = str(tmp_path / f"log{suffix}")
        lg = ResearchLog(p)
        lg.write(CandidateRecord("R2_NESTED", "GUARANTEED", "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", ["FAIL:x"],
                                 ["EV"], "1", [leg("A"), leg("B")], raw_inconsistency=D("0.01"), locked_payoff=D(1),
                                 extra={"phase": "P2"}))
        recs = list(read(p))
        assert recs[0]["raw_inconsistency"] == "0.01" and recs[0]["extra"]["phase"] == "P2"
        assert recs[0]["schema_version"] == 2
