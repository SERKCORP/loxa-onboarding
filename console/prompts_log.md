# Prompts log: console

How the console was directed in Claude Code, and what broke along the way.

| # | Prompt | Result | What broke and the fix |
|---|---|---|---|
| 1 | Build a local website: enter a partner URL, run both agents in parallel, show results within seconds, log every run | `console.py`, `core/agents.py`, `web/` | GitHub Actions takes 30–90s to start a job, too slow for an on-demand run, so the console runs locally and GitHub holds the code and CI |
| 2 | Add a question box that answers from the run's own data and names its source | `core/answer.py` | Answers read "1 SKUs" and lacked a recommendation for launch order; fixed |
| 3 | End-to-end tests: two local partner sites, the example questions, downloads, history | `tests/run_tests.py` | The `console/` package shadowed `console.py`; renamed it `core/`. Test runs leaked into run history; tests now use a temp folder |
| 4 | Make it Windows-safe | UTF-8 subprocess output, Python installer | Agent output could garble on Windows' default encoding; forced UTF-8 |
| 5 | Redesign: graphical snapshot, separate agent tabs, problems log, CRM placeholder, guided tour | `web/`, `core/issues.py` | See tests |
