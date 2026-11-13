"""Entry point:  python -m serpentwatch --config config.yaml"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import sys

from . import __version__
from .config import ConfigError, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(prog="serpentwatch", description=__doc__)
    parser.add_argument("-c", "--config", default="config.yaml", help="path to config.yaml")
    parser.add_argument("--no-preview", action="store_true", help="headless mode (no windows)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    try:
        settings = load_settings(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.no_preview:
        settings = dataclasses.replace(settings, show_preview=False)

    from .app import run  # imported late so --help and config errors stay instant
    run(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
