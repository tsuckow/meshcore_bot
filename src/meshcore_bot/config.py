from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class BleConfig:
    device_name: str | None
    device_address: str | None
    pin: str | None = None
    scan_timeout_s: float = 10.0
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 0


@dataclass(slots=True)
class BotConfig:
    ble: BleConfig
    channel_rules: dict[str, dict[str, str]]
    command_prefix: str = "!"
    ignore_senders: set[str] | None = None


def _must_get(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"Missing required config key: {key}")
    return data[key]


def load_config(path: str | Path) -> BotConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config must be a YAML mapping")

    ble_raw = _must_get(raw, "ble")
    if not isinstance(ble_raw, dict):
        raise ValueError("'ble' config must be a mapping")

    channel_rules = raw.get("channel_rules", {})
    if not isinstance(channel_rules, dict):
        raise ValueError("'channel_rules' must be a mapping")

    ignore_senders_raw = raw.get("ignore_senders")
    ignore_senders = set(ignore_senders_raw) if isinstance(ignore_senders_raw, list) else None

    return BotConfig(
        ble=BleConfig(
            device_name=ble_raw.get("device_name"),
            device_address=ble_raw.get("device_address"),
            pin=ble_raw.get("pin"),
            scan_timeout_s=float(ble_raw.get("scan_timeout_s", 10.0)),
            auto_reconnect=bool(ble_raw.get("auto_reconnect", True)),
            max_reconnect_attempts=int(ble_raw.get("max_reconnect_attempts", 0)),
        ),
        channel_rules=channel_rules,
        command_prefix=str(raw.get("command_prefix", "!")),
        ignore_senders=ignore_senders,
    )
