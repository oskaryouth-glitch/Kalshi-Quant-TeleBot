"""Unit economics and maximum-bid solver. Pure functions, integer cents.

Definitions (also in docs/UNIT_ECONOMICS.md):

  acquisition      = bid + buyer premium + sales tax
  out_of_pocket    = acquisition + transport + disposal + storage + packing
                     + expected cleaning-deposit forfeit + other
  selling_costs    = platform/payment fees + returns/refunds + risk reserve
  profit_before_labor = gross proceeds - out_of_pocket - selling_costs
  net_profit       = profit_before_labor - labor_hours * labor_rate
  cash_invested    = acquisition + transport + disposal + storage + packing + other
  roi              = net_profit / cash_invested
  cash_required    = acquisition + refundable cleaning deposit + transport + disposal
                     (what must be on hand in the first 72 hours)

"gross proceeds" is the expected total sale price of what actually sells
(sell-through is already applied by the valuation step), before any fees.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .money import cost_cents


@dataclass(frozen=True)
class CostPolicy:
    buyer_premium_rate: float
    buyer_premium_min_cents: int
    sales_tax_rate: float
    tax_applies_to_premium: bool = True  # conservative default
    resale_exempt: bool = False
    cleaning_deposit_cents: int = 0
    cleaning_deposit_forfeit_prob: float = 0.0
    selling_fee_rate: float = 0.0
    per_order_fee_cents: int = 0
    packing_cost_per_shipped_order_cents: int = 0
    shipped_order_share: float = 0.0
    returns_rate: float = 0.0
    risk_reserve_rate: float = 0.0
    labor_rate_cents_per_hour: int = 0

    def __post_init__(self) -> None:
        for name in (
            "buyer_premium_rate", "sales_tax_rate", "cleaning_deposit_forfeit_prob",
            "selling_fee_rate", "shipped_order_share", "returns_rate", "risk_reserve_rate",
        ):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name}={v} outside [0, 1]")
        for name in (
            "buyer_premium_min_cents", "cleaning_deposit_cents", "per_order_fee_cents",
            "packing_cost_per_shipped_order_cents", "labor_rate_cents_per_hour",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")


@dataclass(frozen=True)
class Scenario:
    name: str
    gross_proceeds_cents: int
    n_orders: int
    transport_cost_cents: int
    disposal_cost_cents: int
    labor_hours: float
    retained_cuft: float
    storage_cost_cents: int = 0
    other_costs_cents: int = 0

    def __post_init__(self) -> None:
        if self.gross_proceeds_cents < 0 or self.n_orders < 0 or self.labor_hours < 0:
            raise ValueError(f"scenario {self.name}: negative quantity")


@dataclass(frozen=True)
class Acquisition:
    bid_cents: int
    premium_cents: int
    tax_cents: int

    @property
    def total_cents(self) -> int:
        return self.bid_cents + self.premium_cents + self.tax_cents


def acquisition_cost(bid_cents: int, p: CostPolicy) -> Acquisition:
    if bid_cents < 0:
        raise ValueError("bid must be >= 0")
    premium = 0
    if bid_cents > 0:
        premium = max(cost_cents(bid_cents * p.buyer_premium_rate), p.buyer_premium_min_cents)
    base = bid_cents + (premium if p.tax_applies_to_premium else 0)
    tax = 0 if p.resale_exempt else cost_cents(base * p.sales_tax_rate)
    return Acquisition(bid_cents, premium, tax)


@dataclass(frozen=True)
class Evaluation:
    scenario: str
    bid_cents: int
    gross_proceeds_cents: int
    acquisition: Acquisition
    transport_cents: int
    disposal_cents: int
    storage_cents: int
    packing_cents: int
    deposit_expected_loss_cents: int
    other_cents: int
    selling_fees_cents: int
    returns_cents: int
    risk_reserve_cents: int
    labor_hours: float
    labor_cost_cents: int
    retained_cuft: float
    cash_required_cents: int

    @property
    def out_of_pocket_cents(self) -> int:
        return (
            self.acquisition.total_cents + self.transport_cents + self.disposal_cents
            + self.storage_cents + self.packing_cents + self.deposit_expected_loss_cents
            + self.other_cents
        )

    @property
    def selling_costs_cents(self) -> int:
        return self.selling_fees_cents + self.returns_cents + self.risk_reserve_cents

    @property
    def all_in_cost_cents(self) -> int:
        """Every cost including valued labor."""
        return self.out_of_pocket_cents + self.selling_costs_cents + self.labor_cost_cents

    @property
    def profit_before_labor_cents(self) -> int:
        return self.gross_proceeds_cents - self.out_of_pocket_cents - self.selling_costs_cents

    @property
    def net_profit_cents(self) -> int:
        return self.profit_before_labor_cents - self.labor_cost_cents

    @property
    def cash_invested_cents(self) -> int:
        return (
            self.acquisition.total_cents + self.transport_cents + self.disposal_cents
            + self.storage_cents + self.packing_cents + self.other_cents
        )

    @property
    def roi(self) -> float | None:
        inv = self.cash_invested_cents
        return None if inv <= 0 else self.net_profit_cents / inv

    @property
    def profit_per_hour_before_labor_cents(self) -> float | None:
        return None if self.labor_hours <= 0 else self.profit_before_labor_cents / self.labor_hours

    @property
    def net_profit_per_retained_cuft_cents(self) -> float | None:
        return None if self.retained_cuft <= 0 else self.net_profit_cents / self.retained_cuft

    @property
    def gross_per_retained_cuft_cents(self) -> float | None:
        return None if self.retained_cuft <= 0 else self.gross_proceeds_cents / self.retained_cuft

    def summary(self) -> dict:
        d = asdict(self)
        d["acquisition"]["total_cents"] = self.acquisition.total_cents
        d.update(
            out_of_pocket_cents=self.out_of_pocket_cents,
            selling_costs_cents=self.selling_costs_cents,
            all_in_cost_cents=self.all_in_cost_cents,
            profit_before_labor_cents=self.profit_before_labor_cents,
            net_profit_cents=self.net_profit_cents,
            cash_invested_cents=self.cash_invested_cents,
            roi=self.roi,
            profit_per_hour_before_labor_cents=self.profit_per_hour_before_labor_cents,
            net_profit_per_retained_cuft_cents=self.net_profit_per_retained_cuft_cents,
            gross_per_retained_cuft_cents=self.gross_per_retained_cuft_cents,
        )
        return d


def evaluate(bid_cents: int, s: Scenario, p: CostPolicy) -> Evaluation:
    gross = s.gross_proceeds_cents
    acq = acquisition_cost(bid_cents, p)
    return Evaluation(
        scenario=s.name,
        bid_cents=bid_cents,
        gross_proceeds_cents=gross,
        acquisition=acq,
        transport_cents=s.transport_cost_cents,
        disposal_cents=s.disposal_cost_cents,
        storage_cents=s.storage_cost_cents,
        packing_cents=cost_cents(
            s.n_orders * p.shipped_order_share * p.packing_cost_per_shipped_order_cents
        ),
        deposit_expected_loss_cents=cost_cents(
            p.cleaning_deposit_cents * p.cleaning_deposit_forfeit_prob
        ),
        other_cents=s.other_costs_cents,
        selling_fees_cents=cost_cents(gross * p.selling_fee_rate + s.n_orders * p.per_order_fee_cents),
        returns_cents=cost_cents(gross * p.returns_rate),
        risk_reserve_cents=cost_cents(gross * p.risk_reserve_rate),
        labor_hours=s.labor_hours,
        labor_cost_cents=cost_cents(s.labor_hours * p.labor_rate_cents_per_hour),
        retained_cuft=s.retained_cuft,
        cash_required_cents=(
            acq.total_cents + p.cleaning_deposit_cents
            + s.transport_cost_cents + s.disposal_cost_cents
        ),
    )


@dataclass(frozen=True)
class MarginRules:
    """Margin-of-safety constraints. The max bid must satisfy every one."""

    min_expected_profit_cents: int
    target_roi: float
    max_low_case_loss_cents: int
    min_profit_per_hour_before_labor_cents: int
    bankroll_cents: int


def constraint_failures(base: Evaluation, low: Evaluation, r: MarginRules) -> list[str]:
    """Names of violated constraints. Each is monotone non-increasing in the
    bid (it only gets harder to satisfy as the bid rises), which is what makes
    binary search in ``max_bid`` valid."""
    fails = []
    if base.net_profit_cents < r.min_expected_profit_cents:
        fails.append("min_expected_profit")
    # net >= roi * invested, written without division so it is monotone even
    # when invested is tiny
    if base.net_profit_cents < r.target_roi * base.cash_invested_cents:
        fails.append("target_roi")
    # Downside is measured in cash (before valuing labor): it limits real
    # dollars lost. The value of time is enforced by the base-case rules.
    if low.profit_before_labor_cents < -r.max_low_case_loss_cents:
        fails.append("max_low_case_loss")
    if base.profit_before_labor_cents < r.min_profit_per_hour_before_labor_cents * base.labor_hours:
        fails.append("min_profit_per_hour")
    if base.cash_required_cents > r.bankroll_cents:
        fails.append("bankroll")
    return fails


@dataclass(frozen=True)
class MaxBidResult:
    max_bid_cents: int | None  # None: no bid (not even $0) satisfies the rules
    binding_constraints: list[str] = field(default_factory=list)
    base_at_max: Evaluation | None = None
    low_at_max: Evaluation | None = None
    high_at_max: Evaluation | None = None


def max_bid(
    scenarios: dict[str, Scenario], p: CostPolicy, r: MarginRules, step_cents: int = 100
) -> MaxBidResult:
    """Largest bid (a multiple of ``step_cents``, default whole dollars) at
    which every margin-of-safety constraint holds in the base and low cases.

    ``binding_constraints`` lists what fails one step above the max bid (or at
    $0 when no bid works), i.e. why the max is not higher.
    """
    base_s, low_s, high_s = scenarios["base"], scenarios["low"], scenarios["high"]

    def fails(b: int) -> list[str]:
        return constraint_failures(evaluate(b, base_s, p), evaluate(b, low_s, p), r)

    at_zero = fails(0)
    if at_zero:
        return MaxBidResult(None, at_zero)
    # Bidding more than the high-case gross can never be profitable, so this
    # upper bound always fails; guard anyway in case of a zero-gross scenario.
    lo, hi = 0, max(high_s.gross_proceeds_cents, base_s.gross_proceeds_cents) // step_cents + 1
    while not fails(hi * step_cents) and hi < 10**9:
        hi *= 2
    while hi - lo > 1:  # invariant: lo ok, hi fails
        mid = (lo + hi) // 2
        if fails(mid * step_cents):
            hi = mid
        else:
            lo = mid
    b = lo * step_cents
    return MaxBidResult(
        max_bid_cents=b,
        binding_constraints=fails(hi * step_cents),
        base_at_max=evaluate(b, base_s, p),
        low_at_max=evaluate(b, low_s, p),
        high_at_max=evaluate(b, high_s, p),
    )


def increment_for(price_cents: int, schedule: list[list[int | None]]) -> int:
    """Bid increment for a price, given [[upper_bound_exclusive|None, inc], ...]."""
    for upper, inc in schedule:
        if upper is None or price_cents < upper:
            return int(inc)
    raise ValueError("increment schedule must end with an open (null) bound")
