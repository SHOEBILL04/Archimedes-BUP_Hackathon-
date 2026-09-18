import { EnergyScenario } from "@/types/energy";

export const DEFAULT_SAMPLE_SCENARIO: EnergyScenario = {
  demand_kwh: [
    35, 34, 33, 32, 31, 30, 32, 38,
    45, 52, 58, 62, 65, 68, 70, 72,
    75, 78, 74, 68, 60, 52, 45, 40,
  ],
  base_solar_kwh: [
    0, 0, 0, 0, 0, 0, 3, 8,
    15, 22, 30, 38, 42, 44, 40, 32,
    22, 12, 5, 0, 0, 0, 0, 0,
  ],
  tariff_bdt_per_kwh: [
    8, 8, 8, 8, 8, 8, 9, 9,
    10, 10, 11, 12, 12, 13, 13, 14,
    15, 15, 14, 12, 11, 10, 9, 9,
  ],
  battery: {
    capacity_kwh: 100,
    initial_energy_kwh: 40,
    minimum_energy_kwh: 10,
    max_charge_kwh_per_hour: 25,
    max_discharge_kwh_per_hour: 25,
  },
  operator_notes: [
    "Reduce solar from 1 PM to 3 PM by 80%",
    "Do not charge the battery from 6 PM to 8 PM",
  ],
};
