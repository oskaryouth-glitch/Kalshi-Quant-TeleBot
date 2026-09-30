"""LockerLab local web app: the daily desk.

Run with ``lockerlab serve`` (binds to 127.0.0.1). Every write goes through the
same audited functions as the CLI (intake, paper, assumptions); the web layer
adds no shortcuts around them. Nothing here can bid, buy, list or message.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote
from typing import Callable
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import assumptions as assumptions_mod
from .. import desk, intake, paper, platforms
from ..capture import register_sources
from ..config import STATUS_LABELS, STATUSES, Config, Paths
from ..db import connect, transaction
from ..extract import ClaudeExtractor, Extractor
from ..money import fmt, parse_dollars
from ..pit import snapshot_as_of
from ..quick import CATEGORIES, DISPOSAL_LEVELS, TRANSPORT_LABELS, TRANSPORT_LEVELS, QuickEstimate, \
    opportunity_score
from ..rawstore import RawStore
from ..strategies import UnderwritingError
from ..timeutil import from_ts, now_ts

HERE = Path(__file__).parent
MARKET_DEFAULT = "colorado_springs"
READINESS_CHECKS = {
    "transport_confirmed": "Vehicle confirmed (friend's SUV/pickup on 48 h notice, or U-Haul plan)",
    "disposal_called": "Called Woodmen Dump / Peak Disposal and confirmed household self-haul pricing",
    "storage_space": "Dry, secure storage space identified",
    "tax_checked": "Checked sales-tax license requirements with CDOR / Colorado Springs",
}


def create_app(home: Path, extractor_factory: Callable[[Config], Extractor] | None = None,
               clock: Callable[[], str] = now_ts) -> FastAPI:
    paths = Paths(home.resolve())
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    base_cfg = Config.load(paths.config_dir)
    store = RawStore(paths.raw_dir)
    boot = connect(paths.db_path)
    register_sources(boot, base_cfg)
    boot.close()

    def make_extractor(cfg: Config) -> Extractor:
        if extractor_factory:
            return extractor_factory(cfg)
        return ClaudeExtractor(cfg.underwriting.get("extraction", "model"),
                               cfg.underwriting.get("extraction", "effort"))

    app = FastAPI(title="LockerLab", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    tpl = Jinja2Templates(directory=HERE / "templates")

    def local(ts: str | None, market: str = MARKET_DEFAULT) -> str:
        """'Sat Oct 4, 2:00 PM MDT' in the market's time zone (portable, no %-d)."""
        if not ts:
            return "—"
        d = from_ts(ts).astimezone(ZoneInfo(base_cfg.market(market).get("timezone")))
        return f"{d:%a %b} {d.day}, {d.hour % 12 or 12}:{d:%M} {'AM' if d.hour < 12 else 'PM'} {d:%Z}"

    def left(hours: float | None) -> str:
        if hours is None:
            return "end unknown"
        if hours <= 0:
            return "ended"
        if hours < 1:
            return f"{int(hours * 60)}m left"
        if hours < 48:
            return f"{int(hours)}h {int((hours % 1) * 60)}m left"
        return f"{hours / 24:.1f}d left"

    def pct(x) -> str:
        return "—" if x is None else f"{x:.0%}"

    tpl.env.globals.update(fmt=fmt, local=local, left=left, pct=pct, STATUS_LABELS=STATUS_LABELS,
                           CATEGORIES=CATEGORIES, PASS_TAGS=paper.PASS_TAGS, DISPOSAL_LEVELS=DISPOSAL_LEVELS,
                           TRANSPORT_LEVELS=TRANSPORT_LEVELS, TRANSPORT_LABELS=TRANSPORT_LABELS)

    def ctx():
        conn = connect(paths.db_path)
        cfg = assumptions_mod.effective_config(conn, base_cfg)
        return conn, cfg

    def render(request: Request, name: str, **kw) -> HTMLResponse:
        return tpl.TemplateResponse(request, name, kw)

    # ------------------------------------------------------------------ desk
    @app.get("/", response_class=HTMLResponse)
    def home_page(request: Request, sizes: str = "5x5,5x10", max_bid: str = "", ending: str = "",
                  low_disposal: str = "", fits_suv: str = "", category: str = "", min_cash: str = "",
                  min_roi: str = "", min_conf: str = ""):
        conn, cfg = ctx()
        try:
            now = clock()
            rows = desk.load_auctions(conn, cfg, MARKET_DEFAULT, now)
            f = desk.Filters(
                sizes=tuple(s for s in sizes.split(",") if s) if sizes != "all" else (),
                max_current_bid_cents=parse_dollars(max_bid) if max_bid else None,
                ending_within_hours=float(ending) if ending else None,
                low_disposal=bool(low_disposal), fits_suv=bool(fits_suv), category=category or None,
                min_cash_profit_cents=parse_dollars(min_cash) if min_cash else None,
                min_roi=float(min_roi) / 100 if min_roi else None,
                min_confidence=float(min_conf) / 100 if min_conf else None)
            secs = desk.sections(rows, f)
            h = desk.health(rows, now)
            q = dict(sizes=sizes, max_bid=max_bid, ending=ending, low_disposal=low_disposal, fits_suv=fits_suv,
                     category=category, min_cash=min_cash, min_roi=min_roi, min_conf=min_conf)
            return render(request, "desk.html", s=secs, h=h, q=q, f=f,
                          todo={"estimate": len(secs["NEEDS_ESTIMATE"]), "ending": len(secs["ENDING_SOON"]),
                                "results": len(secs["AWAITING_RESULT"])})
        finally:
            conn.close()

    # --------------------------------------------------------------- capture
    @app.get("/capture", response_class=HTMLResponse)
    def capture_form(request: Request, url: str = "", error: str = ""):
        conn, cfg = ctx()
        try:
            pols = {k: platforms.capture_policy(conn, cfg.sources, k) for k in cfg.sources}
            return render(request, "capture.html", sources=cfg.sources, pols=pols, url=url, error=error,
                          markets=list(cfg.markets))
        finally:
            conn.close()

    @app.post("/capture")
    async def capture_submit(request: Request, url: str = Form(""), source_key: str = Form(""),
                             market_key: str = Form(MARKET_DEFAULT),
                             screenshots: list[UploadFile] = File(default=[]),
                             photos: list[UploadFile] = File(default=[])):
        conn, cfg = ctx()
        try:
            files = [(u.filename or "screenshot", await u.read(), "screenshot") for u in screenshots if u.filename]
            files += [(u.filename or "photo", await u.read(), "auction_photo") for u in photos if u.filename]
            files = [f for f in files if f[1]]
            try:
                res = intake.start_intake(conn, store, cfg, url, files, market_key, source_key or None, now=clock())
            except intake.IntakeError as e:
                pols = {k: platforms.capture_policy(conn, cfg.sources, k) for k in cfg.sources}
                return render(request, "capture.html", sources=cfg.sources, pols=pols, url=url,
                              error=" ".join(e.errors), markets=list(cfg.markets))
            it = intake.intake(conn, res.intake_id)
            if it["screenshot_policy"] == "allowed" and any(r == "screenshot" for _, _, r in files):
                intake.run_extraction(conn, store, cfg, res.intake_id, make_extractor(cfg), now=clock())
            notice = json.dumps(res.notices)
            return RedirectResponse(f"/capture/{res.intake_id}?n={quote(notice)}", status_code=303)
        finally:
            conn.close()

    @app.get("/capture/{iid}", response_class=HTMLResponse)
    def review(request: Request, iid: int, n: str = "[]", error: str = ""):
        conn, cfg = ctx()
        try:
            it = intake.intake(conn, iid)
            done = conn.execute("SELECT * FROM intake_confirmations WHERE intake_id = ?", (iid,)).fetchone()
            if done:
                aid = conn.execute("SELECT auction_id FROM auction_observations WHERE id = ?",
                                   (done["observation_id"],)).fetchone()["auction_id"]
                return RedirectResponse(f"/auction/{aid}", status_code=303)
            pol = platforms.capture_policy(conn, cfg.sources, it["source_key"])
            ex = intake.latest_extraction(conn, iid)
            fields = intake.form_defaults(conn, cfg, iid)
            files = intake.intake_files(conn, iid)
            try:
                notices = json.loads(n)
            except json.JSONDecodeError:
                notices = []
            return render(request, "review.html", it=it, pol=pol, ex=ex, fields=fields, files=files,
                          notices=notices, error=error, form_fields=intake.FORM_FIELDS)
        finally:
            conn.close()

    @app.post("/capture/{iid}/extract")
    def re_extract(iid: int):
        conn, cfg = ctx()
        try:
            intake.run_extraction(conn, store, cfg, iid, make_extractor(cfg), now=clock())
            return RedirectResponse(f"/capture/{iid}", status_code=303)
        finally:
            conn.close()

    @app.post("/capture/{iid}/confirm")
    async def confirm(request: Request, iid: int):
        conn, cfg = ctx()
        try:
            form = await request.form()
            values = {f: str(form.get(f, "")) for f in intake.FORM_FIELDS}
            uncertain = {f for f in intake.FORM_FIELDS if form.get(f"unsure_{f}")}
            try:
                aid, _, warnings = intake.confirm_intake(
                    conn, store, cfg, iid, values, uncertain, external_id=str(form.get("external_id", "")),
                    now=clock())
            except intake.IntakeError as e:
                return RedirectResponse(f"/capture/{iid}?error={quote(' | '.join(e.errors))}", status_code=303)
            return RedirectResponse(f"/auction/{aid}?w={quote(json.dumps(warnings))}", status_code=303)
        finally:
            conn.close()

    @app.get("/evidence/{rid}")
    def evidence(rid: int):
        conn, _ = ctx()
        try:
            r = conn.execute("SELECT * FROM raw_captures WHERE id = ? AND capture_method IN "
                             "('screenshot', 'manual_photo')", (rid,)).fetchone()
            if r is None:
                raise HTTPException(404)
            return Response(store.get(r["content_sha256"]), media_type=r["content_type"])
        finally:
            conn.close()

    # --------------------------------------------------------------- auction
    def _auction_page(request: Request, conn, cfg, aid: int, est_form: dict | None = None, calc=None,
                      error: str = "", warnings: list[str] | None = None, settlement=None):
        a = conn.execute("SELECT * FROM auctions WHERE id = ?", (aid,)).fetchone()
        if a is None:
            raise HTTPException(404)
        now = clock()
        rows = {r.id: r for r in desk.load_auctions(conn, cfg, a["market_key"], now)}
        row = rows[aid]
        obs = conn.execute("SELECT * FROM auction_observations WHERE auction_id = ? ORDER BY observed_at, id",
                           (aid,)).fetchall()
        decisions = conn.execute("SELECT * FROM paper_decisions WHERE auction_id = ? ORDER BY decided_at, id",
                                 (aid,)).fetchall()
        imgs = conn.execute("SELECT * FROM images WHERE auction_id = ? ORDER BY position", (aid,)).fetchall()
        shots = conn.execute(
            """SELECT r.id FROM intake_confirmations c JOIN intakes i ON i.id = c.intake_id
               JOIN intake_files f ON f.intake_id = i.id JOIN raw_captures r ON r.id = f.raw_capture_id
               JOIN auction_observations o ON o.id = c.observation_id
               WHERE o.auction_id = ? AND f.role = 'screenshot' ORDER BY r.id""", (aid,)).fetchall()
        if est_form is None:
            est_form = {"visible": "", "hidden_low": "0", "hidden_high": "", "disposal": "light",
                        "transport": "car_suv", "confidence": "50", "tags": [], "note": ""}
            if row.decision and row.decision.get("estimate"):
                e = row.decision["estimate"]
                est_form = {"visible": f"{e['visible_value_cents'] / 100:g}",
                            "hidden_low": f"{e['hidden_low_cents'] / 100:g}",
                            "hidden_high": f"{e['hidden_high_cents'] / 100:g}", "disposal": e["disposal"],
                            "transport": e["transport"], "confidence": f"{e['confidence'] * 100:g}",
                            "tags": e.get("tags", []), "note": ""}
        if settlement is None and row.result_status:
            settlement = intake.settlement_summary(conn, aid)
        return render(request, "auction.html", a=a, row=row, obs=obs, decisions=decisions, imgs=imgs,
                      shots=shots, est=est_form, calc=calc, error=error, warnings=warnings or [],
                      settlement=settlement, is_open=row.state not in ("CLOSED", "AWAITING_RESULT"),
                      json=json, lv=cfg.underwriting.get("labor_value_cents_per_hour"),
                      labor_values=cfg.underwriting.get("labor_value_scenarios_cents"))

    @app.get("/auction/{aid}", response_class=HTMLResponse)
    def auction_page(request: Request, aid: int, w: str = "[]"):
        conn, cfg = ctx()
        try:
            try:
                warnings = json.loads(w)
            except json.JSONDecodeError:
                warnings = []
            return _auction_page(request, conn, cfg, aid, warnings=warnings)
        finally:
            conn.close()

    def _estimate_from_form(form) -> tuple[QuickEstimate, dict]:
        raw = {"visible": str(form.get("visible", "")).strip(), "hidden_low": str(form.get("hidden_low", "0")).strip(),
               "hidden_high": str(form.get("hidden_high", "")).strip(), "disposal": str(form.get("disposal", "")),
               "transport": str(form.get("transport", "")), "confidence": str(form.get("confidence", "")).strip(),
               "tags": list(form.getlist("tags")), "note": str(form.get("note", ""))}
        try:
            vis = parse_dollars(raw["visible"] or "x")
            lo = parse_dollars(raw["hidden_low"] or "0")
            hi = parse_dollars(raw["hidden_high"] or raw["hidden_low"] or "0")
            conf = float(raw["confidence"]) / 100
        except ValueError:
            raise UnderwritingError("Enter dollar amounts for visible and hidden value, and a confidence 0-100.")
        return QuickEstimate(vis, lo, hi, raw["disposal"], raw["transport"], conf, tuple(raw["tags"]),
                             raw["note"]), raw

    @app.post("/auction/{aid}/estimate", response_class=HTMLResponse)
    async def estimate(request: Request, aid: int):
        conn, cfg = ctx()
        try:
            form = await request.form()
            action = str(form.get("action", "calculate"))
            try:
                est, raw = _estimate_from_form(form)
            except UnderwritingError as e:
                return _auction_page(request, conn, cfg, aid, est_form=None, error=str(e))
            try:
                if action == "calculate":
                    res = paper.decide(conn, cfg, aid, est, strategy_key="quick_v1", record=False, now=clock())
                else:
                    bid = str(form.get("paper_bid", "")).strip()
                    res = paper.decide(conn, cfg, aid, est, strategy_key="quick_v1", now=clock(), choice=action,
                                       paper_bid_cents=parse_dollars(bid) if bid and action == "PAPER_BID" else None,
                                       pass_tags=tuple(form.getlist("pass_tags")), note=raw["note"])
                    return RedirectResponse(f"/auction/{aid}#decisions", status_code=303)
            except (UnderwritingError, paper.DecisionRefused, ValueError) as e:
                return _auction_page(request, conn, cfg, aid, est_form=raw, error=str(e))
            snap = snapshot_as_of(conn, aid, res.decided_at)
            score = opportunity_score(res.underwriting.outputs, {
                "visible_value_cents": est.visible_value_cents, "hidden_low_cents": est.hidden_low_cents,
                "hidden_high_cents": est.hidden_high_cents, "disposal": est.disposal, "transport": est.transport,
                "confidence": est.confidence, "tags": list(est.tags)}, snap.size_bucket, snap.current_bid_cents,
                cfg.underwriting)
            return _auction_page(request, conn, cfg, aid, est_form=raw, calc={"uw": res.underwriting, "score": score})
        finally:
            conn.close()

    @app.post("/auction/{aid}/triage")
    async def triage(request: Request, aid: int):
        conn, cfg = ctx()
        try:
            form = await request.form()
            choice = str(form.get("action", "PASS"))
            try:
                paper.decide(conn, cfg, aid, None, strategy_key="triage_v1", now=clock(), choice=choice,
                             pass_tags=tuple(form.getlist("pass_tags")), note=str(form.get("note", "")))
            except paper.DecisionRefused as e:
                return _auction_page(request, conn, cfg, aid, error=str(e))
            return RedirectResponse("/" if form.get("back") else f"/auction/{aid}", status_code=303)
        finally:
            conn.close()

    @app.post("/auction/{aid}/result", response_class=HTMLResponse)
    async def result(request: Request, aid: int):
        conn, cfg = ctx()
        try:
            form = await request.form()
            try:
                summary = intake.record_result(conn, store, cfg, aid, str(form.get("outcome", "")),
                                               str(form.get("winning_price", "")), str(form.get("bid_count", "")),
                                               str(form.get("note", "")), now=clock())
            except intake.IntakeError as e:
                return _auction_page(request, conn, cfg, aid, error=" ".join(e.errors))
            return _auction_page(request, conn, cfg, aid, settlement=summary)
        finally:
            conn.close()

    # --------------------------------------------------------- secondary pages
    @app.get("/calibration", response_class=HTMLResponse)
    def calibration_page(request: Request):
        conn, cfg = ctx()
        try:
            rows = desk.load_auctions(conn, cfg, MARKET_DEFAULT, clock())
            return render(request, "calibration.html", c=desk.calibration(conn, rows), retro=desk.retro(conn, cfg),
                          MIN_N=desk.MIN_N)
        finally:
            conn.close()

    @app.get("/readiness", response_class=HTMLResponse)
    def readiness_page(request: Request, error: str = ""):
        conn, cfg = ctx()
        try:
            rows = desk.load_auctions(conn, cfg, MARKET_DEFAULT, clock())
            sells = conn.execute("SELECT * FROM selling_time_log ORDER BY id DESC").fetchall()
            checks = desk._latest_checks(conn)
            return render(request, "readiness.html", r=desk.readiness(conn, cfg, rows, clock()), sells=sells,
                          checks=checks, CHECKS=READINESS_CHECKS, error=error)
        finally:
            conn.close()

    @app.post("/readiness/check")
    def readiness_check(check_key: str = Form(...), status: str = Form(...), note: str = Form("")):
        if check_key not in READINESS_CHECKS or status not in ("done", "not_done") or not note.strip():
            return RedirectResponse("/readiness?error=" + quote("Add a short note saying what you confirmed."), status_code=303)
        conn, _ = ctx()
        try:
            with transaction(conn):
                conn.execute("INSERT INTO readiness_checks (recorded_at, check_key, status, note) VALUES (?, ?, ?, ?)",
                             (clock(), check_key, status, note.strip()))
            return RedirectResponse("/readiness", status_code=303)
        finally:
            conn.close()

    @app.post("/readiness/selling")
    def selling_log(item: str = Form(...), platform: str = Form(...), listing_minutes: str = Form(...),
                    selling_minutes: str = Form(...), sold: str = Form("1"), price: str = Form("")):
        conn, _ = ctx()
        try:
            try:
                row = (clock(), item.strip(), platform.strip(), float(listing_minutes), float(selling_minutes),
                       1 if sold == "1" else 0, parse_dollars(price) if price.strip() else None)
                if not row[1] or row[3] < 0 or row[4] < 0:
                    raise ValueError
            except ValueError:
                return RedirectResponse("/readiness?error=" + quote("Check the minutes and price."), status_code=303)
            with transaction(conn):
                conn.execute("INSERT INTO selling_time_log (recorded_at, item, platform, listing_minutes, "
                             "selling_minutes, sold, price_cents) VALUES (?, ?, ?, ?, ?, ?, ?)", row)
            return RedirectResponse("/readiness#selling", status_code=303)
        finally:
            conn.close()

    @app.get("/assumptions", response_class=HTMLResponse)
    def assumptions_page(request: Request, error: str = "", saved: str = ""):
        conn, cfg = ctx()
        try:
            set_id, overrides = assumptions_mod.current_overrides(conn)
            history = conn.execute("SELECT id, created_at, note FROM assumption_sets ORDER BY id DESC LIMIT 10").fetchall()
            return render(request, "assumptions.html", rows=assumptions_mod.panel_rows(cfg, overrides),
                          set_id=set_id, history=history, STATUSES=STATUSES, error=error, saved=saved)
        finally:
            conn.close()

    @app.post("/assumptions")
    async def assumptions_save(request: Request):
        form = await request.form()
        conn, _ = ctx()
        try:
            _, overrides = assumptions_mod.current_overrides(conn)
            cfg_now = assumptions_mod.apply_overrides(base_cfg, overrides)
            changes = {}
            for e in assumptions_mod.EDITABLE:
                val = str(form.get(f"v::{e.path}", ""))
                status = str(form.get(f"s::{e.path}", ""))
                source = str(form.get(f"n::{e.path}", "")).strip()
                cur = assumptions_mod.leaf(cfg_now, e.path)
                if val != assumptions_mod.format_value(e.kind, cur["value"]) or status != cur["status"] or source:
                    changes[e.path] = (val, status, source)
            try:
                sid = assumptions_mod.save(conn, base_cfg, changes, str(form.get("note", "")), now=clock())
            except (ValueError, KeyError) as e:
                return RedirectResponse(f"/assumptions?error={quote(str(e))}", status_code=303)
            return RedirectResponse(f"/assumptions?saved={sid or ''}", status_code=303)
        finally:
            conn.close()

    @app.get("/sources", response_class=HTMLResponse)
    def sources_page(request: Request, error: str = ""):
        conn, cfg = ctx()
        try:
            pols = {k: platforms.capture_policy(conn, cfg.sources, k) for k in cfg.sources}
            events = conn.execute("SELECT * FROM source_policy_events ORDER BY id DESC").fetchall()
            return render(request, "sources.html", sources=cfg.sources, pols=pols, events=events, error=error)
        finally:
            conn.close()

    @app.post("/sources/{key}/policy")
    def set_source_policy(key: str, policy: str = Form(...), basis: str = Form(...), note: str = Form("")):
        conn, cfg = ctx()
        try:
            try:
                with transaction(conn):
                    platforms.set_policy(conn, cfg.sources, key, policy, basis, note, clock())
            except (ValueError, KeyError) as e:
                return RedirectResponse(f"/sources?error={quote(str(e))}", status_code=303)
            return RedirectResponse("/sources", status_code=303)
        finally:
            conn.close()

    return app
