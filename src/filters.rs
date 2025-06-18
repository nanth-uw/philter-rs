use fancy_regex::Regex;
use flate2::read::GzDecoder;
use std::collections::HashSet;
use std::fs::File;
use std::path::PathBuf;
use std::str::FromStr;

/// Container for a list of [FilterKind] configurations
#[derive(Debug)]
pub struct FilterList {
    pub items: Vec<FilterKind>,
}

/// Create a [FilterList] from a file. Used to read our compressed json file attached
/// to the python package
pub fn parse_file(fpath: PathBuf) -> FilterList {
    // Open the compressed file
    let file = File::open(fpath).expect("unable to open file");
    let decoder = GzDecoder::new(file);

    // Parse JSON directly from the decompressed stream
    let data: Vec<serde_json::Value> =
        serde_json::from_reader(decoder).expect("unable to parse json");

    let mut filter_list = Vec::with_capacity(data.len());
    for item in data {
        // println!("{:?}", item);
        let kind = item
            .get("type_")
            .expect("expected to have type_ field")
            .as_str()
            .expect("expected type field to be string");
        match kind {
            "regex" => filter_list.push(FilterKind::Regex(item.into())),
            "regex_context" => filter_list.push(FilterKind::RegexContext(item.into())),
            "set" => filter_list.push(FilterKind::Set(item.into())),
            "pos_matcher" => filter_list.push(FilterKind::Pos(item.into())),
            _ => panic!("unexpected filter type {}", kind),
        }
    }
    FilterList { items: filter_list }
}

/// Variations of filters
#[derive(Debug)]
pub enum FilterKind {
    /// The regex filter -> [RegexFilter]
    Regex(RegexFilter),
    /// The regex context filter -> [RegexContextFilter]
    RegexContext(RegexContextFilter),
    /// The set filter -> [SetFilter]
    Set(SetFilter),
    /// The part of speech filter -> [PosFilter]
    Pos(PosFilter),
}

/// Regex filter
#[derive(Debug)]
pub struct RegexFilter {
    /// Compiled regex pattern
    pub pattern: Regex,
    /// Exclude flag
    pub exclude: bool,
}

impl From<serde_json::Value> for RegexFilter {
    fn from(value: serde_json::Value) -> Self {
        let pattern = value
            .get("pattern")
            .expect("expected regex to have pattern")
            .as_str()
            .expect("expected regex pattern to be string");
        let re = Regex::new(pattern).expect("expected to be valid regex pattern");
        let exclude = value
            .get("exclude")
            .expect("expected regex to have exclude")
            .as_bool()
            .expect("expected exclude to be bool");
        RegexFilter {
            pattern: re,
            exclude,
        }
    }
}

/// Direction for the regex context buffer
#[derive(Debug)]
pub enum ContextDirection {
    Left,
    Right,
    LeftOrRight,
}

impl FromStr for ContextDirection {
    type Err = &'static str;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "left" => Ok(Self::Left),
            "right" => Ok(Self::Right),
            "left_or_right" => Ok(Self::LeftOrRight),
            _ => Err("invalid context direction"),
        }
    }
}

/// Regex context pattern
#[derive(Debug)]
pub struct RegexContextFilter {
    /// Compiled regex pattern
    pub pattern: Regex,
    /// Context direction
    pub context: ContextDirection,
    /// Whether we should consider this an "all" filter or an "other"
    pub context_filter_all: bool,
}

impl From<serde_json::Value> for RegexContextFilter {
    fn from(value: serde_json::Value) -> Self {
        let pattern = value
            .get("pattern")
            .expect("expected regex context to have pattern")
            .as_str()
            .expect("expected regex context pattern to be string");
        let re = Regex::new(pattern).expect("expected to be valid regex pattern");
        let context_string = value
            .get("context")
            .expect("expected regex context to have context")
            .as_str()
            .expect("expected context to be string");
        let context =
            ContextDirection::from_str(context_string).expect("expected valid context string");
        let context_filter_all = value
            .get("context_filter_all")
            .expect("expected context_filter_all to be bool")
            .as_bool()
            .expect("expected context_filter_all to be bool");

        RegexContextFilter {
            pattern: re,
            context,
            context_filter_all,
        }
    }
}

/// The Set filter
#[derive(Debug)]
pub struct SetFilter {
    /// Tokens/words
    pub tokens: HashSet<String>,
    /// Parts of speech from `nltk.pos_tag`
    pub pos_tag: Option<String>,
    /// Exclude flag
    pub exclude: bool,
}

impl From<serde_json::Value> for SetFilter {
    fn from(value: serde_json::Value) -> Self {
        let tokens: HashSet<String> = value
            .get("tokens")
            .expect("expected set to have tokens")
            .as_array()
            .expect("expected tokens to be array")
            .iter()
            .map(|x| {
                x.as_str()
                    .expect("expected tokens to be string")
                    .to_string()
            })
            .collect();
        let pos_tag = value
            .get("pos_tag")
            .expect("expected set to have exclude")
            .as_str()
            .map(|x| x.to_string());
        let exclude = value
            .get("exclude")
            .expect("expected set to have exclude")
            .as_bool()
            .expect("expected exclude to be bool");
        SetFilter {
            tokens,
            pos_tag,
            exclude,
        }
    }
}

/// Part of speech filter
#[derive(Debug)]
pub struct PosFilter {
    /// Parts of speech from `nltk.pos_tag`
    pub pos_tag: Option<String>,
    /// Exclude flag
    pub exclude: bool,
}

impl From<serde_json::Value> for PosFilter {
    fn from(value: serde_json::Value) -> Self {
        let pos_tag = value
            .get("pos_tag")
            .expect("expected set to have exclude")
            .as_str()
            .map(|x| x.to_string());
        let exclude = value
            .get("exclude")
            .expect("expected set to have exclude")
            .as_bool()
            .expect("expected exclude to be bool");
        PosFilter { pos_tag, exclude }
    }
}
