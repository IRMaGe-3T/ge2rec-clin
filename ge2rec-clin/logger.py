import logging
from pathlib import Path


def setup_logger(verbose=True, log_file: Path | None = None):

    level = logging.INFO if verbose else logging.WARNING

    handlers = []
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    handlers.append(stream_handler)

    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(exist_ok=True, parents=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )

    return logging.getLogger("mri_pipeline")

