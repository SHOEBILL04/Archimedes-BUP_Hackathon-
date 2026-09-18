import json
import urllib.request
import time
import sys

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SAMPLE_PACK_PATH = "BUP_CSE_FEST_2026_Participant_Docs/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"
BASE_URL = "http://localhost:8000"

if len(sys.argv) > 1 and sys.argv[1] == "--cloud":
    BASE_URL = "https://archimedes-energy-backend.onrender.com"

def run_evaluation():
    print("=" * 75)
    print("  GRIDWISE 2026 -- JUDGE EVALUATION SIMULATOR (10 SAMPLE CASES)")
    print(f"  Target Endpoint: {BASE_URL}/optimize-energy")
    print("=" * 75)

    try:
        with open(SAMPLE_PACK_PATH, "r", encoding="utf-8") as f:
            pack = json.load(f)
    except Exception as e:
        print(f"Could not load sample pack: {e}")
        return

    cases = pack.get("cases", [])
    print(f"Loaded {len(cases)} official sample cases.\n")

    passed_count = 0
    total_cost_diff = 0.0
    latencies = []

    for idx, case in enumerate(cases):
        case_id = case["id"]
        label = case.get("label", "")
        print(f"[{idx+1:02d}/{len(cases):02d}] Testing {case_id}: {label}")

        payload = case["input"]
        expected = case.get("expected_output", {})

        req = urllib.request.Request(
            f"{BASE_URL}/optimize-energy",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                elapsed = time.time() - t0
                latencies.append(elapsed)
                res = json.loads(resp.read().decode("utf-8"))

                if resp.status != 200:
                    print(f"  [FAIL] HTTP {resp.status}")
                    continue

                actual_cost = res.get("total_cost_bdt", res.get("total_grid_cost_bdt", 0))
                expected_cost = expected.get("total_cost_bdt", 0)
                diff = abs(actual_cost - expected_cost)
                total_cost_diff += diff

                verified = res.get("verification", {}).get("verified", False)
                cost_match = "EXACT MATCH" if diff < 0.1 else f"Diff: {diff:.2f} BDT"
                status_icon = "[PASS]" if (diff < 100.0 and verified) else "[REVIEW]"

                print(f"  {status_icon} Cost: {actual_cost:.1f} BDT (Ref: {expected_cost} BDT | {cost_match}) | Latency: {elapsed:.2f}s | Verified: {verified}")
                passed_count += 1

        except Exception as err:
            print(f"  [ERROR] {err}")

    # Summary
    print("\n" + "=" * 75)
    print("  SIMULATION RESULTS SUMMARY")
    print("=" * 75)
    print(f"  Cases Completed: {passed_count} / {len(cases)}")
    if latencies:
        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = latencies[min(p95_idx, len(latencies)-1)]
        avg_latency = sum(latencies) / len(latencies)
        print(f"  Average Latency: {avg_latency:.2f}s")
        print(f"  P95 Latency:     {p95_latency:.2f}s (Threshold: < 5.0s -> FULL 3/3 POINTS)")
    print(f"  Total Cost Difference across pack: {total_cost_diff:.2f} BDT")
    print("=" * 75)

if __name__ == "__main__":
    run_evaluation()
