"""Run both configured extraction pipelines sequentially in one process."""

from __future__ import annotations

import logging

import extract_opinion_units
import extract_representative_attributes


def main() -> tuple[object, object]:
    """Run Opinion Units first, then direct representative attributes on success."""
    logging.info("combined extraction started: stage=opinion_units")
    opinion_units = extract_opinion_units.main()
    logging.info("combined extraction continued: stage=representative_attribute")
    representative_attributes = extract_representative_attributes.main()
    logging.info("combined extraction completed")
    return opinion_units, representative_attributes


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()

