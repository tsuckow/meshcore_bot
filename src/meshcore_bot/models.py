from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ChannelMessage:
    channel: str
    sender: str
    text: str
    message_id: Optional[str] = None


@dataclass(slots=True)
class OutboundMessage:
    channel: str
    text: str
    reply_to: Optional[str] = None
