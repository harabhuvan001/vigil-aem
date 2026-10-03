"""Minimal standard logging configuration without credential dumping."""

import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level.upper(), format="%(asctime)s %(levelname)s %(message)s")
