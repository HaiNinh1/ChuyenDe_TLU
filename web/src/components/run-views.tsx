import { useEffect, useRef, useState } from "react"
import {
  Bug,
  ChevronRight,
  CircleCheck,
  Dna,
  Download,
  GitCompare,
  Lightbulb,
  PencilLine,
  Terminal,
} from "lucide-react"

import { CodeViewer, DiffViewer } from "@/components/code-viewer"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Slider } from "@/components/ui/slider"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { ACTION_LABELS, PHASE_LABELS, fmtPct, type Iteration, type Summary } from "@/lib/api"
import { cn } from "@/lib/utils"

// ------------------------------------------------------------------ chỉ số nhỏ có so sánh với vòng trước
function Delta({ now, prev }: { now: number | null; prev: number | null | undefined }) {
  if (now === null || prev === null || prev === undefined) return null
  const d = Math.round((now - prev) * 10) / 10
  if (d === 0) return null
  return (
    <span className={cn("ml-1 text-[11px] tabular-nums", d > 0 ? "text-success" : "text-destructive")}>
      {d > 0 ? "+" : ""}
      {d}
    </span>
  )
}

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] tracking-wide text-muted-foreground uppercase">{label}</div>
      <div className="mt-0.5 font-mono text-sm font-medium tabular-nums">{children}</div>
    </div>
  )
}

const phaseStyle: Record<string, string> = {
  repair: "border-warning/40 bg-warning/10 text-warning",
  coverage: "border-chart-1/40 bg-chart-1/10 text-chart-1",
  mutation: "border-chart-3/40 bg-chart-3/10 text-chart-3",
  done: "border-success/40 bg-success/10 text-success",
}

/** Một vòng lặp trên dòng thời gian. */
export function IterationItem({ it, prev, last }: { it: Iteration; prev?: Iteration; last: boolean }) {
  const failing = it.failed + it.errors
  return (
    <li className="relative flex gap-4 pb-6">
      {!last && <span className="absolute top-8 bottom-0 left-[15px] w-px bg-border" aria-hidden />}
      <div
        className={cn(
          "relative z-10 flex size-8 shrink-0 items-center justify-center rounded-full border bg-card font-mono text-xs font-semibold",
          it.phase === "done" && "border-success text-success"
        )}
      >
        {it.phase === "done" ? <CircleCheck className="size-4" /> : it.iteration}
      </div>

      <div className="min-w-0 flex-1 rounded-lg border bg-card p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{ACTION_LABELS[it.action] ?? it.action}</span>
          <Badge variant="outline" className={phaseStyle[it.phase]}>
            {PHASE_LABELS[it.phase] ?? it.phase}
          </Badge>
          <span className="ml-auto font-mono text-xs text-muted-foreground tabular-nums">
            Vòng {it.iteration} · {it.elapsed}s · {it.llm_calls_so_far} lần gọi LLM
          </span>
        </div>
        <p className="mt-1.5 text-sm text-muted-foreground">{it.reason}</p>

        <div className="mt-3 grid grid-cols-2 gap-3 rounded-md bg-muted/50 px-3 py-2.5 sm:grid-cols-4">
          <Metric label="Pass / Fail">
            <span className="text-success">{it.passed}</span>
            <span className="text-muted-foreground"> / </span>
            <span className={failing ? "text-destructive" : ""}>{failing}</span>
            {it.xfailed > 0 && <span className="text-muted-foreground"> · {it.xfailed} xfail</span>}
          </Metric>
          <Metric label="Line cov.">
            {it.line_coverage}%<Delta now={it.line_coverage} prev={prev?.line_coverage} />
          </Metric>
          <Metric label="Branch cov.">
            {it.branch_coverage}%<Delta now={it.branch_coverage} prev={prev?.branch_coverage} />
          </Metric>
          <Metric label="Mutation">
            {fmtPct(it.mutation_score)}
            <Delta now={it.mutation_score} prev={prev?.mutation_score} />
            {it.mutants_total > 0 && (
              <span className="ml-1 text-[11px] text-muted-foreground">
                ({it.mutants_killed}/{it.mutants_total})
              </span>
            )}
          </Metric>
        </div>

        {it.classifications?.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {it.classifications.map((c, k) => {
              const bug = c.verdict === "SUSPECTED_BUG"
              return (
                <li key={k} className="flex gap-2 text-sm">
                  {bug ? (
                    <Bug className="mt-0.5 size-4 shrink-0 text-destructive" />
                  ) : (
                    <PencilLine className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  )}
                  <div className="min-w-0">
                    <code className="font-mono text-xs break-all">{c.test}</code>
                    <Badge variant={bug ? "destructive" : "secondary"} className="ml-2 align-middle">
                      {c.verdict}
                    </Badge>
                    <div className="text-xs text-muted-foreground">{c.reason}</div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}

        {it.survived_mutants?.length > 0 && (
          <Collapsible className="mt-3">
            <CollapsibleTrigger className="group flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
              <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
              <Dna className="size-4" /> {it.survived_mutants.length} mutant còn sống
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-1.5">
              {it.survived_mutants.map((m, k) => (
                <pre key={k} className="overflow-x-auto rounded-md border bg-muted/40 px-3 py-2 font-mono text-xs">
                  {m}
                </pre>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {it.lesson && (
          <div className="mt-3 flex gap-2 rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
            <Lightbulb className="mt-0.5 size-3.5 shrink-0" />
            <span>
              <span className="font-medium text-foreground">Bài học: </span>
              {it.lesson}
            </span>
          </div>
        )}
      </div>
    </li>
  )
}

export function Timeline({ iterations }: { iterations: Iteration[] }) {
  return (
    <ol>
      {iterations.map((it, i) => (
        <IterationItem key={i} it={it} prev={iterations[i - 1]} last={i === iterations.length - 1} />
      ))}
    </ol>
  )
}

/** Nhật ký thông báo của agent khi đang chạy. */
export function LiveLog({ messages, running }: { messages: string[]; running: boolean }) {
  // Luôn cuộn xuống thông báo mới nhất
  const boxRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight })
  }, [messages.length])
  return (
    <Card size="sm" className="gap-0 py-0">
      <div className="flex items-center gap-2 border-b px-4 py-2.5 text-sm">
        {running ? <Spinner className="size-4" /> : <Terminal className="size-4 text-muted-foreground" />}
        <span className="font-medium">{running ? "Agent đang làm việc" : "Nhật ký agent"}</span>
        <span className="ml-auto text-xs text-muted-foreground">{messages.length} thông báo</span>
      </div>
      <div ref={boxRef} className="h-36 overflow-y-auto">
        <div className="space-y-0.5 px-4 py-2 font-mono text-xs">
          {messages.map((m, k) => (
            <div key={k} className={cn("text-muted-foreground", k === messages.length - 1 && "text-foreground")}>
              <span className="mr-2 opacity-50 select-none">›</span>
              {m}
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}

// ------------------------------------------------------------------ tổng kết
function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="bg-card px-4 py-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>}
    </div>
  )
}

export function SummaryPanel({ summary }: { summary: Summary }) {
  const { final, stats } = summary
  const bugs = Object.entries(summary.suspected_bugs ?? {})
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Line coverage" value={`${final.line_coverage}%`} />
        <Kpi label="Branch coverage" value={`${final.branch_coverage}%`} />
        <Kpi label="Mutation score" value={fmtPct(final.mutation_score)} />
        <Kpi label="Test pass" value={`${final.passed}`} hint={final.xfailed ? `${final.xfailed} gắn nhãn nghi bug` : undefined} />
        <Kpi label="Gọi LLM" value={`${stats.llm_calls}`} hint={`${final.num_iterations} vòng`} />
        <Kpi label="Thời gian" value={`${stats.total_seconds}s`} hint={`LLM ${stats.llm_seconds}s`} />
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5 text-foreground">
          <CircleCheck className="size-3.5 text-success" /> {summary.stop_reason}
        </span>
        <span>{summary.tools}</span>
        <span className="font-mono">
          {summary.llm.provider}/{summary.llm.model}
        </span>
        {summary.log_path && <span className="font-mono">{summary.log_path.split(/[\\/]/).pop()}</span>}
      </div>
      {bugs.length > 0 && (
        <Alert variant="destructive">
          <Bug />
          <AlertTitle>Nghi phát hiện bug trong code ({bugs.length} test) — cần người kiểm tra</AlertTitle>
          <AlertDescription>
            <ul className="mt-1 space-y-1">
              {bugs.map(([name, reason]) => (
                <li key={name}>
                  <code className="font-mono text-xs">{name}</code>: {reason}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ code test từng vòng
export function TestCodePanel({ summary }: { summary: Summary }) {
  const views = summary.code_views
  const [idx, setIdx] = useState(views.length - 1)
  const [diff, setDiff] = useState(false)
  const view = views[Math.min(idx, views.length - 1)]
  if (!view) return null

  const download = () => {
    const url = URL.createObjectURL(new Blob([view.code], { type: "text/plain" }))
    const a = Object.assign(document.createElement("a"), { href: url, download: summary.test_file_name })
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-mono text-sm">{summary.test_file_name}</CardTitle>
        <CardDescription>
          Vòng {idx} / {views.length - 1} · {view.valid ? `${view.num_tests} test` : "lỗi cú pháp"} ·{" "}
          {view.code.split("\n").length} dòng
          {view.suspected.length > 0 && (
            <span className="text-destructive"> · {view.suspected.length} test SUSPECTED_BUG</span>
          )}
        </CardDescription>
        <CardAction className="flex items-center gap-3">
          {idx > 0 && (
            <div className="flex items-center gap-2">
              <Switch id="diff" checked={diff} onCheckedChange={setDiff} />
              <Label htmlFor="diff" className="text-xs font-normal">
                <GitCompare className="size-3.5" /> Diff
              </Label>
            </div>
          )}
          <Button variant="outline" size="sm" onClick={download}>
            <Download /> Tải file
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        {views.length > 1 && (
          <div className="flex items-center gap-4">
            <span className="text-xs text-muted-foreground">Vòng</span>
            <Slider value={[idx]} min={0} max={views.length - 1} step={1} onValueChange={([v]) => setIdx(v)} />
            <span className="font-mono text-xs tabular-nums">{idx}</span>
          </div>
        )}
        {view.suspected.length > 0 && !diff && (
          <p className="rounded-md border-l-2 border-destructive bg-destructive/5 px-3 py-2 text-xs">
            Các dòng tô đỏ thuộc test được agent <b>giữ lại</b> và gắn nhãn SUSPECTED_BUG (không sửa test cho khớp
            code): <span className="font-mono">{view.suspected.join(", ")}</span>
          </p>
        )}
        {diff && idx > 0 ? (
          <DiffViewer before={views[idx - 1].code} after={view.code} />
        ) : (
          <CodeViewer code={view.code} language={summary.fence} spans={view.spans} className="max-h-[640px]" />
        )}
      </CardContent>
    </Card>
  )
}
