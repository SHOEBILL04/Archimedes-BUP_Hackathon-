import json
import urllib.request
import sys

BASE_URL = "http://localhost:8000"

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_1_health():
    print_header("TEST 1: Health & Readiness Check")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health") as resp:
            data = json.loads(resp.read().decode())
            print(f"Status Code: {resp.status}")
            print(f"Response: {data}")
            assert data.get("status") == "ok"
            print(">>> [PASS] Backend is alive and healthy.")
    except Exception as e:
        print(f">>> [FAIL] {e}")

def test_2_directives_and_distractor():
    print_header("TEST 2: LLM Directive Extraction & Distractor Rejection")
    body = {
        "scenario_id": "MANUAL-TEST-02",
        "operator_notes": [
            "Reduce solar from 1 PM to 3 PM by 80%",
            "The football team won their tournament match today"
        ],
        "hours": [
            {
                "hour": i,
                "demand_kwh": 50.0,
                "solar_kwh": 30.0 if 6 <= i <= 18 else 0.0,
                "tariff_bdt_per_kwh": 15.0 if 17 <= i <= 22 else 8.0,
            }
            for i in range(24)
        ],
        "battery": {
            "capacity_kwh": 100.0,
            "initial_energy_kwh": 40.0,
            "minimum_energy_kwh": 10.0,
            "max_charge_kwh_per_hour": 25.0,
            "max_discharge_kwh_per_hour": 25.0,
        }
    }
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/optimize-energy",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            dirs = data.get("directive_interpretation", [])
            print("Extracted Directives:")
            for d in dirs:
                print(f"  Note {d['note_index']}: applies={d['applies']}, type={d['directive_type']}, adjustment={d.get('structured_adjustment')}")
            
            # Verify Note 0 is solar_reduction for hours [13, 14]
            assert dirs[0]["directive_type"] == "solar_reduction"
            assert dirs[0]["structured_adjustment"]["hours"] == [13, 14]
            assert abs(dirs[0]["structured_adjustment"]["factor"] - 0.2) < 1e-4

            # Verify Note 1 is no_op
            assert dirs[1]["directive_type"] == "no_op"
            assert dirs[1]["applies"] is False
            print(">>> [PASS] Directive correctly parsed and distractor correctly ignored as no_op.")
    except Exception as e:
        print(f">>> [FAIL] {e}")

def test_3_physical_constraints():
    print_header("TEST 3: Physical Constraints & End-of-Day Neutrality")
    body = {
        "scenario_id": "MANUAL-TEST-03",
        "operator_notes": ["Maintain normal operations"],
        "hours": [
            {
                "hour": i,
                "demand_kwh": 60.0,
                "solar_kwh": 25.0 if 7 <= i <= 17 else 0.0,
                "tariff_bdt_per_kwh": 18.0 if 17 <= i <= 22 else 7.0,
            }
            for i in range(24)
        ],
        "battery": {
            "capacity_kwh": 120.0,
            "initial_energy_kwh": 50.0,
            "minimum_energy_kwh": 20.0,
            "max_charge_kwh_per_hour": 30.0,
            "max_discharge_kwh_per_hour": 30.0,
        }
    }
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/optimize-energy",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            v = data.get("verification", {})
            h23 = data["hourly_plan"][23]
            print(f"Initial Energy: 50.0 kWh")
            print(f"Hour 23 Energy After: {h23['battery_energy_after_kwh']} kWh")
            print(f"Deterministic Replay Verified: {v.get('verified')}")
            print(f"Max Constraint Error: {v.get('max_constraint_error')}")
            
            assert abs(h23["battery_energy_after_kwh"] - 50.0) < 0.05
            assert v.get("verified") is True
            assert v.get("max_constraint_error") < 1e-4
            print(">>> [PASS] End-of-day neutrality verified (E23 = E0) and zero constraint violations.")
    except Exception as e:
        print(f">>> [FAIL] {e}")

def test_4_official_sample_case():
    print_header("TEST 4: Official Judge Public Sample Case 1")
    try:
        with open("BUP_CSE_FEST_2026_Participant_Docs/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json", "r", encoding="utf-8") as f:
            pack = json.load(f)
        case0 = pack["cases"][0]
        req = urllib.request.Request(
            f"{BASE_URL}/optimize-energy",
            data=json.dumps(case0["input"]).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            ref_cost = case0["expected_output"]["total_cost_bdt"]
            actual_cost = data.get("total_cost_bdt")
            ref_grid = case0["expected_output"]["total_grid_kwh"]
            actual_grid = data.get("total_grid_kwh")
            print(f"Total Cost: {actual_cost} BDT (Judge Reference: {ref_cost} BDT)")
            print(f"Total Grid: {actual_grid} kWh (Judge Reference: {ref_grid} kWh)")
            assert abs(actual_cost - ref_cost) < 0.1
            assert abs(actual_grid - ref_grid) < 0.1
            print(">>> [PASS] Output matches official judge reference cost and grid usage exactly.")
    except Exception as e:
        print(f">>> [FAIL] {e}")

if __name__ == "__main__":
    test_1_health()
    test_2_directives_and_distractor()
    test_3_physical_constraints()
    test_4_official_sample_case()
    print("\n" + "=" * 60)
    print("  ALL VERIFICATION TESTS FINISHED!")
    print("=" * 60)
