"""Resale module SKELETON (Phase 7+). Interfaces and record types only.

Tables: migrations/003_resale_skeleton.sql. Nothing here is wired into the app
yet, by design: it waits until paper evidence justifies a real purchase.

Principles fixed now so later code can't drift:
  * Everything is an append-only event; current state is the latest event.
  * Money in these records is REALIZED (receipts, actual sale prices).
  * A real acquisition is created by a person after buying; LockerLab never
    bids or buys. It links to the paper decision made BEFORE bidding
    (pre-registration), so predicted vs realized can be compared honestly.
  * Items start with sensitive_review = 1 and can't be listed until a person
    clears them (documents, drives, IDs, medication, weapons: see
    docs/ASSUMPTIONS_AND_RISKS.md §3).
  * Photos: originals are kept; a derived photo names its original and its
    transforms, and transforms that alter apparent condition are banned.
  * Listing channels PREPARE copy for a human to post. No channel posts,
    messages buyers, or accepts offers. eBay API posting, if ever added, will
    require explicit per-listing human approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

ALLOWED_PHOTO_TRANSFORMS = frozenset({"crop", "rotate", "straighten", "white_balance", "exposure",
                                      "background_neutralize", "resize"})
BANNED_PHOTO_TRANSFORMS = frozenset({"inpaint", "retouch", "blemish_removal", "object_removal", "generative_fill"})
GRADES = {"A": "high value, sell individually", "B": "medium value, sell individually", "C": "bundle",
          "D": "donate / recycle / dispose"}


@dataclass(frozen=True)
class RealAcquisition:
    auction_id: int
    winning_bid_cents: int
    premium_cents: int
    tax_cents: int
    pre_registered_decision_id: int | None
    deposit_cents: int = 0
    note: str = ""


@dataclass(frozen=True)
class Item:
    acquisition_id: int
    description: str
    category: str | None = None
    brand: str | None = None
    model: str | None = None
    condition: str | None = None
    grade: str | None = None
    footprint_cuft: float | None = None
    estimated_value_cents: int | None = None
    sensitive_review: bool = True  # must be cleared by a person before listing


@dataclass(frozen=True)
class PhotoDerivation:
    original_photo_id: int
    transforms: tuple[str, ...]

    def __post_init__(self) -> None:
        bad = set(self.transforms) & BANNED_PHOTO_TRANSFORMS
        unknown = set(self.transforms) - ALLOWED_PHOTO_TRANSFORMS - BANNED_PHOTO_TRANSFORMS
        if bad:
            raise ValueError(f"transforms that change apparent condition are not allowed: {sorted(bad)}")
        if unknown:
            raise ValueError(f"unknown transforms {sorted(unknown)}")


@dataclass(frozen=True)
class ListingDraft:
    platform: str
    title: str
    description: str
    ask_cents: int
    quick_sale_cents: int | None
    floor_cents: int | None
    category: str | None = None
    keywords: tuple[str, ...] = ()
    photo_ids: tuple[int, ...] = ()
    pickup_or_shipping: str = "local pickup"
    warnings: list[str] = field(default_factory=list)


class ListingChannel(Protocol):
    """Prepares a listing for a human to post by hand. Deliberately has no
    post/publish/message method."""

    platform: str

    def prepare(self, item: Item, ask_cents: int) -> ListingDraft: ...


class SaleRecorder(Protocol):
    def record_sale(self, item_id: int, price_cents: int, fees_cents: int, platform: str,
                    sold_at: str, selling_minutes: float | None) -> int: ...
