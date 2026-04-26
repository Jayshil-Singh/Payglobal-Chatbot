import json
import os
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    eval_path = root / "eval" / "eval_set.json"
    if not eval_path.exists():
        raise SystemExit("Missing eval/eval_set.json")

    data = json.loads(eval_path.read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    if not cases:
        print("No eval cases configured.")
        return 0

    # Import after env is ready
    from rag_chain import ask, get_rag_chain

    # Allow API key via env for scheduled CI runs
    api_key = (os.getenv("GROK_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("GROK_API_KEY is required to run evals.")

    chain = get_rag_chain(api_key=api_key, chat_history=[])

    passed = 0
    for case in cases:
        q = case.get("question") or ""
        if not q:
            continue
        res = ask(chain, q)
        sources = res.get("sources") or []
        expect = case.get("expect") or {}
        expect_citations = bool(expect.get("citations", True))
        expected_files_any = expect.get("expected_files_any") or []
        ok = True
        if expect_citations and not sources:
            ok = False
        if ok and expected_files_any:
            found_files = {str(s.get("file", "")).lower() for s in sources if isinstance(s, dict)}
            if not any(str(f).lower() in found_files for f in expected_files_any):
                ok = False
        print(f"[{'PASS' if ok else 'FAIL'}] {case.get('id','?')}: sources={len(sources)}")
        if ok:
            passed += 1

    total = len([c for c in cases if c.get("question")])
    print(f"Eval summary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

