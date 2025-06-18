use crate::is_ascii_alphanum_star;
use std::cmp::max;
use std::collections::{HashMap, HashSet};

use itertools::Itertools;

/// A mapping of start/stop coordinates for pattern matches
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Coordinates(HashMap<usize, usize>);

impl From<HashMap<usize, usize>> for Coordinates {
    fn from(map: HashMap<usize, usize>) -> Self {
        Coordinates(map)
    }
}

impl Coordinates {
    /// Access the underlying HashMap
    pub fn data(&self) -> &HashMap<usize, usize> {
        &self.0
    }

    /// Remove an item from the underlying map
    pub fn remove(&mut self, idx: &usize) {
        self.0.remove(idx);
    }

    /// Add an item to the underlying map
    fn add(&mut self, start: usize, stop: usize) {
        self.0
            .entry(start)
            .and_modify(|v| {
                *v = max(stop, *v);
            })
            .or_insert(stop);
    }

    /// Add an item to the underlying map, extending the start/end coordinates as needed
    pub fn add_extend(&mut self, start: usize, stop: usize) {
        let overlaps: Vec<_> = self.max_overlaps(start, stop).collect();
        if overlaps.is_empty() {
            self.0.insert(start, stop);
        } else if overlaps.len() == 1 {
            self.add(overlaps[0].0, overlaps[0].1);
        } else {
            let first = overlaps.first().expect("expected first");
            let last = overlaps.last().expect("expected last");
            self.add(last.0, first.1);
        }
    }

    /// Check if the new start/stop coordinates overlap the existing ones
    pub fn does_overlap(&self, start: usize, stop: usize) -> bool {
        let coords: Vec<usize> = self
            .data()
            .iter()
            .flat_map(|(&s, &e)| (s..=e).collect::<Vec<usize>>())
            .collect();
        for i in start..=stop {
            if coords.contains(&i) {
                return true;
            }
        }
        false
    }

    /// Calculate the max overlap of existing coordinates and the provided start/stop
    pub fn max_overlaps(
        &self,
        start: usize,
        stop: usize,
    ) -> impl Iterator<Item = (usize, usize)> + use<'_> {
        self.data().iter().map(move |(&s, &e)| {
            if start >= s && start <= e {
                if stop >= e {
                    (s, stop)
                } else {
                    (s, e)
                }
            } else if stop >= s && stop <= e {
                if start <= s {
                    (start, e)
                } else {
                    (s, e)
                }
            } else {
                (s, e)
            }
        })
    }
}

/// Get the compliment coordinates based on the provided text and provided coordinates
pub fn get_complement(text: &str, coords: &Coordinates) -> Coordinates {
    let mut complement_map = HashMap::new();

    let current_coords: HashSet<usize> = coords
        .0
        .iter()
        .flat_map(|(&s, &e)| (s..e).collect::<Vec<usize>>())
        .collect();

    let text_coords: HashSet<usize> = (0..text.len()).collect();

    let mut complement_coords: HashSet<&usize> = text_coords.difference(&current_coords).collect();

    for (i, c) in text.char_indices() {
        if is_ascii_alphanum_star(c) {
            let _ = complement_coords.remove(&i);
        }
    }

    let mut complement_list: Vec<_> = complement_coords.into_iter().collect();
    complement_list.sort_unstable();
    for (_key, group) in &complement_list
        .into_iter()
        .enumerate()
        .chunk_by(|(idx, elem)| *elem - idx)
    {
        let group: Vec<_> = group.collect();
        let start = group.first().expect("expected first item in group").1;
        let stop = group.last().expect("expected last item in group").1;
        let _ = complement_map.insert(*start, stop + 1);
    }

    complement_map.into()
}
