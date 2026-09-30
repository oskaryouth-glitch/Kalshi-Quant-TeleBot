"""Configuration loading.

Config values are written as ``{value, status, source}`` leaves (see
config/markets.yaml). ``Assumptions`` resolves them to plain values while
remembering which non-VERIFIED assumptions exist, so every decision can record
exactly which unverified numbers it depended on.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

STATUSES = ("VERIFIED", "SOURCED", "UNVERIFIED", "GUESS", "USER")
# How each status is shown to the operator.
STATUS_LABELS = {
    "VERIFIED": "Verified first-hand",
    "SOURCED": "Sourced, not first-hand",
    "UNVERIFIED": "Unverified",
    "GUESS": "Unverified (guess)",
    "USER": "Your assumption",
}


def _is_leaf(node: Any) -> bool:
    return isinstance(node, dict) and "value" in node and "status" in node


def _check(node: Any, path: str) -> None:
    if _is_leaf(node):
        if node["status"] not in STATUSES:
            raise ValueError(f"{path}: unknown assumption status {node['status']!r}")
    elif isinstance(node, dict):
        for k, v in node.items():
            _check(v, f"{path}.{k}" if path else str(k))


@dataclass(frozen=True)
class Assumptions:
    tree: dict

    def __post_init__(self) -> None:
        _check(self.tree, "")

    def get(self, *path: str) -> Any:
        node: Any = self.tree
        for p in path:
            node = node[p]
        return node["value"] if _is_leaf(node) else node

    def section(self, *path: str) -> "Assumptions":
        node: Any = self.tree
        for p in path:
            node = node[p]
        return Assumptions(node)

    def plain(self) -> Any:
        def strip(n: Any) -> Any:
            if _is_leaf(n):
                return n["value"]
            if isinstance(n, dict):
                return {k: strip(v) for k, v in n.items()}
            return n

        return strip(self.tree)

    def unverified(self, prefix: str = "") -> list[dict]:
        out: list[dict] = []

        def walk(n: Any, path: str) -> None:
            if _is_leaf(n):
                if n["status"] != "VERIFIED":
                    out.append({"path": path, "status": n["status"], "value": n["value"]})
            elif isinstance(n, dict):
                for k, v in n.items():
                    walk(v, f"{path}.{k}" if path else str(k))

        walk(self.tree, prefix)
        return out


@dataclass(frozen=True)
class Paths:
    home: Path

    @property
    def config_dir(self) -> Path:
        return self.home / "config"

    @property
    def data_dir(self) -> Path:
        return self.home / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "lockerlab.sqlite3"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"


def default_paths() -> Paths:
    return Paths(Path(os.environ.get("LOCKERLAB_HOME", Path.cwd())).resolve())


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class Config:
    sources: dict
    markets: dict[str, Assumptions]
    underwriting: Assumptions

    @classmethod
    def load(cls, config_dir: Path) -> "Config":
        markets = load_yaml(config_dir / "markets.yaml")
        return cls(
            sources=load_yaml(config_dir / "sources.yaml"),
            markets={k: Assumptions(v) for k, v in markets.items()},
            underwriting=Assumptions(load_yaml(config_dir / "underwriting.yaml")),
        )

    def market(self, key: str) -> Assumptions:
        if key not in self.markets:
            raise KeyError(f"unknown market {key!r}; known: {sorted(self.markets)}")
        return self.markets[key]


def canonical_json(obj: Any) -> str:
    """Deterministic JSON for hashing and storage."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
