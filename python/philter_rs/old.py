import itertools
import json
import re
from pathlib import Path
from typing import Any, Generator

import nltk
from pydantic import BaseModel, Field


class CoordinateMap(BaseModel):
    map_: dict[int, int] = Field(default_factory=dict)

    def add(self, start: int, stop: int):
        self.map_[start] = stop

    def add_extend(self, start: int, stop: int):
        """adds a new coordinate to the coordinate map
        if overlaps with another, will extend to the larger size
        """
        overlaps = self.max_overlap(start=start, stop=stop)

        def clear_overlaps(items: list[dict[str, Any]]):
            for ov in items:
                self.remove(ov["orig_start"])

        if len(overlaps) == 0:
            self.add(start=start, stop=stop)
        elif len(overlaps) == 1:
            clear_overlaps(items=overlaps)
            # 1 overlap, save this value
            o = overlaps[0]
            self.add(start=o["new_start"], stop=o["new_stop"])
        else:
            clear_overlaps(items=overlaps)
            # greater than 1 overlap, by default this is sorted because of scan order
            o1 = overlaps[0]
            o2 = overlaps[-1]
            self.add(
                start=o2["new_start"],
                stop=o1["new_stop"],
            )

        return True, None

    def remove(self, start: int):
        """Removes this coordinate pairing from the map, all_coords, and coord2pattern"""
        if start in self.map_:
            del self.map_[start]

    def scan(self) -> Generator[tuple[int, int]]:
        """does an inorder scan of the coordinates and their values"""
        coords = list(self.map_.keys())
        coords.sort()
        for coord in coords:
            yield coord, self.map_[coord]

    def keys(self) -> Generator[int]:
        for key in self.map_:
            yield key

    def get_coords(self, start: int) -> tuple[int, int]:
        stop = self.map_[start]
        return start, stop

    def get_all_coords(self) -> Generator[tuple[int, int]]:
        """
        generator does an inorder scan of the coordinates for this file
        """
        coords = list(self.map_.keys())
        for coord in coords:
            yield coord, self.map_[coord]

    def does_exist(self, index: int) -> bool:
        """Simple check to see if this index is a hit (start of coordinates)"""
        return index in self.map_

    def does_overlap(self, start: int, stop: int) -> bool:
        """Check if this coordinate overlaps with any existing range"""

        ranges = [list(range(key, self.map_[key] + 1)) for key in self.map_]
        all_coords = [item for sublist in ranges for item in sublist]
        # removing all_coords implementation until we write some tests
        for i in range(start, stop + 1):
            if i in all_coords:
                return True
        return False

    def calc_overlap(self, start: int, stop: int) -> list[dict[str, int]]:
        """given a set of coordinates, will calculate all overlaps
        perf: stop after we know we won't hit any more
        perf: use binary search approach
        """

        overlaps: list[dict[str, int]] = []
        for s in self.map_:
            e = self.map_[s]
            if start <= s or s <= stop:
                if e <= stop:
                    overlaps.append({"start": s, "stop": e})
                else:
                    overlaps.append({"start": s, "stop": stop})
            elif e >= start or e <= stop:
                if s >= start:
                    overlaps.append({"start": s, "stop": e})
                else:
                    overlaps.append({"start": start, "stop": e})
        return overlaps

    def max_overlap(self, start: int, stop: int) -> list[dict[str, int]]:
        """given a set of coordinates, will calculate max of all overlaps
        perf: stop after we know we won't hit any more
        perf: use binary search approach
        """

        overlaps: list[dict[str, int]] = []
        for s in self.map_:
            e = self.map_[s]
            if s <= start <= e:
                # We found an overlap
                if stop >= e:
                    overlaps.append(
                        {
                            "orig_start": s,
                            "orig_end": e,
                            "new_start": s,
                            "new_stop": stop,
                        }
                    )
                else:
                    overlaps.append(
                        {"orig_start": s, "orig_end": e, "new_start": s, "new_stop": e}
                    )

            elif s <= stop <= e:
                if start <= s:
                    overlaps.append(
                        {
                            "orig_start": s,
                            "orig_end": e,
                            "new_start": start,
                            "new_stop": e,
                        }
                    )
                else:
                    overlaps.append(
                        {"orig_start": s, "orig_end": e, "new_start": s, "new_stop": e}
                    )

        return overlaps

    def get_complement(self, text: str) -> dict:
        """get the complementary coordinates of the input coordinate map (excludes punctuation)"""

        complement_coordinate_map = {}

        current_map_coordinates = []
        for start_key in self.map_:
            start = start_key
            stop = self.map_[start_key]
            current_map_coordinates += range(start, stop)

        text_coordinates = list(range(0, len(text)))
        complement_coordinates = list(
            set(text_coordinates) - set(current_map_coordinates)
        )

        # Remove punctuation from complement coordinates
        punctuation_matcher = re.compile(r"[^a-zA-Z0-9*]")
        for i in range(0, len(text)):
            if punctuation_matcher.match(text[i]):
                if i in complement_coordinates:
                    complement_coordinates.remove(i)

        # Group complement coordinates into ranges
        def to_ranges(iterable):
            iterable = sorted(set(iterable))
            for key, group in itertools.groupby(
                    enumerate(iterable), lambda t: t[1] - t[0]
            ):
                group = list(group)
                yield group[0][1], group[-1][1] + 1

        complement_coordinate_ranges = list(to_ranges(complement_coordinates))

        # Create complement dictionary
        for tup in complement_coordinate_ranges:
            start = tup[0]
            stop = tup[1]
            complement_coordinate_map[start] = stop

        return complement_coordinate_map


def precompile(regex: str) -> re.Pattern:
    """precompiles our regex to speed up pattern matching"""
    return re.compile(regex)


def init_set(filepath: Path) -> set[str]:
    """loads a set of words, (must be a dictionary or set shape) returns result"""
    with open(filepath, "r") as f:
        data = json.load(f)
    return set(data.keys())


def init_patterns(fpath: Path) -> list[dict[str, Any]]:
    """given our input pattern config will load our sets and pre-compile our regex"""

    with open(fpath, "r") as f:
        data = json.load(f)

    patterns: list[dict[str, Any]] = []
    for pattern in data:
        if pattern["type"] == "set":
            pattern["data"] = init_set(pattern["filepath"])
            patterns.append(pattern)
        elif pattern["type"] in {"regex", "regex_context"}:
            with open(pattern["filepath"], "r") as f:
                text = f.read().strip()
            pattern["data"] = precompile(regex=text)
            patterns.append(pattern)

    return [p for p in patterns if p["type"] != "regex_context"]
    # return patterns


def map_regex(text: str, regex: re.Pattern) -> CoordinateMap:
    """Creates a coordinate map from the pattern on this data
    generating a coordinate map of hits given (dry run doesn't transform)
    """
    # print(pattern)
    coord_map = CoordinateMap()

    # if __debug__: print("map_regex(): searching for regex with index " + str(pattern_index))
    # if __debug__ and pattern_index: print("map_regex(): regex is " + str(regex))
    matches = regex.finditer(text)

    for m in matches:
        # print(m.group())
        # print(self.patterns[pattern_index]['title'])

        coord_map.add_extend(m.start(), m.start() + len(m.group()))

    return coord_map


def map_pos(text: str, pos_set: set[str]) -> CoordinateMap:
    """Creates a coordinate mapping of words which match this part of speech (POS)"""
    coords = CoordinateMap()

    # Use pre-process to split sentence by spaces AND symbols, while preserving spaces in the split list

    cleaned = get_clean(text=text)
    pos_list = list(nltk.pos_tag(tokens=cleaned))

    start_coordinate = 0
    for tup in pos_list:
        word = tup[0]
        pos = tup[1]
        start = start_coordinate
        stop = start_coordinate + len(word)
        # word_clean = self.get_clean_word2(filename,word)
        word_clean = re.sub(r"[^a-zA-Z0-9]+", "", word.lower().strip())
        if len(word_clean) == 0:
            # got a blank space or something without any characters or digits, move forward
            start_coordinate += len(word)
            continue

        if pos in pos_set:
            coords.add_extend(start, stop)

        # advance our start coordinate
        start_coordinate += len(word)

    return coords


def map_set(text: str, words: set[set], pos_tag: list[str] | None) -> CoordinateMap:
    """Creates a coordinate mapping of words any words in this set"""
    coords = CoordinateMap()

    # get part of speech we will be sending through this set
    # note, if this is empty we will put all parts of speech through the set
    check_pos = False
    if pos_tag:
        check_pos = True

    cleaned = get_clean(text=text)
    pos_list = list(nltk.pos_tag(cleaned))

    start_coordinate = 0
    for tup in pos_list:
        word = tup[0]
        pos = tup[1]
        start = start_coordinate
        stop = start_coordinate + len(word)

        # This converts spaces into empty strings, so we know to skip forward to the next real word
        word_clean = re.sub(r"[^a-zA-Z0-9]+", "", word.lower().strip())
        if len(word_clean) == 0:
            # got a blank space or something without any characters or digits, move forward
            start_coordinate += len(word)
            continue

        if not check_pos or (check_pos and pos in pos_tag):
            if word_clean in words or word in words:
                coords.add_extend(start, stop)

        # advance our start coordinate
        start_coordinate += len(word)

    return coords


def map_regex_context(
        text: str, pattern: dict[str, Any], pre_process=r"[^a-zA-Z0-9]"
) -> dict[str, Any]:
    """map_regex_context creates a coordinate map from combined regex + PHI coordinates
    of all previously mapped patterns
    """

    coord_map = pattern["coordinate_map"]
    regex = pattern["data"]
    context = pattern["context"]
    context_filter = pattern.get("context_filter", "all")

    # Get PHI coordinates
    if context_filter == "all":
        # current_include_map = self.get_full_include_map(filename)
        current_include_map = self.include_map
        # Create complement exclude map (also excludes punctuation)
        full_exclude_map = current_include_map.get_complement(text)

    else:
        full_exclude_map = {}
        for start, stop in coord_map.get_all_coords():
            full_exclude_map[start] = stop

    # 1. Get coordinates of all include and exclude mathches

    punctuation_matcher = re.compile(r"[^a-zA-Z0-9*]")
    # 2. Find all patterns expressions that match regular expression
    matches = regex.finditer(text)
    # print(full_exclud_map)
    for m in matches:
        # initialize phi_left and phi_right
        phi_left = False
        phi_right = False

        match_start = m.span()[0]
        match_end = m.span()[1]

        # PHI context left and right
        phi_starts = []
        phi_ends = []
        for start in full_exclude_map:
            phi_starts.append(start)
            phi_ends.append(full_exclude_map[start])

        if match_start in phi_ends:
            phi_left = True

        if match_end in phi_starts:
            phi_right = True

        # Get index of m.group()first alphanumeric character in match
        tokenized_matches = []
        match_text = m.group()
        split_match = re.split(r"(\s+)", re.sub(pre_process, " ", match_text))

        # Get all spans of tokenized match (because remove() function requires tokenized start coordinates)
        coord_tracker = 0
        for element in split_match:
            if element != "":
                if not punctuation_matcher.match(element[0]):
                    current_start = match_start + coord_tracker
                    current_end = current_start + len(element)
                    tokenized_matches.append((current_start, current_end))

                    coord_tracker += len(element)
                else:
                    coord_tracker += len(element)

        ## Check for context, and add to coordinate map
        if (
                (context == "left" and phi_left)
                or (context == "right" and phi_right)
                or (context == "left_or_right" and (phi_right or phi_left))
                or (context == "left_and_right" and (phi_right and phi_left))
        ):
            for item in tokenized_matches:
                coord_map.add_extend(item[0], item[1])

    pattern["coordinate_map"] = coord_map
    return pattern


def transform(text: str, include: CoordinateMap) -> str:
    """transform
    turns input files into output PHI files
    protected health information will be replaced by the replacement character

    transform the data
    ORDER: Order is preserved prioritiy,
    patterns at spot 0 will have priority over patterns at index 2

    **Anything not caught in these passes will be assumed to be PHI
    """
    last_marker = 0
    punctuation_matcher = re.compile(r"[^a-zA-Z0-9*]")

    # read the text by character, any non-punc non-overlaps will be replaced
    contents = []
    for i in range(0, len(text)):
        if i < last_marker:
            continue

        if include.does_exist(i):
            # add our preserved text
            start, stop = include.get_coords(i)
            contents.append(text[start:stop])
            last_marker = stop
        elif punctuation_matcher.match(text[i]):
            contents.append(text[i])
        else:
            contents.append("*")

    return "".join(contents)


def philter(text: str, patterns: list[dict[str, Any]]) -> str:
    """Main function that handles the full PHI filtering pipeline"""
    # Get coordinates from all patterns
    pattern_results = map_coordinates(text, patterns)

    # Generate include map from pattern results
    include_map = apply_pattern_coords(pattern_results)

    # Transform text using include map
    return transform(text, include_map)


def apply_pattern_coords(
        pattern_results: list[tuple[CoordinateMap, bool, str]],
) -> CoordinateMap:
    """Pure function to generate include map from pattern coordinates"""
    include_map = CoordinateMap()
    exclude_map = CoordinateMap()  # Temporary for overlap checking

    for coords, is_exclude, pattern_type in pattern_results:
        for start, stop in coords.get_all_coords():
            if pattern_type != "regex_context":
                if is_exclude:
                    if not include_map.does_overlap(start, stop):
                        exclude_map.add_extend(start, stop)
                else:
                    if not exclude_map.does_overlap(start, stop):
                        include_map.add_extend(start, stop)
            else:
                # Special handling for regex_context
                if is_exclude:
                    exclude_map.add_extend(start, stop)
                    include_map.remove(start)
                else:
                    include_map.add_extend(start, stop)
                    exclude_map.remove(start)

    return include_map


def map_coordinates(
        text: str, patterns: list[dict[str, Any]]
) -> list[tuple[CoordinateMap, bool, str]]:
    """Maps all patterns to their coordinates in the text"""
    pattern_results = []

    for pattern in patterns:
        if pattern["type"] == "regex":
            coords = map_regex(text, pattern["data"])
        elif pattern["type"] == "regex_context":
            coords = map_regex_context(text, pattern)
        elif pattern["type"] == "set":
            coords = map_set(text, pattern["data"], pattern.get("pos", None))
        elif pattern["type"] == "pos_matcher":
            coords = map_pos(text, pattern["pos"])
        else:
            raise Exception(f"Error, pattern type not supported: {pattern['type']}")

        pattern_results.append((coords, pattern["exclude"], pattern["type"]))

    return pattern_results


def main():
    note_files = list((Path().cwd() / "newer/data/i2b2_notes/").glob("*.txt"))
    print(note_files)

    notes = []
    for note_file in note_files:
        with open(note_file) as f:
            note = f.read().strip()
            notes.append(note)

    text = "my name is Nick Anthony! 😁 I was born on 7/9/95"

    patterns = init_patterns(Path("configs/philter_zeta.json"))
    print(len(patterns))
    # print(patterns[0])

    r = philter(text, patterns)
    print(r)

    # size = 1_000
    #
    # for _ in trange(size):
    #     result = philter(text, patterns)
    #     # print(result)
    #
    # big_notes = notes * int(size / len(notes))
    # for note in tqdm(big_notes):
    #     result = philter(note, patterns)
    # print(result)
