"""Time-versioned fee ledger: effective_at -> fee_type -> multiplier -> source/provenance.

Official facts this relies on (sources/docs, verified 2026-09-27):
  F1 GET /series/fee_changes?show_historical=true returns "ALL fee changes previous and
     upcoming" (API changelog). The series history is complete.
  F2 The Series object's fee_type / fee_multiplier equal the latest change in that history
     (checked live on KXMLBSB, KXMLBGAME, KXGDPYEAR, KXMVECROSSCATEGORY, KXMLBEXTRAS).
  F3 Event object fields fee_type_override / fee_multiplier_override: "When present, takes
     precedence over the series-level fee for this event's markets." They are omitempty:
     absent or null means no override is in force.
  F4 GET /events/fee_changes lists ONLY future-scheduled event overrides. It has no
     show_historical parameter. A past override is therefore visible only through the event
     object (F3), never through the change list.
  F5 A change with both override fields null clears the override (docs).

Resolution of the fee in force at snapshot time t for (series S, event E):
  1. Event layer. It needs a direct observation of the event object at time o_E, with
     t - MAX_OBS_AGE <= o_E <= t (collected by the collector: GET /events/{E} for every leg in
     P2/P3/AUDIT). Its state is then updated by any recorded scheduled event change with
     o_E < effective_at <= t (the latest wins; a null change clears it).
     No fresh observation -> FEE_UNRESOLVED(EVENT_NOT_OBSERVED / EVENT_OBSERVATION_STALE).
  2. If an override is in force, use it. Otherwise use the series layer: the latest of
     {series history changes with effective_at <= t, series object observations at o_S <= t}.
     If the latest is an observation, it must be consistent with the latest history change
     before it (otherwise SERIES_LEDGER_CONFLICT). There must be a fresh series observation
     (o_S >= t - MAX_OBS_AGE), or the history must cover t with a change after the last
     observation; otherwise FEE_UNRESOLVED(SERIES_NOT_OBSERVED).
  3. Boundary guard: if t is within BOUNDARY_S of any known scheduled change for S or E, or
     an observation disagrees with the recorded schedule, -> FEE_UNRESOLVED. The exact instant
     at which the API reflects a change is not documented.
  4. The fee type must be modelled (fees.SUPPORTED_TAKER_TYPES), else FEE_UNRESOLVED.
There is no max(), no floor, and no substitution of historical values.

Persistence: an append-only JSONL. Scheduled changes are stored once each. Observations are
stored when the observed state CHANGES (plus the first observation per key). Freshness
("last confirmed at") is kept in memory only, so after a restart nothing resolves until each
key is re-observed.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from decimal import Decimal

from . import fees as FEES

MAX_OBS_AGE_NS = 30 * 1_000_000_000
BOUNDARY_NS = 60 * 1_000_000_000


class FeeUnresolved(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"FEE_UNRESOLVED:{code}:{detail}")
        self.code = code


def _iso_to_ns(s: str) -> int:
    import datetime as dt
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1_000_000_000)


def _state(fee_type, mult):
    if fee_type is None or mult is None:
        return None
    return (str(fee_type), str(Decimal(str(mult))))


@dataclass(frozen=True)
class Change:
    layer: str                 # "series" | "event"
    key: str                   # series ticker | event ticker
    effective_ns: int
    state: tuple | None        # (fee_type, multiplier) ; None = cleared (event layer only)
    source: str


class FeeLedger:
    def __init__(self, path: str | None = None, known_as_of_ns: int | None = None):
        """known_as_of_ns: when loading history, ignore changes first seen after this time (used
        by sarb/reconstruct.py to avoid look-ahead)."""
        self.path = path
        self._lock = threading.Lock()
        self.changes: dict[tuple[str, str], list[Change]] = {}       # (layer, key) -> sorted
        self._change_ids: set[str] = set()
        self.obs: dict[tuple[str, str], list[tuple[int, tuple | None]]] = {}   # persisted state-change points
        self.confirmed: dict[tuple[str, str], tuple[int, tuple | None]] = {}   # in-memory: last observation
        if path and os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    if line.strip():
                        rec = json.loads(line)
                        if rec["kind"] == "change" and known_as_of_ns is not None and rec.get("seen_ns", 0) > known_as_of_ns:
                            continue
                        if rec["kind"] == "obs" and known_as_of_ns is not None:
                            continue          # reconstruction replays recorded observations explicitly
                        self._apply(rec, persist=False)

    # ------------------------------------------------------------------ ingest
    def _append(self, rec: dict) -> None:
        if self.path:
            with open(self.path, "a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def _apply(self, rec: dict, persist: bool) -> bool:
        if rec["kind"] == "change":
            cid = rec["id"]
            if cid in self._change_ids:
                return False
            self._change_ids.add(cid)
            st = tuple(rec["state"]) if rec["state"] else None
            lst = self.changes.setdefault((rec["layer"], rec["key"]), [])
            lst.append(Change(rec["layer"], rec["key"], rec["effective_ns"], st, rec["source"]))
            lst.sort(key=lambda c: c.effective_ns)
        else:
            st = tuple(rec["state"]) if rec["state"] else None
            pts = self.obs.setdefault((rec["layer"], rec["key"]), [])
            if pts and pts[-1][1] == st and pts[-1][0] <= rec["observed_ns"]:
                return False
            pts.append((rec["observed_ns"], st))
            pts.sort(key=lambda p: p[0])
        if persist:
            self._append(rec)
        return True

    def add_series_changes(self, rows: list[dict]) -> int:
        n = 0
        with self._lock:
            for r in rows:
                rec = {"kind": "change", "layer": "series", "key": r["series_ticker"],
                       "effective_ns": _iso_to_ns(r["scheduled_ts"]),
                       "state": _state(r.get("fee_type"), r.get("fee_multiplier")),
                       "id": "S:" + str(r.get("id") or json.dumps(r, sort_keys=True)),
                       "source": f"series_fee_change:{r.get('id')}@{r['scheduled_ts']}", "seen_ns": time.time_ns()}
                n += self._apply(rec, True)
        return n

    def add_event_changes(self, rows: list[dict]) -> int:
        n = 0
        with self._lock:
            for r in rows:
                rec = {"kind": "change", "layer": "event", "key": r["event_ticker"],
                       "effective_ns": _iso_to_ns(r["scheduled_ts"]),
                       "state": _state(r.get("fee_type_override"), r.get("fee_multiplier_override")),
                       "id": "E:" + str(r.get("id") or json.dumps(r, sort_keys=True)),
                       "source": f"event_fee_change:{r.get('id')}@{r['scheduled_ts']}", "seen_ns": time.time_ns()}
                n += self._apply(rec, True)
        return n

    def observe_event(self, event: dict, observed_ns: int) -> None:
        st = _state(event.get("fee_type_override"), event.get("fee_multiplier_override"))
        self._observe("event", event["event_ticker"], st, observed_ns)

    def observe_series(self, series: dict, observed_ns: int) -> None:
        s = series.get("series", series)
        st = _state(s.get("fee_type"), s.get("fee_multiplier"))
        self._observe("series", s["ticker"], st, observed_ns)

    def _observe(self, layer: str, key: str, st, observed_ns: int) -> None:
        with self._lock:
            k = (layer, key)
            if k not in self.confirmed or self.confirmed[k][0] <= observed_ns:
                self.confirmed[k] = (observed_ns, st)
            self._apply({"kind": "obs", "layer": layer, "key": key, "observed_ns": observed_ns,
                         "state": list(st) if st else None}, True)

    # ------------------------------------------------------------------ resolution
    def _boundary(self, layer: str, key: str, t: int) -> Change | None:
        for c in self.changes.get((layer, key), []):
            if abs(c.effective_ns - t) <= BOUNDARY_NS:
                return c
        return None

    def _latest_change(self, layer: str, key: str, lo_excl: int | None, hi_incl: int) -> Change | None:
        best = None
        for c in self.changes.get((layer, key), []):
            if c.effective_ns <= hi_incl and (lo_excl is None or c.effective_ns > lo_excl):
                best = c
        return best

    def resolve(self, series: str, event: str, t_ns: int) -> FEES.ResolvedFee:
        with self._lock:
            for layer, key in (("event", event), ("series", series)):
                b = self._boundary(layer, key, t_ns)
                if b:
                    raise FeeUnresolved("NEAR_SCHEDULED_CHANGE", f"{layer}:{key}:{b.source}")
            # ---- event layer
            ob = self.confirmed.get(("event", event))
            if ob is None:
                raise FeeUnresolved("EVENT_NOT_OBSERVED", event)
            o_ns, o_state = ob
            if o_ns > t_ns or t_ns - o_ns > MAX_OBS_AGE_NS:
                raise FeeUnresolved("EVENT_OBSERVATION_STALE", f"{event}:{(t_ns - o_ns) / 1e9:.1f}s")
            prior = self._latest_change("event", event, None, o_ns)
            if prior is not None and o_ns - prior.effective_ns > BOUNDARY_NS and prior.state != o_state:
                raise FeeUnresolved("EVENT_LEDGER_CONFLICT", f"{event}: schedule {prior.state} vs observed {o_state}")
            later = self._latest_change("event", event, o_ns, t_ns)
            ev_state, ev_src = (later.state, later.source) if later else (o_state, f"event_object_observed@{o_ns}")
            if ev_state is not None:
                return self._typed(FEES.ResolvedFee(ev_state[0], Decimal(ev_state[1]), ev_src))
            # ---- series layer
            so = self.confirmed.get(("series", series))
            hist = self._latest_change("series", series, None, t_ns)
            if so is not None and so[0] <= t_ns:
                s_ns, s_state = so
                prior_s = self._latest_change("series", series, None, s_ns)
                if prior_s is not None and s_ns - prior_s.effective_ns > BOUNDARY_NS and prior_s.state != s_state:
                    raise FeeUnresolved("SERIES_LEDGER_CONFLICT", f"{series}: history {prior_s.state} vs observed {s_state}")
                after = self._latest_change("series", series, s_ns, t_ns)
                if after is not None:
                    st, src = after.state, after.source
                elif t_ns - s_ns <= MAX_OBS_AGE_NS:
                    st, src = s_state, f"series_object_observed@{s_ns}"
                else:
                    raise FeeUnresolved("SERIES_OBSERVATION_STALE", f"{series}:{(t_ns - s_ns) / 1e9:.1f}s")
            else:
                raise FeeUnresolved("SERIES_NOT_OBSERVED", series)
            if st is None:
                raise FeeUnresolved("SERIES_FEE_MISSING", series)
            return self._typed(FEES.ResolvedFee(st[0], Decimal(st[1]), src + ("|event:no_override" if o_state is None else "")))

    @staticmethod
    def _typed(rf: FEES.ResolvedFee) -> FEES.ResolvedFee:
        if rf.fee_type not in FEES.SUPPORTED_TAKER_TYPES:
            raise FeeUnresolved("UNSUPPORTED_FEE_TYPE", rf.fee_type)
        return rf
