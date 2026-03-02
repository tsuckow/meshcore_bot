from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from meshcore import EventType, MeshCore

from .config import BleConfig
from .models import ChannelMessage, OutboundMessage

_logger = logging.getLogger(__name__)


class MeshCoreBleClient:
    """MeshCore package-backed client for a companion node over BLE."""

    def __init__(self, config: BleConfig) -> None:
        self._config = config
        self._mesh: MeshCore | None = None
        self._queue: asyncio.Queue[ChannelMessage] | None = None
        self._subscription = None
        self._auto_fetch_started = False
        self._channel_name_by_index: dict[str, str] = {}

    async def _load_channel_name_map(self) -> None:
        if not self._mesh:
            return

        channel_map: dict[str, str] = {}

        info_event = await self._mesh.commands.send_device_query()
        if info_event.type == EventType.ERROR:
            _logger.warning("Failed to query device info for channel map: %s", info_event.payload)
            self._channel_name_by_index = channel_map
            return

        info_payload = info_event.payload if isinstance(info_event.payload, dict) else {}
        max_channels_raw = info_payload.get("max_channels", 0)
        try:
            max_channels = int(max_channels_raw)
        except (TypeError, ValueError):
            max_channels = 0

        for channel_idx in range(max_channels):
            channel_event = await self._mesh.commands.get_channel(channel_idx)
            if channel_event.type == EventType.ERROR:
                continue

            payload = channel_event.payload if isinstance(channel_event.payload, dict) else {}
            idx_raw = payload.get("channel_idx", channel_idx)
            try:
                idx = str(int(idx_raw))
            except (TypeError, ValueError):
                idx = str(channel_idx)

            name_raw = payload.get("channel_name")
            if name_raw is None:
                continue

            name = str(name_raw).strip()
            if not name:
                continue

            channel_map[idx] = name

        self._channel_name_by_index = channel_map
        if channel_map:
            _logger.info("Loaded channel map from device: %s", channel_map)
        else:
            _logger.warning("No channel names returned from device; rules will use index or '*' fallback")

    async def connect(self) -> None:
        _logger.info("Connecting to companion node via meshcore")
        self._mesh = await MeshCore.create_ble(
            address=self._config.device_address,
            pin=self._config.pin,
            auto_reconnect=self._config.auto_reconnect,
            max_reconnect_attempts=self._config.max_reconnect_attempts,
            debug=True
        )
        if self._mesh is None:
            raise RuntimeError("Failed to connect to MeshCore node")

        self._queue = asyncio.Queue()
        await self._load_channel_name_map()

        async def on_channel_message(event) -> None:
            payload = event.payload if isinstance(event.payload, dict) else {}
            raw_text = str(payload.get("text", ""))
            sender = str(payload.get("pubkey_prefix", "unknown"))
            text = raw_text
            channel_idx = payload.get("channel_idx")
            channel_idx_str = str(channel_idx if channel_idx is not None else "")
            channel_name = self._channel_name_by_index.get(channel_idx_str)

            if ": " in raw_text:
                parsed_sender, parsed_text = raw_text.split(": ", 1)
                if parsed_sender.strip():
                    sender = parsed_sender.strip()
                    text = parsed_text

            message = ChannelMessage(
                channel=channel_idx_str,
                channel_name=channel_name,
                sender=sender,
                text=text,
                message_id=str(payload.get("sender_timestamp")) if payload.get("sender_timestamp") is not None else None,
            )
            if self._queue is not None:
                self._queue.put_nowait(message)

        self._subscription = self._mesh.subscribe(EventType.CHANNEL_MSG_RECV, on_channel_message)
        await self._mesh.start_auto_message_fetching()
        self._auto_fetch_started = True
        _logger.info("MeshCore connection established")

    async def disconnect(self) -> None:
        if not self._mesh:
            return
        if self._auto_fetch_started:
            await self._mesh.stop_auto_message_fetching()
            self._auto_fetch_started = False
        if self._subscription is not None:
            self._mesh.unsubscribe(self._subscription)
            self._subscription = None
        if self._mesh.is_connected:
            await self._mesh.disconnect()
        self._mesh = None
        self._queue = None
        self._channel_name_by_index = {}
        _logger.info("MeshCore disconnected")

    async def send_message(self, outbound: OutboundMessage) -> None:
        if not self._mesh or not self._mesh.is_connected:
            raise RuntimeError("Not connected")

        try:
            channel_idx = int(outbound.channel)
        except ValueError as exc:
            raise ValueError(
                "Channel must be a numeric MeshCore channel index (e.g. '0', '1')"
            ) from exc

        result = await self._mesh.commands.send_chan_msg(channel_idx, outbound.text)
        if result.type == EventType.ERROR:
            raise RuntimeError(f"MeshCore send failed: {result.payload}")

    async def run_message_loop(
        self,
        on_message: Callable[[ChannelMessage], Awaitable[None]],
        reconnect_delay_s: float = 3.0,
    ) -> None:
        while True:
            try:
                await self.connect()
                while self._mesh and self._mesh.is_connected and self._queue is not None:
                    message = await self._queue.get()
                    await on_message(message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _logger.exception("BLE loop error: %s", exc)
            finally:
                await self.disconnect()
                await asyncio.sleep(reconnect_delay_s)
