import logging


def configure_logging() -> None:
    """Configure global logging defaults."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
