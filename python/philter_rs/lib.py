from typing import Any

import nltk
from pydantic import BaseModel

from philter_rs import _prs, utils


class PhilterEngine(BaseModel):
    """Main engine to perform Philter PHI transformations.

    Due to parsing configs, this can take a few seconds to load, so only
    load this once at the start of your processing.
    """

    _engine: _prs.Engine | None = None

    def model_post_init(self, context: Any, /) -> None:
        utils.ensure_nltk_resource()
        fpath = utils.config_path()
        self._engine = _prs.create_engine(config_path=fpath)

    def process(self, text: str) -> str:
        """Takes text, clean it, tag POS, and transform PHI to asterisk

        Args:
            text: The text to de-identify

        Returns:
            str: Transformed text
        """
        clean_tokens = _prs.clean_text(text)
        pos_tags: list[tuple[str, str]] = nltk.pos_tag(clean_tokens)
        transformed = self._engine.philter(
            text=text,
            pos_tags=pos_tags,
        )
        return transformed
