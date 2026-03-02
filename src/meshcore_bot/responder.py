from __future__ import annotations

from dataclasses import dataclass

from .models import ChannelMessage, OutboundMessage


@dataclass(slots=True)
class ResponseEngine:
    channel_rules: dict[str, dict[str, str]]
    command_prefix: str = "!"
    ignore_senders: set[str] | None = None

    def maybe_respond(self, msg: ChannelMessage) -> OutboundMessage | None:
        if self.ignore_senders and msg.sender in self.ignore_senders:
            return None

        rules = self.channel_rules.get(msg.channel_name) if msg.channel_name else None
        if not rules:
            rules = self.channel_rules.get(msg.channel)
        if not rules:
            rules = self.channel_rules.get("*")
        if not rules:
            return None

        text = msg.text.strip()
        if not text.startswith(self.command_prefix):
            return None

        command = text[len(self.command_prefix):].strip().lower()
        if not command:
            return None

        response = rules.get(command)
        if response is None:
            return None

        return OutboundMessage(channel=msg.channel, text=response, reply_to=msg.message_id)
