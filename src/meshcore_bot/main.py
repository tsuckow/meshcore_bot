from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from meshcore_bot.ble_client import MeshCoreBleClient
    from meshcore_bot.config import load_config
    from meshcore_bot.models import ChannelMessage
    from meshcore_bot.responder import ResponseEngine
else:
    from .ble_client import MeshCoreBleClient
    from .config import load_config
    from .models import ChannelMessage
    from .responder import ResponseEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MeshCore BLE channel bot")
    parser.add_argument(
        "--config",
        default="config/bot.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = load_config(args.config)
    client = MeshCoreBleClient(cfg.ble)
    responder = ResponseEngine(
        channel_rules=cfg.channel_rules,
        command_prefix=cfg.command_prefix,
        ignore_senders=cfg.ignore_senders,
    )

    async def on_message(message: ChannelMessage) -> None:
        logging.getLogger(__name__).info(
            "rx channel=%s sender=%s text=%s",
            message.channel,
            message.sender,
            message.text,
        )
        outbound = responder.maybe_respond(message)
        if outbound is None:
            return

        await client.send_message(outbound)
        logging.getLogger(__name__).info(
            "tx channel=%s text=%s",
            outbound.channel,
            outbound.text,
        )

    await client.run_message_loop(on_message)


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
