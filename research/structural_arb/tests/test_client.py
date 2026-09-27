import ast, inspect, os, re
import pytest
from sarb import client as C


class FakeResp:
    status_code = 200
    text = "{}"
    def json(self): return {"ok": True}


class FakeSession:
    def __init__(self):
        self.headers = {"Authorization": "Bearer SECRET", "KALSHI-ACCESS-KEY": "k", "User-Agent": "x"}
        self.calls = []
    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        return FakeResp()


def test_only_get_and_no_auth_headers():
    s = FakeSession()
    c = C.PublicClient(session=s, per_second=1000)
    r = c.orderbook("KXTEST-26SEP27-T50")
    assert s.calls[0][0] == "GET"
    assert "authorization" not in {h.lower() for h in s.headers}
    assert "kalshi-access-key" not in {h.lower() for h in s.headers}
    assert "Authorization" not in s.calls[0][2]["headers"]
    assert r.sent_utc_ns <= r.recv_utc_ns and r.latency_ns >= 0


@pytest.mark.parametrize("path", ["/portfolio/orders", "/portfolio/balance", "/markets/X/../../portfolio/orders",
                                  "/portfolio/positions", "/communications/rfqs", "https://evil"])
def test_forbidden_paths(path):
    with pytest.raises(C.ForbiddenRequest):
        C.check_path(path)


@pytest.mark.parametrize("path", ["/events", "/markets/KXHIGHNY-26SEP27-B75.5/orderbook", "/series/KXHIGHNY",
                                  "/series/fee_changes", "/exchange/status"])
def test_allowed_paths(path):
    C.check_path(path)


def test_package_has_no_write_verbs_or_credentials():
    """Static guard: no module in sarb issues non-GET requests, touches order endpoints,
    or reads credentials."""
    pkg = os.path.dirname(C.__file__)
    for fn in os.listdir(pkg):
        if not fn.endswith(".py"):
            continue
        src = open(os.path.join(pkg, fn)).read()
        assert not re.search(r"\.(post|put|delete|patch)\(", src), fn
        assert not re.search(r"request\(\s*['\"](POST|PUT|DELETE|PATCH)", src), fn
        assert "KALSHI_API_KEY" not in src and "private_key" not in src.lower(), fn
        assert "/portfolio" not in src, fn
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                for n in names:
                    assert not n.startswith(("src", "trader", "kalshi_api", "telegram")), (fn, n)


def test_global_cooldown_after_429():
    import time as _t
    from sarb.client import _RateLimiter
    rl = _RateLimiter(1000, 10)
    rl.feedback(429)
    t = _t.monotonic(); rl.wait()
    assert _t.monotonic() - t >= 0.9 and rl.cooldowns == 1
    rl.feedback(429)
    assert rl._backoff == 4.0
    for _ in range(20):
        rl.feedback(200)
    assert rl._backoff == 1.0
