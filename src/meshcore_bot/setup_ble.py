from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from meshcore import EventType, MeshCore
from meshcore.ble_cx import BLEAK_AVAILABLE, BleakScanner
import yaml


def _ask(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    if value:
        return value
    return default or ""


def _ask_yes_no(text: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    value = input(f"{text} ({hint}): ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def _select_index(max_count: int, prompt: str, allow_skip: bool = False) -> int | None:
    while True:
        raw = input(prompt).strip().lower()
        if allow_skip and raw in {"", "s", "skip"}:
            return None
        if raw.isdigit():
            index = int(raw)
            if 0 <= index < max_count:
                return index
        print("Invalid selection. Try again.")


async def _discover_devices(scan_timeout_s: float) -> list[Any]:
    if not BLEAK_AVAILABLE:
        raise RuntimeError("BLE scanning is unavailable; ensure meshcore BLE dependencies are installed")

    print(f"Scanning for BLE devices for {scan_timeout_s:.0f}s...")
    devices = await BleakScanner.discover(timeout=scan_timeout_s)
    deduped: dict[str, Any] = {}
    for device in devices:
        deduped[device.address] = device
    sorted_devices = sorted(
        deduped.values(),
        key=lambda device: ((device.name or "").lower(), device.address.lower()),
    )
    return sorted_devices


async def _test_connection(address: str, pin: str | None) -> str | None:
    mesh = await MeshCore.create_ble(address=address, pin=pin)
    if mesh is None:
        raise RuntimeError("Could not connect to MeshCore node")

    try:
        info_event = await mesh.commands.send_device_query()
        if info_event.type == EventType.ERROR:
            print(f"Connected, but device query returned error: {info_event.payload}")
            return None

        payload = info_event.payload if isinstance(info_event.payload, dict) else {}
        ble_pin = payload.get("ble_pin")
        if ble_pin is not None:
            return str(ble_pin)
        return None
    finally:
        await mesh.disconnect()


async def _connect_and_test(
    selected_device,
    require_pairing: bool,
    pin_hint: str | None,
) -> str | None:
    print(f"\nConnecting to {selected_device.name or 'Unknown'} ({selected_device.address})...")
    if require_pairing:
        if pin_hint:
            print(
                "Pairing requested. If Windows prompts for a passkey/PIN, use this value:",
                pin_hint,
            )
        else:
            print("Pairing requested. Complete the OS Bluetooth prompt if it appears.")

    discovered_pin = await _test_connection(selected_device.address, pin_hint if require_pairing else None)
    print("Connection test successful")
    if discovered_pin:
        print(f"Node reports BLE PIN: {discovered_pin}")
    else:
        print("Node did not report a BLE PIN in device info")
    return discovered_pin


def _build_config(
    device,
    pin: str | None,
    scan_timeout_s: float,
) -> dict:
    return {
        "ble": {
            "device_address": device.address,
            "device_name": device.name,
            "pin": pin,
            "scan_timeout_s": scan_timeout_s,
            "auto_reconnect": True,
            "max_reconnect_attempts": 0,
        },
        "command_prefix": "!",
        "ignore_senders": ["my-bot-node-id"],
        "channel_rules": {
            "0": {
                "ping": "pong",
                "status": "MeshCore bot online",
            },
            "1": {
                "help": "Commands: !help, !ping",
            },
            "*": {
                "echo": "I hear you",
            },
        },
    }


async def run_setup() -> None:
    print("MeshCore BLE setup helper\n")
    scan_timeout_s = float(_ask("Scan timeout in seconds", "8"))
    devices = await _discover_devices(scan_timeout_s)
    if not devices:
        raise RuntimeError("No BLE devices discovered")

    print("\nNearby BLE devices:")
    for index, device in enumerate(devices):
        print(f"  [{index}] {device.name or 'Unknown'}  ({device.address})")

    selected_index = _select_index(len(devices), "Select device index: ")
    assert selected_index is not None
    selected_device = devices[selected_index]

    require_pairing = _ask_yes_no("Attempt pairing before test connection?", default=False)
    pin_hint = None
    if require_pairing:
        pin_hint = _ask("Enter PIN/passkey hint if your device shows one (optional)", "") or None

    discovered_pin = await _connect_and_test(
        selected_device,
        require_pairing=require_pairing,
        pin_hint=pin_hint,
    )

    out_path = Path(_ask("Config output path", "config/bot.yaml"))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    config_data = _build_config(
        selected_device,
        pin=discovered_pin or pin_hint,
        scan_timeout_s=scan_timeout_s,
    )

    out_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    print(f"\nWrote config to {out_path}")
    print("Next: run `python -m meshcore_bot.main --config config/bot.yaml --log-level INFO`")


def main() -> None:
    asyncio.run(run_setup())


if __name__ == "__main__":
    main()
