use crate::filters::{parse_file, FilterList};
use crate::{manual_tokenize, philter};
use pyo3::types::{PyModule, PyModuleMethods};
use pyo3::{pyclass, pyfunction, pymethods, pymodule, wrap_pyfunction, Bound, PyResult};
use std::path::PathBuf;

/// Clean the text
#[pyfunction]
pub fn clean_text(text: &str) -> Vec<&str> {
    manual_tokenize(text)
}

/// Create our python engine
#[pyfunction]
pub fn create_engine(config_path: PathBuf) -> Engine {
    let filter_list = parse_file(config_path);
    Engine {
        compiled_filters: filter_list,
    }
}

/// The python engine
#[pyclass]
pub struct Engine {
    compiled_filters: FilterList,
}

#[pymethods]
impl Engine {
    fn __repr__(&self) -> String {
        format!("Engine(patterns: {})", self.compiled_filters.items.len())
    }
    fn __str__(&self) -> String {
        format!("Engine(patterns: {})", self.compiled_filters.items.len())
    }
    ///  Execute the algorithm (patterns) on the text/pos-tags
    pub fn philter(&self, text: &str, pos_tags: Vec<(String, String)>) -> String {
        philter(text, pos_tags, &self.compiled_filters)
    }
}

/// Our python module
#[pymodule]
fn _prs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(clean_text, m)?)?;
    m.add_function(wrap_pyfunction!(create_engine, m)?)?;
    m.add_class::<Engine>()?;
    Ok(())
}
