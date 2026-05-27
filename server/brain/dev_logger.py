"""
Development-only logger for debugging voice pipeline without polluting production logs.

Usage in any file:
    from server.brain.dev_logger import get_dev_logger
    dev = get_dev_logger()
    dev.debug("User said: %s", user_text)
    dev.info("Order state changed to: %s", state.order_flow_state)
    dev.warning("create_order was blocked - missing confirmation")

The logger is cached (singleton pattern) so multiple calls return the same instance
and avoid duplicate handlers. Configure the level in get_dev_logger() if needed.
"""

import logging
from functools import lru_cache


@lru_cache(maxsize=1)
def get_dev_logger():
    """
    Get or create the development logger.
    
    Cached via @lru_cache so multiple imports return the same instance.
    This prevents duplicate handlers and ensures consistent output.
    """
    logger = logging.getLogger("dev")
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers = []
    
    # Console handler with clean format
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[DEV %(levelname)s %(asctime)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Don't propagate to root logger (keeps output isolated)
    logger.propagate = False
    
    return logger


# Example usage (commented out):
# if __name__ == "__main__":
#     dev = get_dev_logger()
#     dev.debug("Debug message (only shown at DEBUG level)")
#     dev.info("Info message - use for state changes, important milestones")
#     dev.warning("Warning message - use for blocked operations, anomalies")
#     dev.error("Error message - use for failures that don't crash")
