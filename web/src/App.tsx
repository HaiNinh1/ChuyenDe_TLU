import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTheme } from "next-themes"
import { toast } from "sonner"
import { Activity, ChartLine, FileCode2, FlaskConical, History, Moon, Play, Sun, TestTubes } from "lucide-react"

import { AppSidebar, type Mode } from "@/components/app-sidebar"
import { ProgressChart } from "@/components/charts"
import { CodeViewer } from "@/components/code-viewer"
import { ResultsView } from "@/components/results-view"
import { LiveLog, SummaryPanel, TestCodePanel, Timeline } from "@/components/run-views"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, fmtPct, runAgent, type Iteration, type LogItem, type Meta, type Results, type RunRequest, type Summary } from "@/lib/api"

const DEFAULT_FORM: RunRequest = {
  source_kind: "sample",
  language: "python",
  file: "grading.py",
  code: "",
  ext: ".py",
  module_name: "user_module",
  use_mutation: true,
  use_memory: false,
  max_iterations: 6,
  line_threshold: 95,
  branch_threshold: 90,
  mutation_threshold: 80,
  max_mutants: 20,
  provider: "mock",
  model: "mock",
}

const FENCE_BY_EXT: Record<string, string> = { ".py": "python", ".js": "javascript", ".ts": "typescript" }
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

function NoData({ text }: { text: string }) {
  return (
    <Empty className="border border-dashed">
      <EmptyHeader>
        <EmptyTitle className="text-sm font-normal text-muted-foreground">{text}</EmptyTitle>
      </EmptyHeader>
    </Empty>
  )
}

export default function App() {
  const { resolvedTheme, setTheme } = useTheme()
  const [meta, setMeta] = useState<Meta | null>(null)
  const [logs, setLogs] = useState<LogItem[]>([])
  const [results, setResults] = useState<Results | null>(null)
  const [mode, setMode] = useState<Mode>("run")
  const [form, setForm] = useState<RunRequest>(DEFAULT_FORM)
  const [detectedExt, setDetectedExt] = useState(".py")
  const [selectedLog, setSelectedLog] = useState("")
  const [speed, setSpeed] = useState(1)
  const [source, setSource] = useState<{ code: string; fence: string } | null>(null)

  // Trạng thái một lần chạy / phát lại
  const [busy, setBusy] = useState<"run" | "replay" | null>(null)
  const [live, setLive] = useState<Iteration[]>([])
  const [messages, setMessages] = useState<string[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [tab, setTab] = useState("progress")
  const abortRef = useRef<AbortController | null>(null)
  const replayStop = useRef(false)

  const patchForm = useCallback((patch: Partial<RunRequest>) => setForm((f) => ({ ...f, ...patch })), [])

  // Tải dữ liệu ban đầu
  useEffect(() => {
    api
      .meta()
      .then((m) => {
        setMeta(m)
        const py = m.languages.find((l) => l.name === "python") ?? m.languages[0]
        setForm((f) => ({
          ...f,
          language: py?.name ?? f.language,
          file: py?.files.includes("grading.py") ? "grading.py" : (py?.files[0] ?? ""),
          provider: m.default_provider,
          model: m.default_model,
        }))
      })
      .catch((e) => toast.error(`Không kết nối được server: ${e.message}`, { description: "Hãy chạy python server.py" }))
    api.logs().then((l) => {
      setLogs(l)
      setSelectedLog(l[0]?.name ?? "")
    })
    api.results().then(setResults)
  }, [])

  // Tự nhận diện ngôn ngữ của code dán vào
  useEffect(() => {
    if (form.source_kind !== "paste" || !form.code.trim()) return
    const t = setTimeout(() => {
      api.detect(form.code).then(({ ext }) => {
        setDetectedExt(ext)
        patchForm({ ext })
      })
    }, 400)
    return () => clearTimeout(t)
  }, [form.code, form.source_kind, patchForm])

  // Mã nguồn module đang chọn
  useEffect(() => {
    if (mode !== "run" || form.source_kind !== "sample" || !form.file) return
    api.source(form.language, form.file).then(setSource).catch(() => setSource(null))
  }, [mode, form.source_kind, form.language, form.file])

  const language = useMemo(() => {
    if (!meta) return undefined
    const name = form.source_kind === "paste" ? (form.ext === ".py" ? "python" : "javascript") : form.language
    return meta.languages.find((l) => l.name === name)
  }, [meta, form.source_kind, form.ext, form.language])

  const canRun =
    !!language?.env.ok &&
    (form.source_kind === "sample" ? !!form.file : !!form.code.trim() && /^[a-z_][a-z0-9_]*$/.test(form.module_name))

  const reset = () => {
    setLive([])
    setMessages([])
    setSummary(null)
    setTab("progress")
  }

  const onRun = async () => {
    reset()
    setBusy("run")
    const controller = new AbortController()
    abortRef.current = controller
    try {
      await runAgent(
        { ...form, use_mutation: form.use_mutation && !!language?.env.mutation_available },
        (e) => {
          if (e.event === "message") setMessages((m) => [...m, e.data])
          else if (e.event === "iteration") setLive((l) => [...l, e.data])
          else if (e.event === "summary") {
            setSummary(e.data)
            toast.success("Agent đã chạy xong", { description: e.data.stop_reason })
            api.logs().then(setLogs)
          } else if (e.event === "error") toast.error("Agent gặp lỗi", { description: e.data })
        },
        controller.signal
      )
    } catch (e) {
      if (!controller.signal.aborted) toast.error("Không chạy được agent", { description: (e as Error).message })
    } finally {
      setBusy(null)
    }
  }

  const onReplay = async () => {
    if (!selectedLog) return
    reset()
    setBusy("replay")
    replayStop.current = false
    try {
      const s = await api.log(selectedLog)
      setMessages([`Phát lại ${selectedLog} — không gọi LLM, không cần mạng`])
      for (const it of s.iterations) {
        if (replayStop.current) break
        setLive((l) => [...l, it])
        await sleep(speed * 1000)
      }
      setSummary(s)
    } catch (e) {
      toast.error("Không đọc được log", { description: (e as Error).message })
    } finally {
      setBusy(null)
    }
  }

  const onStop = () => {
    abortRef.current?.abort() // chỉ ngừng nhận dữ liệu; tiến trình agent trên server vẫn chạy nốt
    replayStop.current = true
  }

  const iterations = summary?.iterations ?? live
  const title =
    summary?.module_path?.split(/[\\/]/).pop() ??
    (mode === "replay"
      ? selectedLog
      : form.source_kind === "sample"
        ? form.file
        : `${form.module_name}${form.ext}`)

  // Mã nguồn hiển thị ở tab "Mã nguồn"
  const shownSource =
    summary?.source_code && (mode === "replay" || busy === null)
      ? { code: summary.source_code, fence: summary.fence }
      : mode === "run" && form.source_kind === "paste"
        ? { code: form.code, fence: FENCE_BY_EXT[form.ext] }
        : mode === "run"
          ? source
          : null

  return (
    <SidebarProvider style={{ "--sidebar-width": "19rem" } as React.CSSProperties}>
      <AppSidebar
        meta={meta}
        mode={mode}
        onModeChange={setMode}
        form={form}
        onFormChange={patchForm}
        detectedExt={detectedExt}
        language={language}
        logs={logs}
        selectedLog={selectedLog}
        onSelectLog={setSelectedLog}
        speed={speed}
        onSpeedChange={setSpeed}
        busy={busy !== null}
        canRun={canRun}
        onRun={onRun}
        onReplay={onReplay}
        onStop={onStop}
      />
      <SidebarInset className="min-w-0">
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-5" />
          <div className="flex min-w-0 items-center gap-2">
            <span className="hidden text-sm text-muted-foreground sm:inline">
              {mode === "replay" ? "Replay" : "Chạy mới"}
            </span>
            <span className="hidden text-muted-foreground sm:inline">/</span>
            <span className="truncate font-mono text-sm font-medium">{title}</span>
            {busy && (
              <Badge variant="outline" className="gap-1.5">
                <span className="size-1.5 animate-pulse rounded-full bg-primary" />
                {busy === "run" ? "Đang chạy" : "Đang phát lại"}
              </Badge>
            )}
          </div>
          <div className="ml-auto flex items-center gap-2">
            {language && mode === "run" && (
              <Badge variant="secondary" className="hidden md:inline-flex">
                {language.display_name}
              </Badge>
            )}
            <Button
              variant="ghost"
              size="icon"
              aria-label="Đổi giao diện sáng/tối"
              onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            >
              {resolvedTheme === "dark" ? <Sun /> : <Moon />}
            </Button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8">
          <Tabs value={tab} onValueChange={setTab} className="gap-6">
            <TabsList variant="line" className="w-full justify-start gap-1 overflow-x-auto border-b pb-0 [&>button]:flex-none [&>button]:px-3">
              <TabsTrigger value="progress">
                <Activity /> Tiến trình
              </TabsTrigger>
              <TabsTrigger value="chart">
                <ChartLine /> Biểu đồ
              </TabsTrigger>
              <TabsTrigger value="code">
                <TestTubes /> Code test
              </TabsTrigger>
              <TabsTrigger value="source">
                <FileCode2 /> Mã nguồn
              </TabsTrigger>
              <TabsTrigger value="results">
                <FlaskConical /> Kết quả thực nghiệm
              </TabsTrigger>
            </TabsList>

            <TabsContent value="progress" className="space-y-6">
              {busy || iterations.length > 0 ? (
                <>
                  {summary && <SummaryPanel summary={summary} />}
                  {(busy || messages.length > 0) && !summary && <LiveLog messages={messages} running={!!busy} />}
                  {iterations.length >= 2 && !summary && (
                    <Card>
                      <CardContent>
                        <ProgressChart iterations={iterations} className="aspect-auto h-[220px] w-full" />
                      </CardContent>
                    </Card>
                  )}
                  <div>
                    <h2 className="mb-4 text-sm font-medium text-muted-foreground">
                      Các vòng lặp ({iterations.length})
                    </h2>
                    <Timeline iterations={iterations} />
                  </div>
                </>
              ) : (
                <Empty className="border border-dashed py-16">
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <TestTubes />
                    </EmptyMedia>
                    <EmptyTitle>Chưa có lần chạy nào</EmptyTitle>
                    <EmptyDescription>
                      Chọn ngôn ngữ và module ở thanh bên rồi bấm <b>Chạy agent</b>, hoặc phát lại một lần chạy đã lưu
                      (không cần mạng).
                    </EmptyDescription>
                  </EmptyHeader>
                  <EmptyContent className="flex-row justify-center gap-2">
                    <Button disabled={!canRun || mode !== "run"} onClick={onRun}>
                      <Play /> Chạy agent
                    </Button>
                    <Button variant="outline" onClick={() => setMode("replay")}>
                      <History /> Chế độ replay
                    </Button>
                  </EmptyContent>
                </Empty>
              )}
            </TabsContent>

            <TabsContent value="chart" className="space-y-6">
              {iterations.length > 0 ? (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle>Coverage và mutation score qua các vòng</CardTitle>
                      <CardDescription>Mutation score chỉ có sau khi agent chuyển sang pha mutation.</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ProgressChart iterations={iterations} />
                    </CardContent>
                  </Card>
                  <div className="overflow-hidden rounded-lg border">
                    <Table>
                      <TableHeader className="bg-muted/50">
                        <TableRow>
                          <TableHead>Vòng</TableHead>
                          <TableHead className="text-right">Line</TableHead>
                          <TableHead className="text-right">Branch</TableHead>
                          <TableHead className="text-right">Mutation</TableHead>
                          <TableHead className="text-right">Test pass</TableHead>
                          <TableHead className="text-right">Gọi LLM (cộng dồn)</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody className="font-mono text-xs tabular-nums">
                        {iterations.map((it) => (
                          <TableRow key={it.iteration}>
                            <TableCell>{it.iteration}</TableCell>
                            <TableCell className="text-right">{it.line_coverage}%</TableCell>
                            <TableCell className="text-right">{it.branch_coverage}%</TableCell>
                            <TableCell className="text-right">{fmtPct(it.mutation_score)}</TableCell>
                            <TableCell className="text-right">{it.passed}</TableCell>
                            <TableCell className="text-right">{it.llm_calls_so_far}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </>
              ) : (
                <NoData text="Chưa có dữ liệu. Hãy chạy agent hoặc replay một log." />
              )}
            </TabsContent>

            <TabsContent value="code">
              {summary ? (
                <TestCodePanel key={summary.log_path ?? summary.module} summary={summary} />
              ) : (
                <NoData text={busy ? "Code test sẽ hiện khi agent chạy xong." : "Chưa có dữ liệu."} />
              )}
            </TabsContent>

            <TabsContent value="source">
              {shownSource?.code ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="font-mono text-sm">{title}</CardTitle>
                    <CardDescription>Module cần sinh test (đặc tả nằm trong docstring / JSDoc).</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <CodeViewer code={shownSource.code} language={shownSource.fence} />
                  </CardContent>
                </Card>
              ) : (
                <NoData text="Chưa chọn module." />
              )}
            </TabsContent>

            <TabsContent value="results">
              <ResultsView results={results} meta={meta} />
            </TabsContent>
          </Tabs>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
