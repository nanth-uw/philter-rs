use crate::coordinates::{get_complement, Coordinates};
use crate::filters::{
    ContextDirection, FilterKind, FilterList, PosFilter, RegexContextFilter, RegexFilter, SetFilter,
};
use crate::{is_ascii_alphanum_star, make_alphanum, manual_tokenize};
use std::collections::HashSet;

/// Apply a [RegexFilter] to a string, returning [Coordinates]
pub fn map_regex(filter: &RegexFilter, text: &str) -> Coordinates {
    let mut coords = Coordinates::default();
    for m in filter.pattern.find_iter(text) {
        let m = m.expect("expected match not to fail");
        coords.add_extend(m.start(), m.end());
    }
    coords
}

/// Apply a [RegexContextFilter] to a string, returning [Coordinates]
pub fn map_regex_context(
    filter: &RegexContextFilter,
    text: &str,
    current_include: &mut Coordinates,
) -> Coordinates {
    let mut coords = Coordinates::default();
    if filter.context_filter_all {
        return coords;
    }
    let complement = get_complement(text, current_include);

    let phi_starts: HashSet<usize> = complement.data().keys().cloned().collect();
    let phi_ends: HashSet<usize> = complement.data().values().cloned().collect();

    for m in filter.pattern.find_iter(text) {
        let m = m.expect("expected capture not to fail");

        let matched_text = m.as_str();
        let clean = make_alphanum(matched_text);
        let tokens = manual_tokenize(&clean);

        let (start, end) = (m.start(), m.end());
        let mut phi_left = false;
        let mut phi_right = false;

        if phi_ends.contains(&start) {
            phi_left = true;
        }
        if phi_starts.contains(&end) {
            phi_right = true;
        }

        let mut coord_tracker: usize = 0;
        let mut tokenized_matches = Vec::new();
        for token in tokens {
            if token.is_empty() {
                continue;
            }
            if !is_ascii_alphanum_star(token.chars().next().expect("expected non-empty string")) {
                let current_start = start + coord_tracker;
                let current_end = current_start + token.len();
                tokenized_matches.push((current_start, current_end));
                coord_tracker += token.len();
            }
        }
        match (&filter.context, phi_left, phi_right) {
            (ContextDirection::Left, true, _) => {
                for item in tokenized_matches {
                    coords.add_extend(item.0, item.1);
                }
            }
            (ContextDirection::LeftOrRight, true, _) => {
                for item in tokenized_matches {
                    coords.add_extend(item.0, item.1);
                }
            }
            (ContextDirection::LeftOrRight, _, true) => {
                for item in tokenized_matches {
                    coords.add_extend(item.0, item.1);
                }
            }
            _ => continue,
        }
    }
    coords
}

/// Apply a [SetFilter] to a string, returning [Coordinates]
pub fn map_set(filter: &SetFilter, pos_tags: &[(String, String)]) -> Coordinates {
    let mut coords = Coordinates::default();
    let check_pos = filter.pos_tag.is_some();

    let mut start_coordinate = 0;
    for (token, tag) in pos_tags {
        let (start, stop) = (start_coordinate, start_coordinate + token.len());
        if token.trim().is_empty() {
            start_coordinate = stop;
            continue;
        }

        if !check_pos || (check_pos && filter.pos_tag.clone().unwrap() == *tag) {
            if filter.tokens.contains(token)
                || filter.tokens.contains(token.to_ascii_lowercase().trim())
            {
                coords.add_extend(start, stop);
            }
        }
    }

    coords
}

/// Apply a [PosFilter] to a string, returning [Coordinates]
pub fn map_pos(filter: &PosFilter, pos_labels: &[(String, String)]) -> Coordinates {
    let mut coords = Coordinates::default();
    let mut start_coordinate: usize = 0;
    for (token, pos_tag) in pos_labels {
        let (start, stop) = (start_coordinate, start_coordinate + token.len());
        // quick check, we know token is alphanum because of pre-processing
        if token.trim().is_empty() {
            start_coordinate = stop;
            continue;
        }
        match &filter.pos_tag {
            Some(tag) => {
                if tag == pos_tag {
                    coords.add_extend(start, stop);
                }
            }
            None => {}
        }
        start_coordinate = stop;
    }
    coords
}

/// Apply the results of a [FilterKind] to the global (for a single text)
/// include/exclude maps considering the filters exclude status.
pub fn apply_filter_result(
    include_map: &mut Coordinates,
    exclude_map: &mut Coordinates,
    coordinates: Coordinates,
    is_exclude: bool,
    is_regex_context: bool,
) {
    for (&start, &stop) in coordinates.data() {
        match (is_exclude, is_regex_context) {
            (true, false) => {
                if !include_map.does_overlap(start, stop) {
                    exclude_map.add_extend(start, stop);
                }
            }
            (false, false) => {
                if !exclude_map.does_overlap(start, stop) {
                    include_map.add_extend(start, stop);
                }
            }
            (true, true) => {
                exclude_map.add_extend(start, stop);
                include_map.remove(&start);
            }
            (false, true) => {
                include_map.add_extend(start, stop);
                exclude_map.remove(&stop);
            }
        }
    }
}

/// Search the text (and its part of speech tags) for filter matches. Return the final include map
/// of valid (keep) [Coordinates]
pub fn search(text: &str, pos_tags: Vec<(String, String)>, filters: &FilterList) -> Coordinates {
    let mut include_map = Coordinates::default();
    let mut exclude_map = Coordinates::default();

    for item in &filters.items {
        match item {
            FilterKind::RegexContext(f) => {
                let coords = map_regex_context(f, text, &mut include_map);
                // context and known to exclude
                apply_filter_result(&mut include_map, &mut exclude_map, coords, true, true);
            }
            FilterKind::Regex(f) => {
                let coords = map_regex(f, text);
                // not context, defer to pattern for exclude
                apply_filter_result(&mut include_map, &mut exclude_map, coords, f.exclude, false);
            }
            FilterKind::Set(f) => {
                let coords = map_set(f, &pos_tags);
                // not context, defer to pattern for exclude
                apply_filter_result(&mut include_map, &mut exclude_map, coords, f.exclude, false);
            }
            FilterKind::Pos(f) => {
                let coords = map_pos(f, &pos_tags);
                // not context, defer to pattern for exclude
                apply_filter_result(&mut include_map, &mut exclude_map, coords, f.exclude, false);
            }
        }
    }
    include_map
}

/// Transform the text according to the provided include [Coordinates], replacing non-included
/// positions with an asterisk
pub fn transform(text: &str, include: Coordinates) -> String {
    let mut contents = String::with_capacity(text.len());
    let mut last_marker: usize = 0;
    for (start, c) in text.char_indices() {
        if start < last_marker {
            continue;
        }
        if let Some(stop) = include.data().get(&start) {
            contents.push_str(&text[start..*stop]);
            last_marker = *stop;
        } else if !is_ascii_alphanum_star(c) {
            contents.push(c);
        } else {
            contents.push('*');
        }
    }
    contents
}
