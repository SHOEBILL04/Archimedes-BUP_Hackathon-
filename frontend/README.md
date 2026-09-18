# Smart Campus Energy Optimization Platform - Frontend

Modern, high-performance Next.js App Router frontend with TypeScript, Tailwind CSS, shadcn/ui primitives, and Recharts data visualization.

## Architecture

- **`app/`**: Next.js App Router pages and API routes (`/`, `/dashboard`, `/api/health`).
- **`components/ui/`**: Reusable base primitives (`Card`, `Button`, `Badge`) with sleek dark theme and glassmorphism.
- **`components/layout/`**: Structural layout components (`Sidebar`, `Header`, `PageContainer`).
- **`components/energy/`**: Energy domain components (`ScenarioForm`, `OptimizationSummary`, `ScheduleTable`).
- **`components/charts/`**: Reactive telemetry visualizations (`DemandChart`, `SolarChart`, `BatteryChart`).
- **`lib/api/`**: Typed `apiClient` communicating with FastAPI backend via HTTP.
- **`types/`**: Strict TypeScript interfaces for scenarios, schedules, and API envelopes.

## Local Development

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

### 3. Run Development Server

```bash
npm run dev
```

The frontend will be available at: `http://localhost:3000`

### 4. Lint and Type Check

```bash
npm run lint
npx tsc --noEmit
```
