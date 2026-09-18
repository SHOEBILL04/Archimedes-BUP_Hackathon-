export type DirectiveType =
  | "solar_reduction"
  | "minimum_battery_reserve"
  | "no_charge_window"
  | "no_discharge_window"
  | "max_grid_window"
  | "no_op";

export interface BatteryParameters {
  capacity_kwh: number;
  initial_energy_kwh: number;
  minimum_energy_kwh: number;
  max_charge_kwh_per_hour: number;
  max_discharge_kwh_per_hour: number;
}

export interface EnergyScenario {
  demand_kwh: number[];
  base_solar_kwh: number[];
  tariff_bdt_per_kwh: number[];
  battery: BatteryParameters;
  operator_notes: string[];
}

export interface DirectiveInterpretation {
  note_index: number;
  directive_type: DirectiveType;
  structured_adjustment?: Record<string, unknown> | null;
  applies: boolean;
}

export interface HourSchedule {
  hour: number;
  demand_kwh: number;
  effective_solar_kwh: number;
  solar_used_kwh: number;
  battery_charge_kwh: number;
  battery_discharge_kwh: number;
  battery_energy_after_kwh: number;
  grid_kwh: number;
  tariff_bdt_per_kwh: number;
  grid_cost_bdt: number;
}

export interface VerificationResult {
  verified: boolean;
  max_constraint_error: number;
  total_grid_cost_bdt: number;
}

export interface OptimizationResponse {
  directive_interpretation: DirectiveInterpretation[];
  schedule: HourSchedule[];
  total_grid_cost_bdt: number;
  total_grid_kwh: number;
  verification: VerificationResult;
  status_message?: string;
}
