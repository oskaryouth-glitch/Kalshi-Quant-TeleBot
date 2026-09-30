"""Command line interface. Run ``lockerlab --help``.

Nothing here bids, buys, lists or posts. Every command reads or appends to
the local database only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import analysis, capture, paper, reports
from .config import Config, default_paths
from .db import connect
from .money import fmt
from .pit import find_auction
from .rawstore import RawStore
from .strategies import OperatorEstimate, UnderwritingError
from .timeutil import parse_user_time

ESTIMATE_TEMPLATE = """\
# Paper-decision estimate for ONE auction. Fill this in from the photos
# BEFORE the auction ends, then run: lockerlab decide <this file>
auction:
  source: storagetreasures
  external_id: "EXAMPLE-123456"
strategy: manual_v1

# What would the things that actually SELL bring in, in total, before fees?
# Think sold prices, not asking prices. Include the hidden boxes at a
# pessimistic guess. low = hidden stuff is junk; high = pleasant surprise.
gross_proceeds: {low: 150, base: 400, high: 900}
confidence: 0.4   # 0-1: how much do the photos really show?

volume:
  fill_fraction: 0.5    # share of the unit's volume that is full
  keep_fraction: 0.3    # share of the contents worth selling
  trash_fraction: 0.4   # share of the contents that goes to the dump (rest: donate)
longest_item_in: 48     # longest single item you'd have to move, inches

counts:
  listings: 12     # separate listings you would create (bundles count once)
  orders: 10       # separate sales you expect
  mattresses: 0
  appliances: 0
  ewaste_items: 0
  bulky_items: 0   # couches, dressers, anything two-person

categories: [tools, outdoor]
reasons:
  - "visible DeWalt tool bag (possible)"
  - "organized totes"
notes: ""
"""


def _ctx(args):
    paths = default_paths()
    if getattr(args, "home", None):
        from .config import Paths

        paths = Paths(Path(args.home).resolve())
    cfg = Config.load(paths.config_dir)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(paths.db_path)
    return paths, cfg, conn


def cmd_init(args) -> int:
    paths, cfg, conn = _ctx(args)
    capture.register_sources(conn, cfg)
    print(f"database: {paths.db_path}")
    print(f"raw evidence: {paths.raw_dir}")
    print(f"sources registered: {', '.join(cfg.sources)}")
    return 0


def cmd_sources(args) -> int:
    _, cfg, _ = _ctx(args)
    for key, s in cfg.sources.items():
        print(f"{key:22} automated={s.get('automated_collection'):11} manual={s.get('manual_capture'):10} "
              f"{s.get('name')}")
        if s.get("next_step"):
            print(f"{'':22} next: {s['next_step']}")
    return 0


def cmd_template(args) -> int:
    text = capture.template_csv() if args.kind == "capture" else ESTIMATE_TEMPLATE
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_import(args) -> int:
    paths, cfg, conn = _ctx(args)
    try:
        res = capture.import_csv(conn, RawStore(paths.raw_dir), cfg, Path(args.file), args.market, args.by)
    except capture.CaptureError as e:
        print("IMPORT REJECTED (nothing was written):", file=sys.stderr)
        for err in e.errors:
            print(f"  {err}", file=sys.stderr)
        return 2
    if res.already_imported:
        print(f"already imported (raw capture #{res.raw_capture_id}); nothing to do")
        return 0
    print(f"raw capture #{res.raw_capture_id}: {res.observations} observations, {res.new_auctions} new auctions")
    for w in res.warnings:
        print(f"  warning: {w}")
    return 0


def cmd_photos(args) -> int:
    paths, cfg, conn = _ctx(args)
    aid = find_auction(conn, args.source, args.external_id)
    if aid is None:
        print(f"unknown auction {args.source}/{args.external_id}", file=sys.stderr)
        return 2
    market = conn.execute("SELECT market_key FROM auctions WHERE id = ?", (aid,)).fetchone()["market_key"]
    observed = parse_user_time(args.observed_at, cfg.market(market).get("timezone"))
    try:
        added, skipped = capture.import_photos(conn, RawStore(paths.raw_dir), args.source, args.external_id,
                                               observed, [Path(p) for p in args.files], args.by)
    except capture.CaptureError as e:
        print("\n".join(e.errors), file=sys.stderr)
        return 2
    print(f"added {added} photos, skipped {skipped} duplicates")
    return 0


def cmd_auctions(args) -> int:
    _, _, conn = _ctx(args)
    rows = conn.execute(
        """SELECT a.source_key, a.external_id, a.market_key, o.status, o.size_bucket, o.current_bid_cents,
                  o.final_price_cents, o.ends_at, o.observed_at, o.city,
                  (SELECT COUNT(*) FROM auction_observations x WHERE x.auction_id = a.id) AS n_obs
           FROM auctions a JOIN auction_observations o ON o.id = (
               SELECT id FROM auction_observations WHERE auction_id = a.id
               ORDER BY observed_at DESC, id DESC LIMIT 1)
           WHERE (? IS NULL OR a.market_key = ?)
           ORDER BY o.ends_at""",
        (args.market, args.market),
    ).fetchall()
    out = [{
        "auction": f"{r['source_key']}/{r['external_id']}", "status": r["status"], "size": r["size_bucket"],
        "bid_cents": r["current_bid_cents"], "final_cents": r["final_price_cents"],
        "ends_at_utc": r["ends_at"][:16] if r["ends_at"] else None, "obs": r["n_obs"], "city": r["city"],
    } for r in rows if not args.open or r["status"] in ("scheduled", "active")]
    print(reports.format_table(out))
    return 0


def render_underwriting(res: paper.DecisionResult, recorded: bool) -> str:
    uw = res.underwriting
    snap = uw.inputs["snapshot"]
    ev = uw.outputs["evaluations"]
    b, lo, hi = ev["base"], ev["low"], ev["high"]
    t = uw.outputs["transport"]["choice"]
    d = uw.outputs["disposal"]
    size = f"{snap['width_ft']:g}x{snap['length_ft']:g}" if snap["width_ft"] else "?"
    pph = b.get("cash_profit_per_hour_cents")
    lines = [
        f"AUCTION: {snap['source_key']}/{snap['external_id']}  {size} ({snap['size_bucket']})  "
        f"{snap.get('city') or ''}  ends {snap['ends_at'] or 'unknown'} UTC",
        f"INFORMATION AS OF: {res.decided_at} (observation #{snap['observation_id']}, observed {snap['observed_at']})",
        f"CURRENT BID [OBSERVED]: {fmt(snap['current_bid_cents'])}",
        f"MAXIMUM RECOMMENDED PAPER BID: {fmt(uw.max_bid_cents)}",
        f"  (limited by: {', '.join(uw.outputs['binding_constraints']) or '-'})",
        f"FIGURES BELOW ARE AT BID {fmt(uw.outputs['evaluated_at_bid_cents'])}; all ESTIMATED:",
        f"EXPECTED GROSS REVENUE: {fmt(b['gross_proceeds_cents'])} "
        f"(low {fmt(lo['gross_proceeds_cents'])}, high {fmt(hi['gross_proceeds_cents'])}; "
        f"after {uw.inputs['valuation_haircut']:.0%} haircut)",
        f"EXPECTED CASH COSTS: {fmt(b['cash_expenses_cents'])}",
        f"EXPECTED CASH PROFIT: {fmt(b['cash_profit_cents'])} "
        f"(low {fmt(lo['cash_profit_cents'])}, high {fmt(hi['cash_profit_cents'])})",
        "EXPECTED ECONOMIC PROFIT (cash - hours x value of time): " + ", ".join(
            f"{fmt(v)} at ${int(k) // 100}/h"
            for k, v in uw.outputs.get("economic_profit_cents_by_labor_value", {}).get("base", {}).items()),
        f"EXPECTED CASH ROI: {b['cash_roi']:.0%}" if b.get("cash_roi") is not None else "EXPECTED CASH ROI: n/a",
        f"CASH REQUIRED UP FRONT: {fmt(b['cash_required_cents'])}",
        f"EXPECTED LABOR: {b['labor_hours']:.1f} hours",
        f"EXPECTED CASH PROFIT/HOUR: {fmt(round(pph)) if pph is not None else 'n/a'}",
        f"VALUE DENSITY: {uw.outputs['value_density']} "
        f"({fmt(round(b['gross_per_retained_cuft_cents'] or 0))}/kept cuft, "
        f"cash profit {fmt(round(b['cash_profit_cents'] / b['retained_cuft'])) if b['retained_cuft'] else 'n/a'}/kept cuft)",
        f"DISPOSAL: {d['burden_level']} ({fmt(d['total_cents'])}, {d['visits']} dump visit(s), "
        f"{uw.outputs['volumes_cuft']['trash']:.0f} cuft trash)",
        f"TRANSPORT: {t['trips']} trip(s) by {t['vehicle']} ({fmt(t['cost_cents'])})",
        f"DISPOSAL ROUTE: {', '.join(d.get('pathways', [])) or 'none'}",
        f"CONFIDENCE: {uw.confidence:.0%}",
        f"DECISION: {uw.decision}" + (f"  paper bid {fmt(uw.paper_bid_cents)}" if uw.paper_bid_cents else ""),
        "REASONS:",
        *(f"  * {r}" for r in uw.reasons),
        f"UNVERIFIED ASSUMPTIONS IN PLAY: {uw.outputs['unverified_assumption_count']} "
        "(see: lockerlab report assumptions)",
        f"RECORDED: paper decision #{res.decision_id}" if recorded else "DRY RUN: nothing recorded",
    ]
    return "\n".join(lines)


def _load_estimate(conn, path):
    d = yaml.safe_load(Path(path).read_text())
    a = d["auction"]
    aid = find_auction(conn, a["source"], str(a["external_id"]))
    if aid is None:
        raise UnderwritingError(f"unknown auction {a['source']}/{a['external_id']}; import a capture first")
    return aid, d.get("strategy", "manual_v1"), OperatorEstimate.from_dict(d)


def cmd_underwrite(args, record: bool) -> int:
    _, cfg, conn = _ctx(args)
    try:
        aid, strat, est = _load_estimate(conn, args.file)
        res = paper.decide(conn, cfg, aid, est, strategy_key=strat, record=record)
    except (UnderwritingError, paper.DecisionRefused, KeyError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    print(render_underwriting(res, record))
    return 0


def cmd_settle(args) -> int:
    _, cfg, conn = _ctx(args)
    counts = paper.settle_all(conn, cfg)
    print(json.dumps(counts) if counts else "nothing to settle")
    return 0


def cmd_report(args) -> int:
    _, cfg, conn = _ctx(args)
    if args.which == "market":
        print("Final prices are OBSERVED; all-in acquisition is INFERRED (price x premium x tax).")
        print(reports.format_table(reports.market_rows(conn, args.market)))
    elif args.which == "paper":
        print("Win/loss is SIMULATED against observed outcomes (rule "
              f"{paper.SETTLEMENT_RULE}); profits are ESTIMATED, not REALIZED.")
        print(reports.format_table(reports.paper_rows(conn, args.strategy)))
    elif args.which == "coverage":
        for k, v in reports.coverage(conn).items():
            print(f"{k:32} {v}")
    elif args.which == "assumptions":
        rows = reports.assumption_rows(cfg)
        print(f"{len(rows)} assumptions are not VERIFIED:")
        for r in rows:
            print(f"  {r['status']:10} {r['path']} = {r['value']}")
    return 0


def cmd_breakeven(args) -> int:
    _, cfg, _ = _ctx(args)
    prof = analysis.Profile(
        fill_fraction=args.fill, keep_fraction=args.keep, trash_fraction=args.trash,
        avg_sale_cents=int(args.avg_sale * 100), longest_item_in=args.longest,
    )
    bids = [int(float(b) * 100) for b in args.bids.split(",")]
    print(f"SIMULATED from config assumptions ({args.market}). Each cell: minimum BASE-case gross resale "
          "(before the valuation haircut) the unit must hold for the margin rules to allow that bid.")
    print(f"profile: {prof}")
    print(reports.format_table(analysis.breakeven_table(
        args.market, cfg.market(args.market), cfg.underwriting, bids, prof)))
    return 0


def cmd_sensitivity(args) -> int:
    import csv as _csv

    _, cfg, _ = _ctx(args)
    data = analysis.sensitivity(args.market, cfg.market(args.market), cfg.underwriting,
                                avg_sale_cents=int(args.avg_sale * 100))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"sensitivity_{args.market}_avg{int(args.avg_sale)}"
    (out / f"{stem}.json").write_text(json.dumps(data, indent=1))
    with open(out / f"{stem}.csv", "w", newline="") as f:
        cols = [k for k in data["cells"][0] if k != "pathways"] + ["pathways"]
        w = _csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for c in data["cells"]:
            w.writerow(c | {"pathways": " ".join(c["pathways"])})
    (out / f"{stem}.md").write_text(analysis.render_sensitivity_md(data))
    print(f"wrote {out}/{stem}.{{json,csv,md}} ({len(data['cells'])} cells). All figures SIMULATED.")
    return 0


def cmd_serve(args) -> int:
    try:
        import uvicorn

        from .web.app import create_app
    except ImportError:
        print('The desk needs the app extras: pip install -e ".[app]"', file=sys.stderr)
        return 2
    paths = default_paths() if not args.home else None
    home = Path(args.home).resolve() if args.home else paths.home
    print(f"LockerLab desk: http://{args.host}:{args.port}  (Ctrl+C to stop)")
    if args.host not in ("127.0.0.1", "localhost"):
        print("Warning: reachable from other devices on this network. There is no login.", file=sys.stderr)
    uvicorn.run(create_app(home), host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_source_policy(args) -> int:
    from . import platforms
    from .db import transaction
    from .timeutil import now_ts

    _, cfg, conn = _ctx(args)
    capture.register_sources(conn, cfg)
    if args.policy is None:
        for k in cfg.sources:
            p = platforms.capture_policy(conn, cfg.sources, k)
            print(f"{k:22} {p.screenshot_policy:12} ({p.decided_by}) {p.reason[:90]}")
        return 0
    try:
        with transaction(conn):
            platforms.set_policy(conn, cfg.sources, args.source, args.policy, args.basis, args.note or "", now_ts())
    except (ValueError, KeyError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    print(f"{args.source}: screenshots {args.policy} (recorded)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lockerlab", description="Paper-only storage auction research system")
    p.add_argument("--home", help="project dir holding config/ and data/ (default: $LOCKERLAB_HOME or cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the database and register sources").set_defaults(fn=cmd_init)
    sub.add_parser("sources", help="show sources and their access-compliance status").set_defaults(fn=cmd_sources)

    t = sub.add_parser("template", help="print a capture CSV or estimate YAML template")
    t.add_argument("kind", choices=["capture", "estimate"])
    t.add_argument("--out")
    t.set_defaults(fn=cmd_template)

    i = sub.add_parser("import", help="import a manual capture CSV")
    i.add_argument("file")
    i.add_argument("--market", required=True)
    i.add_argument("--by", help="who captured it")
    i.set_defaults(fn=cmd_import)

    ph = sub.add_parser("photos", help="attach saved auction photos")
    ph.add_argument("source")
    ph.add_argument("external_id")
    ph.add_argument("--observed-at", required=True, help="when you saved them (local time ok)")
    ph.add_argument("--by")
    ph.add_argument("files", nargs="+")
    ph.set_defaults(fn=cmd_photos)

    a = sub.add_parser("auctions", help="list auctions with their latest observation")
    a.add_argument("--market")
    a.add_argument("--open", action="store_true", help="only scheduled/active")
    a.set_defaults(fn=cmd_auctions)

    u = sub.add_parser("underwrite", help="dry-run underwriting from an estimate YAML (records nothing)")
    u.add_argument("file")
    u.set_defaults(fn=lambda args: cmd_underwrite(args, record=False))

    d = sub.add_parser("decide", help="record a FORWARD paper decision from an estimate YAML")
    d.add_argument("file")
    d.set_defaults(fn=lambda args: cmd_underwrite(args, record=True))

    sub.add_parser("settle", help="settle paper decisions against observed outcomes").set_defaults(fn=cmd_settle)

    r = sub.add_parser("report", help="evidence reports")
    r.add_argument("which", choices=["market", "paper", "coverage", "assumptions"])
    r.add_argument("--market")
    r.add_argument("--strategy")
    r.set_defaults(fn=cmd_report)

    be = sub.add_parser("breakeven", help="hurdle gross resale by unit size and bid (pre-data analysis)")
    be.add_argument("--market", default="colorado_springs")
    be.add_argument("--bids", default="0,25,50,100,200,400", help="comma-separated dollars")
    be.add_argument("--fill", type=float, default=0.5)
    be.add_argument("--keep", type=float, default=0.3)
    be.add_argument("--trash", type=float, default=0.4)
    be.add_argument("--avg-sale", type=float, default=40.0, help="average $ per sale")
    be.add_argument("--longest", type=float, default=48.0, help="longest item, inches")
    be.set_defaults(fn=cmd_breakeven)

    se = sub.add_parser("sensitivity", help="5x5/5x10 profit grids by bid, realized gross, disposal, vehicle")
    se.add_argument("--market", default="colorado_springs")
    se.add_argument("--avg-sale", type=float, default=50.0, help="average $ per sale (drives labor)")
    se.add_argument("--out-dir", default="docs/generated")
    se.set_defaults(fn=cmd_sensitivity)

    sv = sub.add_parser("serve", help="open the daily desk in your browser (local only)")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8765)
    sv.set_defaults(fn=cmd_serve)

    sp = sub.add_parser("source-policy", help="show or record per-source screenshot policy")
    sp.add_argument("source", nargs="?")
    sp.add_argument("policy", nargs="?", choices=["allowed", "manual_only"])
    sp.add_argument("--basis", default="other", choices=["written_permission", "api_agreement",
                    "terms_reviewed_no_restriction", "revoked", "other"])
    sp.add_argument("--note", help="why (required when changing)")
    sp.set_defaults(fn=cmd_source_policy)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
