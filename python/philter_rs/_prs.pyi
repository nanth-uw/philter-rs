from pathlib import Path


def clean_text(text: str) -> list[str]:
    """Clean the text maintaining spaces and return tokens including spaces

    Args:
        text: Text to clean

    Returns:
        str: cleaned text tokens
    """


class Engine:
    """Main Rust engine for Pattern searching"""

    ...

    def philter(
            self,
            text: str,
            pos_tags: list[tuple[str, str]],
    ) -> str:
        """Transform and de-identify the text

        Args:
            text: Text to transform
            pos_tags: Part of Speech tags from `nltk.pos_tag`

        Returns:
            str: text transformed w/ PHI removed and replaced with asterisks
        """
        ...


def create_engine(config_path: str | Path) -> Engine:
    """Create the regex/pattern engine

    Args:
       config_path: Path to the embedded config

    Returns:
        Engine: Philter engine
    """
    ...
