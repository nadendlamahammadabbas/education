# Misconception Tutor

Traces wrong answers back to a likely root misconception, then generates targeted practice.
Five misconceptions (fractions, order of operations, negatives, squaring a sum, percent changes),
two problem templates each.

## Run (Windows PowerShell)
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest                                          # all tests
uvicorn server.main:create_app --factory --reload
# open http://127.0.0.1:8000
python -m engine.simulate                       # simulation results as JSON
```
If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
No pytest? `python run_tests_stdlib.py` runs the same tests (the HTTP tests need FastAPI and are skipped).

## How it works
- **Bug = executable misconception.** Each template computes the correct answer and the exact answer a
  student holding the target misconception would give (`engine/templates.py`). Items are only emitted when
  the two differ, so a match is unambiguous.
- **Classification = matching, not guessing.** `classify()` returns `correct`, `misconception`, or
  `other_error`. Unparseable input is rejected and never recorded.
- **Evidence, not one-shot labels.** Per misconception, the last 6 informative answers give
  P(active) = P(Beta(1+matches, 1+corrects) > 0.5). One match = *candidate* (0.75); two = *active* (0.875).
  A learner who starts answering correctly drops back to *none*.
- **Flow.** 10-question diagnostic (each misconception twice, two surface forms) -> practice set on the
  most likely misconception (4 targeted at rising difficulty, 1 interleaved) -> mixed review when nothing is
  flagged. Feedback is built from the learner's own numbers; no LLM is involved anywhere.
- **Persistence.** SQLite file `tutor.db` (override with `TUTOR_DB`). Learner state is derived from the
  attempt log, so restarts lose nothing.
- **Session Review & History.** Detailed step-by-step attempt log with prompt, learner answer, correct answer,
  and worked solution (`/api/learners/{id}/history`).
- **Deliberate Practice & Profile Management.** Learners or teachers can trigger targeted practice on any
  misconception at any time (`/api/learners/{id}/practice`), switch profiles, or reset diagnostic checks.


## Evidence that targeting helps
`/api/evidence` (button in the UI) and `python -m engine.simulate` run simulated learners with the same
learning rule in both conditions, differing only in how practice is allocated (targeted vs random).
It is a simulation under stated assumptions, not data from real learners. For real evidence, compare a
learner's bug-answer rate on the diagnostic vs a later session; the profile dots show this per misconception.

## Known limits
- Diagnosis from 2 items per misconception is noisy: a learner who holds a misconception gives the bug
  answer ~81% of the time in the simulator, so recall is ~0.8. Practice and review items keep refining it.
- Free-entry numeric answers only. Work shown is not analysed.
- Misconceptions are mapped to templates by hand; no external dataset is used.
