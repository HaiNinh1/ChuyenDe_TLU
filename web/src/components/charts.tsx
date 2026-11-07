import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import type { CsvRow, Iteration } from "@/lib/api"

// Màu theo CHỈ SỐ (không theo thứ tự xuất hiện): line = chart-1, branch = chart-2, mutation = chart-3
const metricConfig = {
  line: { label: "Line coverage", color: "var(--chart-1)" },
  branch: { label: "Branch coverage", color: "var(--chart-2)" },
  mutation: { label: "Mutation score", color: "var(--chart-3)" },
} satisfies ChartConfig
const ORDER = ["line", "branch", "mutation"]

/** Coverage và mutation score qua các vòng lặp. */
export function ProgressChart({ iterations, className }: { iterations: Iteration[]; className?: string }) {
  const data = iterations.map((it) => ({
    round: `Vòng ${it.iteration}`,
    line: it.line_coverage,
    branch: it.branch_coverage,
    mutation: it.mutation_score,
  }))
  const hasMutation = iterations.some((it) => it.mutation_score !== null)

  return (
    <ChartContainer config={metricConfig} className={className ?? "aspect-auto h-[300px] w-full"}>
      <LineChart data={data} margin={{ top: 12, right: 16, left: 4, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="round" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tickMargin={8} unit="%" width={52} />
        <ChartTooltip cursor={{ strokeDasharray: "3 3" }} content={<ChartTooltipContent indicator="line" />} />
        <ChartLegend content={<ChartLegendContent />} itemSorter={(item) => ORDER.indexOf(String(item.dataKey))} />
        {(["line", "branch", "mutation"] as const)
          .filter((k) => k !== "mutation" || hasMutation)
          .map((key) => (
            <Line
              key={key}
              dataKey={key}
              type="monotone"
              stroke={`var(--color-${key})`}
              strokeWidth={2}
              // line và branch thường trùng nhau -> branch nét đứt để vẫn thấy cả hai đường
              strokeDasharray={key === "branch" ? "6 4" : undefined}
              dot={{ r: 4, strokeWidth: 2, stroke: "var(--card)", fill: `var(--color-${key})` }}
              activeDot={{ r: 5 }}
              connectNulls
              isAnimationActive={false}
            />
          ))}
      </LineChart>
    </ChartContainer>
  )
}

const resultConfig = {
  line_coverage: { label: "Line coverage", color: "var(--chart-1)" },
  branch_coverage: { label: "Branch coverage", color: "var(--chart-2)" },
  mutation_score: { label: "Mutation (held-out)", color: "var(--chart-3)" },
} satisfies ChartConfig

/** So sánh 4 cấu hình thực nghiệm A/B/C/D của một ngôn ngữ. */
export function ConfigChart({ rows }: { rows: CsvRow[] }) {
  const data = rows.map((r) => ({
    config: r.config.split(":")[0],
    name: r.config,
    line_coverage: Number(r.line_coverage),
    branch_coverage: Number(r.branch_coverage),
    mutation_score: r.mutation_score === "" ? null : Number(r.mutation_score),
  }))
  // Trục y bắt đầu từ 0 để không phóng đại chênh lệch nhỏ giữa các cấu hình
  return (
    <ChartContainer config={resultConfig} className="aspect-auto h-[280px] w-full">
      <BarChart data={data} barGap={2} barCategoryGap="22%" margin={{ top: 12, right: 8, left: 4, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="config" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis domain={[0, 100]} tickLine={false} axisLine={false} unit="%" width={52} />
        <ChartTooltip
          cursor={{ fill: "var(--muted)", opacity: 0.5 }}
          content={
            <ChartTooltipContent labelFormatter={(_, payload) => payload?.[0]?.payload?.name ?? ""} />
          }
        />
        <ChartLegend
          content={<ChartLegendContent />}
          itemSorter={(item) => Object.keys(resultConfig).indexOf(String(item.dataKey))}
        />
        {(Object.keys(resultConfig) as (keyof typeof resultConfig)[]).map((key) => (
          <Bar key={key} dataKey={key} fill={`var(--color-${key})`} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        ))}
      </BarChart>
    </ChartContainer>
  )
}
