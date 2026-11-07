import { ChevronRight, Info } from "lucide-react"

import { ConfigChart } from "@/components/charts"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { CsvRow, Meta, Results } from "@/lib/api"

type Column = { key: string; label: string; unit?: string }

const SUMMARY_COLS: Column[] = [
  { key: "config", label: "Cấu hình" },
  { key: "line_coverage", label: "Line", unit: "%" },
  { key: "branch_coverage", label: "Branch", unit: "%" },
  { key: "mutation_score", label: "Mutation held-out", unit: "%" },
  { key: "mutation_all", label: "Mutation tất cả", unit: "%" },
  { key: "iterations", label: "Vòng" },
  { key: "llm_calls", label: "Gọi LLM" },
  { key: "seconds", label: "Giây" },
  { key: "tests_total", label: "Số test" },
  { key: "bug_detection_rate", label: "Phát hiện bug", unit: "%" },
]

const MODULE_COLS: Column[] = [
  { key: "module", label: "Module" },
  { key: "config", label: "Cấu hình" },
  { key: "line_coverage", label: "Line", unit: "%" },
  { key: "branch_coverage", label: "Branch", unit: "%" },
  { key: "mutation_score", label: "Mutation held-out", unit: "%" },
  { key: "mutation_all", label: "Mutation tất cả", unit: "%" },
  { key: "llm_calls", label: "Gọi LLM" },
  { key: "bug_detected", label: "Bắt được bug" },
]

const RUN_COLS: Column[] = [
  { key: "module", label: "Module" },
  { key: "config", label: "Cấu hình" },
  { key: "run", label: "Lượt" },
  { key: "line_coverage", label: "Line", unit: "%" },
  { key: "mutation_score", label: "Held-out", unit: "%" },
  { key: "mutation_all", label: "Tất cả", unit: "%" },
  { key: "mutants_heldout", label: "Mutant held-out" },
  { key: "llm_calls", label: "LLM" },
  { key: "suspected", label: "Nghi bug" },
  { key: "stop_reason", label: "Lý do dừng" },
]

function DataTable({ rows, cols }: { rows: CsvRow[]; cols: Column[] }) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow>
            {cols.map((c, i) => (
              <TableHead key={c.key} className={i === 0 ? "" : "text-right"}>
                {c.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, k) => (
            <TableRow key={k}>
              {cols.map((c, i) => (
                <TableCell
                  key={c.key}
                  className={i === 0 ? "font-medium" : "text-right font-mono text-xs tabular-nums"}
                >
                  {r[c.key] === "" || r[c.key] === undefined ? "—" : `${r[c.key]}${c.unit ?? ""}`}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function Section({ title, count, children }: { title: string; count: number; children: React.ReactNode }) {
  return (
    <Collapsible>
      <CollapsibleTrigger className="group flex w-full items-center gap-2 rounded-md py-2 text-sm font-medium hover:text-foreground">
        <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
        {title}
        <Badge variant="secondary">{count}</Badge>
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2">{children}</CollapsibleContent>
    </Collapsible>
  )
}

export function ResultsView({ results, meta }: { results: Results | null; meta: Meta | null }) {
  if (!results || results.summary.length === 0) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyTitle>Chưa có kết quả thực nghiệm</EmptyTitle>
          <EmptyDescription>
            Chạy <code className="font-mono">python evaluate.py --quick</code> hoặc{" "}
            <code className="font-mono">python evaluate.py --runs 3</code>.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const languages = [...new Set(results.summary.map((r) => r.language || "python"))]
  const name = (lang: string) => meta?.languages.find((l) => l.name === lang)?.display_name ?? lang
  const of = (rows: CsvRow[], lang: string) => rows.filter((r) => (r.language || "python") === lang)

  return (
    <Tabs defaultValue={languages[0]} className="gap-4">
      <TabsList>
        {languages.map((l) => (
          <TabsTrigger key={l} value={l}>
            {name(l)}
          </TabsTrigger>
        ))}
      </TabsList>
      {languages.map((lang) => {
        const rows = of(results.summary, lang)
        const first = rows[0]
        return (
          <TabsContent key={lang} value={lang} className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>So sánh 4 cấu hình — {name(lang)}</CardTitle>
                <CardDescription>
                  A: sinh một lần · B: + vòng lặp coverage · C: B + mutation · D: C + bộ nhớ. Trung bình trên{" "}
                  {first?.n_modules} module × {first?.n_runs} lượt chạy.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ConfigChart rows={rows} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Bảng trung bình theo cấu hình</CardTitle>
                <CardDescription className="flex gap-1.5">
                  <Info className="mt-0.5 size-3.5 shrink-0" />
                  Mutation held-out chỉ chấm trên các mutant LLM chưa từng thấy trong prompt; cột "tất cả" để thấy mức
                  chênh.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <DataTable rows={rows} cols={SUMMARY_COLS} />
                <Section title="Chi tiết theo module" count={of(results.by_module, lang).length}>
                  <DataTable rows={of(results.by_module, lang)} cols={MODULE_COLS} />
                </Section>
                <Section title="Dữ liệu thô từng lần chạy" count={of(results.runs, lang).length}>
                  <DataTable rows={of(results.runs, lang)} cols={RUN_COLS} />
                </Section>
              </CardContent>
            </Card>
          </TabsContent>
        )
      })}
      <p className="text-xs text-muted-foreground">
        Nguồn: <code className="font-mono">results/*.csv</code> do <code className="font-mono">python evaluate.py</code>{" "}
        tạo ra. Quy mô nhỏ (giới hạn request của model miễn phí) — xem phần hạn chế trong HOC_TAP.md.
      </p>
    </Tabs>
  )
}
