"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";
import { CHART_COLORS_HEX } from "@/lib/constants";

/* ── Types ──────────────────────────────────────────────────────── */
interface TooltipPayloadItem {
  value: number;
  name: string;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

interface StatusChartDatum {
  name: string;
  count: number;
}

interface TimeChartDatum {
  date: string;
  count: number;
}

interface LabelCountDatum {
  label: string;
  count: number;
}

export interface DashboardChartsProps {
  statusChartData: StatusChartDatum[];
  jobsOverTime: TimeChartDatum[];
  topLocations: LabelCountDatum[];
  topCompanies: LabelCountDatum[];
}

/* ── Shared chart tooltip ─────────────────────────────────────── */
function ChartTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-border rounded-lg px-3 py-2 shadow-lg">
      {label && <p className="text-[11px] text-text-tertiary mb-1">{label}</p>}
      {payload.map((entry) => (
        <p
          key={entry.name}
          className="text-[12px] font-medium"
          style={{ color: entry.color }}
        >
          {entry.value}
        </p>
      ))}
    </div>
  );
}

/**
 * Recharts visualisations extracted into a separate file so the entire
 * recharts library can be code-split via `next/dynamic`.
 */
export function DashboardCharts({
  statusChartData,
  jobsOverTime,
  topLocations,
  topCompanies,
}: DashboardChartsProps) {
  return (
    <section className="grid grid-cols-1 xl:grid-cols-2 gap-5">
      {/* Pipeline by status */}
      <div className="bg-white border border-border rounded-xl p-5 shadow-sm">
        <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-widest mb-4">
          Pipeline by Status
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={statusChartData}
            margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(0,0,0,0.06)"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: "rgba(0,0,0,0.45)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "rgba(0,0,0,0.45)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              content={<ChartTooltip />}
              cursor={{ fill: "rgba(0,0,0,0.04)" }}
            />
            <Bar
              dataKey="count"
              fill={CHART_COLORS_HEX[0]}
              radius={[4, 4, 0, 0]}
              opacity={0.9}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Jobs over time */}
      <div className="bg-white border border-border rounded-xl p-5 shadow-sm">
        <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-widest mb-4">
          Jobs Over Time
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart
            data={jobsOverTime}
            margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(0,0,0,0.06)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fill: "rgba(0,0,0,0.45)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "rgba(0,0,0,0.45)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<ChartTooltip />} />
            <Line
              type="monotone"
              dataKey="count"
              stroke={CHART_COLORS_HEX[0]}
              strokeWidth={2}
              dot={{ fill: CHART_COLORS_HEX[0], r: 3, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: CHART_COLORS_HEX[0] }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Top locations */}
      <div className="bg-white border border-border rounded-xl p-5 shadow-sm">
        <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-widest mb-4">
          Top Locations
        </h3>
        {topLocations.length === 0 ? (
          <p className="text-sm text-text-tertiary">No location data.</p>
        ) : (
          <div className="space-y-3">
            {topLocations.map(({ label, count }) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-sm text-text-secondary w-44 truncate font-medium">
                  {label}
                </span>
                <div className="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(count / (topLocations[0]?.count ?? 1)) * 100}%`,
                      background: CHART_COLORS_HEX[0],
                      opacity: 0.75,
                    }}
                  />
                </div>
                <span className="text-sm text-text-tertiary tabular-nums w-6 text-right font-medium">
                  {count}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top companies */}
      <div className="bg-white border border-border rounded-xl p-5 shadow-sm">
        <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-widest mb-4">
          Top Companies
        </h3>
        {topCompanies.length === 0 ? (
          <p className="text-sm text-text-tertiary">No company data.</p>
        ) : (
          <div className="space-y-3">
            {topCompanies.map(({ label, count }) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-sm text-text-secondary w-44 truncate font-medium">
                  {label}
                </span>
                <div className="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(count / (topCompanies[0]?.count ?? 1)) * 100}%`,
                      background: CHART_COLORS_HEX[1],
                      opacity: 0.75,
                    }}
                  />
                </div>
                <span className="text-sm text-text-tertiary tabular-nums w-6 text-right font-medium">
                  {count}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
