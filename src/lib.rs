use crate::filters::FilterList;
use crate::processors::{search, transform};

mod bindings;
mod coordinates;
mod filters;
mod processors;

/// Replace non-ascii-alphanum with space
pub fn make_alphanum(text: &str) -> String {
    // use ascii variants which are slightly faster
    text.chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { ' ' })
        .collect()
}

/// split on ascii whitespace, retaining spaces
pub fn manual_tokenize(text: &str) -> Vec<&str> {
    let mut tokens = Vec::with_capacity(text.len());
    let mut start = 0;
    for (i, c) in text.char_indices() {
        if c.is_ascii_whitespace() {
            // push previous
            let slice = &text[start..i];
            if slice.is_empty() {
                tokens.push(" ");
                start = i + 1;
                continue;
            } else {
                tokens.push(slice);
                tokens.push(" ");
                start = i + 1;
            }
        }
    }

    if start < text.len() {
        tokens.push(&text[start..]);
    }
    tokens
}

/// Check if is ascii-alphanum OR is '*' using short-circuiting pattern matching
fn is_ascii_alphanum_star(c: char) -> bool {
    match c {
        'a'..='z' | 'A'..='Z' | '0'..='9' => true,
        '*' => true,
        _ => false,
    }
}

/// Main de-identification entrypoint, replaces characters with asterisk
pub fn philter(text: &str, pos_tags: Vec<(String, String)>, filters: &FilterList) -> String {
    let final_include = search(text, pos_tags, filters);
    let result = transform(text, final_include);
    result
}
