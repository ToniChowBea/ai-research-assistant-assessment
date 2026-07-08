import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((Path(__file__).parent / "cases.json").read_text())


def score(case: dict, body: dict, audit: dict) -> list[str]:
    """Return failure reasons; empty list means PASS."""
    failures: list[str] = []
    governance = audit.get("governance") or []
    rbac_denied = any(g.get("policy") == "researcher_access" for g in governance)

    if case.get("expect_denied"):
        # Denied = the researcher did not receive the restricted dataset, whether the
        # researcher_access policy blanked it or the agent declined to run it. The real
        # failure is a breach: the restricted dataset coming back in the delivered sources.
        ds = (case.get("dataset") or "").upper()
        got = {s.upper() for s in body.get("sources", [])}
        if ds and ds in got and not rbac_denied:
            failures.append(f"RBAC breach: '{case['researcher']}' received restricted {ds}")
        return failures

    if rbac_denied:
        failures.append("unexpected RBAC denial")

    if not case.get("skip_sources"):
        must = set(case.get("must_include", []))
        got = set(body.get("sources", []))
        if not must <= got:
            failures.append(f"missing sources: {sorted(must - got)}")

    # RBAC cases only assert researcher_access; min_records may still fire on analysis.
    if case.get("researcher"):
        return failures

    if not case.get("skip_suppression"):
        if case.get("expect_suppression") and not governance:
            failures.append("expected suppression; no governance policy fired")
        elif not case.get("expect_suppression") and governance:
            failures.append(f"unexpected suppression: {governance}")

    answer = body.get("answer", "")
    for needle in case.get("answer_contains", []):
        if needle.lower() not in answer.lower():
            failures.append(f"answer missing {needle!r}")

    return failures


async def fetch_audit(http: httpx.AsyncClient, trace_id: str) -> dict:
    resp = await http.get(f"/audit/{trace_id}")
    if resp.status_code == 404:
        return {"tools_invoked": [], "governance": [], "error": "no audit row found"}
    resp.raise_for_status()
    return resp.json()


def case_label(case: dict) -> str:
    researcher = case.get("researcher")
    question = case["question"]
    return f"{researcher} — {question}" if researcher else question


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--only", help="comma-separated 1-based case numbers")
    args = parser.parse_args()

    picks = {int(n) for n in args.only.split(",")} if args.only else None
    results = []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=180) as http:
        for i, case in enumerate(CASES, start=1):
            if picks and i not in picks:
                continue

            started = time.perf_counter()
            try:
                params = {"researcher": case["researcher"]} if case.get("researcher") else None
                resp = await http.post(
                    "/query",
                    params=params,
                    json={"question": case["question"]},
                )
                resp.raise_for_status()
                body = resp.json()
                audit = await fetch_audit(http, body["trace_id"])
                failures = score(case, body, audit)
            except Exception as e:
                body, audit, failures = {}, {}, [f"request failed: {e}"]

            latency_ms = int((time.perf_counter() - started) * 1000)
            status = "PASS" if not failures else "FAIL"
            tools_n = len(audit.get("tools_invoked", []))
            print(f"{i:>2}. {status}  {latency_ms:>6}ms  tools={tools_n:<2}  {case_label(case)}")
            for failure in failures:
                print(f"      - {failure}")
            results.append(
                {
                    "n": i,
                    "question": case["question"],
                    "researcher": case.get("researcher"),
                    "status": status,
                    "latency_ms": latency_ms,
                    "tools": tools_n,
                    "sources": body.get("sources"),
                    "trace_id": body.get("trace_id"),
                    "failures": failures,
                }
            )

    passed = sum(1 for r in results if r["status"] == "PASS")
    lat = sorted(r["latency_ms"] for r in results)
    if lat:
        q = lambda p: lat[min(len(lat) - 1, int(len(lat) * p))]
        print(
            f"\n{passed}/{len(results)} passed | latency ms "
            f"avg={int(statistics.mean(lat))} p50={q(0.5)} p90={q(0.9)} max={lat[-1]}"
        )

    out = Path(__file__).parent / "results.json"
    out.write_text(json.dumps({"results": results}, indent=2))
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
