# MeshCore BLE Bot (Python)

A Python bot that connects to a MeshCore companion node over BLE and auto-responds to channel messages.

## What it does

- Connects to companion node via the `meshcore` Python package.
- Subscribes to MeshCore channel-message events.
- Applies per-channel command rules (e.g. `!ping` -> `pong`).
- Sends replies with MeshCore channel send commands.
- Reconnects automatically if BLE disconnects.

## Channel rules

Use channel names as keys in `channel_rules`, e.g. `"General"`, `"Ops"`.
Incoming MeshCore events provide `channel_idx`; on connect, the bot queries the
device for channel metadata and maps `channel_idx -> channel_name` using
`send_device_query()` + `get_channel(idx)`.
`"*"` remains a fallback for messages that don't match a configured channel key.

## Setup

1. Create and activate a venv:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the BLE setup helper (scan nearby devices, test pairing/connection, read device PIN if available, and generate config):

```powershell
python -m meshcore_bot.setup_ble
```

If you install the package, you can also run:

```powershell
meshcore-setup
```

4. (Optional) Copy/edit config manually instead:

```powershell
Copy-Item config\bot.example.yaml config\bot.yaml
```

Update BLE address/name and (optional) PIN in `config/bot.yaml`.

## Run

```powershell
python -m meshcore_bot.main --config config/bot.yaml --log-level INFO
```

## Notes

- On Windows, BLE requires Bluetooth hardware and permissions.
- Prefer `device_address` for stable reconnect behavior.
- Keep your bot's own sender ID in `ignore_senders` to avoid response loops.
