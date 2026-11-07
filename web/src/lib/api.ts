// Kiểu dữ liệu + hàm gọi API của server.py. Tên trường giữ nguyên như log JSON của agent.

export type EnvStatus = {
  ok: boolean
  mutation_available: boolean
  message: string
  install_hint: string
  tools: Record<string, string>
}

export type Language = {
  name: string
  display_name: string
  extensions: string[]
  test_framework: string
  coverage_tool: string
  mutation_tool: string
  tools: string
  files: string[]
  env: EnvStatus
}

export type Meta = {
  languages: Language[]
  providers: Record<string, string>
  default_provider: string
  default_model: string
}

export type Classification = { test: string; verdict: string; reason: string }

export type Iteration = {
  iteration: number
  phase: string
  action: string
  reason: string
  test_code: string
  passed: number
  failed: number
  errors: number
  xfailed: number
  collection_error: string
  line_coverage: number
  branch_coverage: number
  mutation_score: number | null
  mutants_total: number
  mutants_killed: number
  survived_mutants: string[]
  classifications: Classification[]
  lesson: string
  llm_calls_so_far: number
  elapsed: number
}

export type CodeView = {
  code: string
  valid: boolean
  num_tests: number
  suspected: string[]
  spans: [number, number][]
}

export type Summary = {
  module: string
  module_path?: string
  language?: string
  label?: string
  stop_reason: string
  iterations: Iteration[]
  final_test_code: string
  suspected_bugs: Record<string, string>
  final: {
    line_coverage: number
    branch_coverage: number
    mutation_score: number | null
    num_iterations: number
    passed: number
    failed: number
    xfailed: number
  }
  stats: { llm_calls: number; input_tokens: number; output_tokens: number; total_seconds: number; llm_seconds: number }
  llm: { provider: string; model: string }
  source_code?: string
  log_path?: string
  // Do server.py thêm vào
  code_views: CodeView[]
  tools: string
  fence: string
  test_file_name: string
}

export type LogItem = {
  name: string
  language: string
  module: string
  label: string
  iterations: number
  line_coverage: number | null
  mutation_score: number | null
  suspected_bugs: number
  model: string
  mtime: number
}

export type CsvRow = Record<string, string>
export type Results = { summary: CsvRow[]; by_module: CsvRow[]; runs: CsvRow[] }

export type RunRequest = {
  source_kind: "sample" | "paste"
  language: string
  file: string
  code: string
  ext: string
  module_name: string
  use_mutation: boolean
  use_memory: boolean
  max_iterations: number
  line_threshold: number
  branch_threshold: number
  mutation_threshold: number
  max_mutants: number
  provider: string
  model: string
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const api = {
  meta: () => getJson<Meta>("/api/meta"),
  source: (language: string, file: string) =>
    getJson<{ code: string; fence: string }>(
      `/api/source?language=${encodeURIComponent(language)}&file=${encodeURIComponent(file)}`
    ),
  detect: (code: string) =>
    getJson<{ ext: string }>("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    }),
  logs: () => getJson<LogItem[]>("/api/logs"),
  log: (name: string) => getJson<Summary>(`/api/logs/${encodeURIComponent(name)}`),
  results: () => getJson<Results>("/api/results"),
}

export type RunEvent =
  | { event: "start"; data: { module: string; tools: string } }
  | { event: "message"; data: string }
  | { event: "iteration"; data: Iteration }
  | { event: "summary"; data: Summary }
  | { event: "error"; data: string }

/** Chạy agent: đọc luồng Server-Sent Events, gọi onEvent cho mỗi sự kiện (mỗi vòng lặp, mỗi thông báo). */
export async function runAgent(req: RunRequest, onEvent: (e: RunEvent) => void, signal?: AbortSignal) {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  })
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`)
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ""
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    // Mỗi sự kiện kết thúc bằng một dòng trống
    let cut: number
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, cut)
      buffer = buffer.slice(cut + 2)
      const event = chunk.match(/^event: (.*)$/m)?.[1]
      const data = chunk.match(/^data: (.*)$/m)?.[1]
      if (event && data) onEvent({ event, data: JSON.parse(data) } as RunEvent)
    }
  }
}

export const ACTION_LABELS: Record<string, string> = {
  generate: "Sinh bộ test ban đầu",
  fix_collection: "Sửa file test hỏng",
  fix_tests: "Phân loại & sửa test fail",
  improve_coverage: "Bổ sung test tăng coverage",
  kill_mutants: "Bổ sung test giết mutant",
  stop: "Dừng",
}

export const PHASE_LABELS: Record<string, string> = {
  repair: "Sửa lỗi",
  coverage: "Coverage",
  mutation: "Mutation",
  done: "Kết thúc",
}

export const fmtPct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v}%`)
