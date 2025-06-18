import gzip
import json
from importlib import resources

import nltk


def get_clean(text: str, pre_process=r"[^a-zA-Z0-9]") -> list[str]:
    # Use pre-process to split sentence by spaces AND symbols, while preserving spaces in the split list
    lst = re.split(r"(\s+)", text)
    cleaned = []
    for item in lst:
        if len(item) > 0:
            if not item.isspace():
                split_item = re.split(r"(\s+)", re.sub(pre_process, " ", item))
                for elem in split_item:
                    if len(elem) > 0:
                        cleaned.append(elem)
            else:
                cleaned.append(item)
    return cleaned


def ensure_nltk_resource():
    """Ensures punkt tokenizer is downloaded and works"""
    name = "tokenizers/punkt"
    try:
        nltk.data.find(name)
    except LookupError:
        print(f"NLTK resource '{name}' not found. Downloading...")
        nltk.download(name)
        try:
            nltk.pos_tag("hi there")
        except:
            raise ValueError("expected to have working pos tagger after download")


def config_path() -> str:
    """Loads filters from compressed data file from the package."""
    data_dir = resources.files("philter_rs") / "data"
    file_path = data_dir / "uw-config.json.gzip"
    return str(file_path)


def _load_config_data() -> list[dict[str, str | bool | set[str] | None]]:
    """Loads filters from compressed data file from the package."""
    data_dir = resources.files("philter_rs") / "data"
    file_path = data_dir / "uw-config.json.gzip"

    with gzip.open(file_path, "r") as f:
        bytes_data = f.read()
    json_string = bytes_data.decode(encoding="utf-8")
    parsed: list[dict[str, str | bool | set[str] | None]] = json.loads(json_string)
    return parsed
