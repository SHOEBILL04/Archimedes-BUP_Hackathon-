import json
import urllib.request
import sys

def main():
    with open('BUP_CSE_FEST_2026_Participant_Docs/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json', 'r', encoding='utf-8') as f:
        pack = json.load(f)

    case0 = pack['cases'][0]
    print(f"=== TESTING CASE: {case0['id']} ({case0['label']}) ===")
    print("Operator Notes:")
    for i, n in enumerate(case0['input']['operator_notes']):
        print(f"  [{i}]: {n}")

    req = urllib.request.Request(
        'http://localhost:8000/optimize-energy',
        data=json.dumps(case0['input']).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("\n>>> RESPONSE RECEIVED (HTTP 200 OK)")
            print(f"Scenario ID: {data.get('scenario_id')}")
            print(f"Total Cost BDT: {data.get('total_cost_bdt')} (Reference: {case0['expected_output']['total_cost_bdt']})")
            print(f"Total Grid kWh: {data.get('total_grid_kwh')} (Reference: {case0['expected_output']['total_grid_kwh']})")
            print(f"Peak Grid kWh: {data.get('peak_grid_kwh')} (Reference: {case0['expected_output']['peak_grid_kwh']})")
            print("\nExtracted Directives:")
            for d in data.get('directive_interpretation', []):
                print(f"  Note {d['note_index']}: applies={d['applies']}, type={d['directive_type']}, adj={d.get('structured_adjustment')}")
            print("\nDeterministic Replay Verification:")
            print(f"  Verified: {data['verification']['verified']}")
            print(f"  Max Error: {data['verification']['max_constraint_error']}")
            print("\nFirst 3 Hours Plan:")
            for h in data.get('hourly_plan', [])[:3]:
                print(f"  Hour {h['hour']}: grid={h['grid_kwh']}, solar={h['solar_used_kwh']}, action={h['battery_action']}, bat_kwh={h['battery_kwh']}, bat_soc={h['battery_energy_after_kwh']}")
    except Exception as err:
        print(f"FAILED: {err}", file=sys.stderr)
        if hasattr(err, 'read'):
            print(err.read().decode(), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
