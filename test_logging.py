#!/usr/bin/env python3
"""Quick test script to verify logging configuration works."""

import os
import sys

# Add backend to path
sys.path.insert(0, "apps/backend/src")

# Load env vars
from dotenv import load_dotenv
load_dotenv()

# Configure logging first
from backend.logging import configure_logging
from backend.config import AppConfig

config = AppConfig.load()
print(f"[TEST] Loaded config: log_level={config.log_level}, loki_url={config.loki_url}")

configure_logging(
    level=config.log_level,
    loki_url=config.loki_url,
    loki_labels=config.loki_labels,
)

# Now import and test loggers
from backend.logger_factory import get_logger

logger = get_logger(__name__)

print("\n" + "="*60)
print("TESTING LOGGING")
print("="*60 + "\n")

logger.debug("This is a DEBUG message")
logger.info("This is an INFO message")
logger.warning("This is a WARNING message")
logger.error("This is an ERROR message")

# Test module-level logger
from backend.services.llm import logger as llm_logger
llm_logger.info("Testing LLM logger - should appear in console and Loki")

from backend.services.telegram_bot import logger as bot_logger
bot_logger.info("Testing bot logger - should appear in console and Loki")

print("\n" + "="*60)
print("DONE - Check console output above and Grafana Loki")
print("="*60)
