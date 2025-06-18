# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "pydantic>2",
#   "rich",
# ]
# ///

import gzip
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal, Annotated

from pydantic import BaseModel, Field, ConfigDict, BeforeValidator, TypeAdapter

DATA_DIR = Path().cwd() / "data"
DEST_DIR = Path().cwd() / "python" / "philter_rs" / "data"


def _parse_regex_from_file(x: Any) -> str:
    fpath = Path(x)
    with open(DATA_DIR / fpath, "r") as f:
        pattern = f.read().strip()
    return pattern


class RegexFilter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type_: str = Field(alias="type", default="regex")
    pattern: Annotated[str, BeforeValidator(_parse_regex_from_file), Field(alias="filepath")]
    exclude: bool

    def model_post_init(self, context: Any, /) -> None:
        assert re.compile(self.pattern), f"Unable to compile pattern: {self.pattern}"


def _parse_context_filter(x: Any) -> bool:
    if str(x).lower() == "all":
        return True
    else:
        return False


class RegexContextFilter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type_: str = Field(alias="type", default="regex_context")
    pattern: Annotated[str, BeforeValidator(_parse_regex_from_file), Field(alias="filepath")]
    exclude: bool
    context: Literal["left", "right", "left_or_right"]
    context_filter_all: Annotated[bool, BeforeValidator(_parse_context_filter), Field(alias="context_filter")]

    def model_post_init(self, context: Any, /) -> None:
        assert re.compile(self.pattern), f"Unable to compile pattern: {self.pattern}"


def _parse_token_set_from_file(x: Any) -> list[str]:
    fpath = Path(x)
    with open(DATA_DIR / fpath, "r") as f:
        data = json.load(f)
    return sorted(set(data.keys()))


def _parse_pos_tags(x: Any) -> str | None:
    if x is None or len(list(x)) == 0:
        return None
    else:
        return list(x)[0]


class SetFilter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type_: str = Field(alias="type", default="set")
    tokens: Annotated[list[str], BeforeValidator(_parse_token_set_from_file), Field(alias="filepath")]
    pos_tag: Annotated[str | None, BeforeValidator(_parse_pos_tags), Field(alias="pos")]
    exclude: bool


class PosFilter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type_: str = Field(alias="type", default="pos_matcher")
    pos_tag: Annotated[str | None, BeforeValidator(_parse_pos_tags), Field(alias="pos")]
    exclude: bool


Filters = TypeAdapter(list[RegexFilter | RegexContextFilter | SetFilter | PosFilter])

type FilterList = list[RegexFilter | RegexContextFilter | SetFilter | PosFilter]


def load_data() -> FilterList:
    config_path = DATA_DIR / "configs" / "philter_zeta.json"
    with open(config_path, "r") as f:
        string_data = f.read()
    filters = Filters.validate_json(string_data)
    return filters


def dump_data(items: FilterList):
    with open(DATA_DIR / "optimized_config.json", "w") as f:
        for x in items:
            f.write(x.model_dump_json() + "\n")
    data = Filters.dump_json(items)
    with gzip.open(DATA_DIR / "optimized_config.json.gzip", "wb") as f:
        f.write(data)
    compressed = Path(DATA_DIR / "optimized_config.json.gzip")
    dest_path = DEST_DIR / "uw-config.json.gzip"
    shutil.copy(compressed, dest_path)


def main():
    parsed_config_data = load_data()
    print(f"Parsed: {len(parsed_config_data)} filters")

    variants: dict[str, int] = defaultdict(int)
    for item in parsed_config_data:
        variants[item.type_] += 1
    print(f"Variant counts: {dict(variants)}")

    dump_data(items=parsed_config_data)
    print(f"Dumped and copied data")


if __name__ == "__main__":
    main()
