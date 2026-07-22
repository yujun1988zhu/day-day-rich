# Task Completion
- No dedicated test, lint, formatter, or type-check config is present.
- For source changes, at minimum run Python compilation: `venv/Scripts/python.exe -m compileall app.py src config.py`.
- For UI/data-path changes, manually smoke run Streamlit: `venv/Scripts/python.exe -m streamlit run app.py --server.port 8501`.
- For packaging changes, run the relevant Windows build script and inspect generated release artifacts.
- Consider running `serena memories check` after updating memory references.