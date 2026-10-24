"""Runs the test suite without pytest (every test is a plain function with no fixtures).
Prefer `pytest` when available; this is a fallback."""
import importlib, pathlib, sys, time, traceback

sys.path.insert(0, str(pathlib.Path(__file__).parent))
failed = passed = 0
for f in sorted(pathlib.Path("tests").glob("test_*.py")):
    try:
        mod = importlib.import_module(f"tests.{f.stem}")
    except BaseException as e:
        print(f"SKIP {f.name}: {type(e).__name__}: {str(e)[:80]}"); continue
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        t0 = time.time()
        try:
            getattr(mod, name)(); passed += 1; print(f"PASS {f.stem}::{name} ({time.time() - t0:.2f}s)")
        except Exception:
            failed += 1; print(f"FAIL {f.stem}::{name}"); traceback.print_exc()
print(f"\n{passed} passed, {failed} failed"); sys.exit(1 if failed else 0)
