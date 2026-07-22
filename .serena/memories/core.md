# Core
- Streamlit single-page stock scanner. Entrypoint: `app.py`; domain modules under `src/`.
- Main source map: `src/data_engine.py` handles public market APIs, CSV cache files, and watchlist persistence; `src/factor.py` ranks candidates; `src/signals.py` computes indicators/signals; `src/chart.py` renders mplfinance charts.
- Generated/release artifacts are present in repo working tree (`build/`, `dist/`, `AlphaScanner_Release/`, zip); treat source review separately from packaging output.
- Read `mem:tech_stack` for runtime/dependency facts, `mem:conventions` for local style, `mem:suggested_commands` for run/build commands, and `mem:task_completion` before completion checks.