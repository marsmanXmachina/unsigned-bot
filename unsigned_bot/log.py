"""
Module for custom logger.
"""

import logging


def setup_logger(name="unsigned_bot", log_level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt='%(levelname)s - %(asctime)s [%(module)s]: %(message)s',  datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)

    return logger


# Initialize global logger
logger = setup_logger()