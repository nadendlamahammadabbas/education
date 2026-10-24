# Rules for AI agents working in this repo (Antigravity: add as a workspace rule)
- Work on ONE change at a time. Write or update the test first, then the code. Run `pytest` and show the real output.
- Never use an LLM to compute answers, labels or feedback numbers. All of that lives in `engine/` and is deterministic.
- `engine/` is pure Python: no web, database or network imports. Use `fractions.Fraction`, never floats.
- No dead code, unused dependencies, placeholder functions or TODO stubs. Every function is covered by a test.
- To add a misconception: add it to `engine/registry.py`, add exactly two templates in `engine/templates.py`
  (different surface forms, `correct != bug` always), and the existing property tests will cover it.
- If a requirement is unclear, stop and ask. Do not guess.
