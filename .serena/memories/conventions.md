# Conventions
- Existing code comments/docstrings and UI copy are primarily Chinese; preserve that language when editing source comments or visible labels.
- Configuration constants live in `config.py`; avoid scattering tunable values in modules.
- CSV cache files live under `data/`; code generally creates the directory through `ensure_data_dir()` before persistence.
- Public API parsing is centralized in `src/data_engine.py`; keep endpoint-specific parsing close to fetch functions.
- UI currently uses top-level Streamlit statements in `app.py`; refactors should extract small rendering/data helpers without changing visible behavior.