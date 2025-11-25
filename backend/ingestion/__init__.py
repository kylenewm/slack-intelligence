"""Ingestion modules for Slack Intelligence"""

from .slack_ingester import SlackIngester
from .message_parser import MessageParser

__all__ = ["SlackIngester", "MessageParser"]

