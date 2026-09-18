export interface HealthStatusResponse {
  status: "ok" | string;
}

export interface ApiErrorResponse {
  detail: string;
  code?: string;
  context?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}
