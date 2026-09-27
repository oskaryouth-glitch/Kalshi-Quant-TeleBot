from decimal import Decimal as D
import pytest
from sarb.orderbook import parse_orderbook, walk, displayed_depth, OrderBookFormatError, Level


FP = {"orderbook_fp": {"yes_dollars": [["0.3000", "5.00"], ["0.4200", "10.00"], ["0.4100", "3.00"]],
                       "no_dollars": [["0.5500", "7.00"], ["0.5000", "20.00"]]}}
LEGACY = {"orderbook": {"yes": [[30, 5], [42, 10], [41, 3]], "no": [[55, 7], [50, 20]]}}


@pytest.mark.parametrize("body", [FP, LEGACY])
def test_parse_and_derive_asks(body):
    ob = parse_orderbook("T", body)
    assert [l.price for l in ob.yes_bids] == [D("0.42"), D("0.41"), D("0.30")]
    assert ob.best_bid("yes").price == D("0.42")
    # yes ask = 1 - best no bid
    assert ob.best_ask("yes") == Level(D("0.45"), D(7))
    assert ob.best_ask("no") == Level(D("0.58"), D(10))
    assert [l.price for l in ob.asks("yes")] == [D("0.45"), D("0.50")]
    assert not ob.is_crossed()


def test_duplicates_aggregated_and_zero_dropped():
    ob = parse_orderbook("T", {"orderbook_fp": {"yes_dollars": [["0.4", "1"], ["0.4", "2"], ["0.3", "0"]], "no_dollars": []}})
    assert ob.yes_bids == (Level(D("0.4"), D(3)),)
    assert ob.best_ask("yes") is None


def test_empty_and_null_sides():
    ob = parse_orderbook("T", {"orderbook": {"yes": None, "no": None}})
    assert ob.yes_bids == () and ob.no_bids == ()


@pytest.mark.parametrize("bad", [{}, {"orderbook_fp": {"yes_dollars": [["1.2", "1"]]}}, {"orderbook": {"yes": [[0, 1]]}},
                                 {"orderbook_fp": {"yes_dollars": [["0.5"]]}}, []])
def test_bad_formats(bad):
    with pytest.raises(OrderBookFormatError):
        parse_orderbook("T", bad)


def test_crossed_and_locked_detection():
    ob = parse_orderbook("T", {"orderbook_fp": {"yes_dollars": [["0.6", "1"]], "no_dollars": [["0.5", "1"]]}})
    assert ob.is_crossed()
    locked = parse_orderbook("T", {"orderbook_fp": {"yes_dollars": [["0.6", "1"]], "no_dollars": [["0.4", "1"]]}})
    assert locked.is_crossed()
    ok = parse_orderbook("T", {"orderbook_fp": {"yes_dollars": [["0.6", "1"]], "no_dollars": [["0.39", "1"]]}})
    assert not ok.is_crossed()


def test_walk_depth():
    ob = parse_orderbook("T", FP)
    asks = ob.asks("yes")   # 7 @ .45, 20 @ .50
    f = walk(asks, D(10))
    assert f.complete and f.filled == 10
    assert f.cost == D(7) * D("0.45") + D(3) * D("0.50")
    assert f.fills == (Level(D("0.45"), D(7)), Level(D("0.50"), D(3)))
    assert f.worst_price == D("0.50")
    g = walk(asks, D(100))
    assert not g.complete and g.filled == 27 == displayed_depth(asks)


def test_fractional_counts_and_subpenny():
    ob = parse_orderbook("T", {"orderbook_fp": {"yes_dollars": [], "no_dollars": [["0.5550", "1.50"]]}})
    f = walk(ob.asks("yes"), D("1.25"))
    assert f.fills == (Level(D("0.4450"), D("1.25")),)
