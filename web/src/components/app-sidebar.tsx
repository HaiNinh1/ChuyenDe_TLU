import { FlaskConical, History, Play, Square, TriangleAlert } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type { Language, LogItem, Meta, RunRequest } from "@/lib/api"

export type Mode = "run" | "replay"

const SEGMENTED = "w-full gap-0.5 rounded-lg bg-muted p-0.5"
const SEGMENT_ITEM =
  "flex-1 rounded-md! text-muted-foreground data-[state=on]:bg-background data-[state=on]:text-foreground data-[state=on]:shadow-sm"
const EXT_NAMES: Record<string, string> = { ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript" }

type Props = {
  meta: Meta | null
  mode: Mode
  onModeChange: (m: Mode) => void
  form: RunRequest
  onFormChange: (patch: Partial<RunRequest>) => void
  detectedExt: string
  language: Language | undefined
  logs: LogItem[]
  selectedLog: string
  onSelectLog: (name: string) => void
  speed: number
  onSpeedChange: (s: number) => void
  busy: boolean
  canRun: boolean
  onRun: () => void
  onReplay: () => void
  onStop: () => void
}

/** Thanh trượt có nhãn + giá trị hiện tại. */
function SliderField({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  disabled,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  unit?: string
  disabled?: boolean
  onChange: (v: number) => void
}) {
  return (
    <Field data-disabled={disabled}>
      <div className="flex items-center justify-between">
        <FieldLabel className="text-xs font-normal text-muted-foreground">{label}</FieldLabel>
        <span className="font-mono text-xs tabular-nums">
          {value}
          {unit}
        </span>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        onValueChange={([v]) => onChange(v)}
      />
    </Field>
  )
}

export function AppSidebar(p: Props) {
  const { form, language } = p
  const env = language?.env
  const mutationOk = env?.mutation_available ?? false

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <FlaskConical className="size-4" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold">LLM Test Agent</div>
            <div className="text-xs text-muted-foreground">Coverage + mutation feedback</div>
          </div>
        </div>
        <ToggleGroup
          type="single"
          size="sm"
          className={`mt-3 ${SEGMENTED}`}
          value={p.mode}
          onValueChange={(v) => v && p.onModeChange(v as Mode)}
        >
          <ToggleGroupItem value="run" className={SEGMENT_ITEM}>
            <Play /> Chạy mới
          </ToggleGroupItem>
          <ToggleGroupItem value="replay" className={SEGMENT_ITEM}>
            <History /> Replay log
          </ToggleGroupItem>
        </ToggleGroup>
      </SidebarHeader>

      <SidebarContent>
        {p.mode === "run" ? (
          <>
            <SidebarGroup>
              <SidebarGroupLabel>Mã nguồn</SidebarGroupLabel>
              <SidebarGroupContent className="px-2">
                <FieldGroup className="gap-4">
                  <ToggleGroup
                    type="single"
                    size="sm"
                    className={SEGMENTED}
                    value={form.source_kind}
                    onValueChange={(v) => v && p.onFormChange({ source_kind: v as RunRequest["source_kind"] })}
                  >
                    <ToggleGroupItem value="sample" className={SEGMENT_ITEM}>
                      Module mẫu
                    </ToggleGroupItem>
                    <ToggleGroupItem value="paste" className={SEGMENT_ITEM}>
                      Dán code
                    </ToggleGroupItem>
                  </ToggleGroup>

                  {form.source_kind === "sample" ? (
                    <>
                      <Field>
                        <FieldLabel className="text-xs">Ngôn ngữ</FieldLabel>
                        <Select
                          value={form.language}
                          onValueChange={(v) => {
                            const lang = p.meta?.languages.find((l) => l.name === v)
                            p.onFormChange({ language: v, file: lang?.files[0] ?? "" })
                          }}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {p.meta?.languages.map((l) => (
                              <SelectItem key={l.name} value={l.name}>
                                {l.display_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>
                      <Field>
                        <FieldLabel className="text-xs">Module</FieldLabel>
                        <Select value={form.file} onValueChange={(v) => p.onFormChange({ file: v })}>
                          <SelectTrigger className="w-full font-mono text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {language?.files.map((f) => (
                              <SelectItem key={f} value={f} className="font-mono text-xs">
                                {f}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>
                    </>
                  ) : (
                    <>
                      <Field>
                        <FieldLabel className="text-xs">Code cần sinh test</FieldLabel>
                        <Textarea
                          className="h-40 resize-none font-mono text-xs"
                          placeholder="Dán hàm/module, nên có docstring hoặc JSDoc mô tả hành vi đúng"
                          value={form.code}
                          onChange={(e) => p.onFormChange({ code: e.target.value })}
                        />
                      </Field>
                      <div className="grid grid-cols-2 gap-2">
                        <Field>
                          <FieldLabel className="text-xs">Ngôn ngữ</FieldLabel>
                          <Select value={form.ext} onValueChange={(v) => p.onFormChange({ ext: v })}>
                            <SelectTrigger className="w-full">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Object.entries(EXT_NAMES).map(([ext, name]) => (
                                <SelectItem key={ext} value={ext}>
                                  {name}
                                  {ext === p.detectedExt && form.code.trim() ? " (tự nhận)" : ""}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </Field>
                        <Field>
                          <FieldLabel className="text-xs">Tên module</FieldLabel>
                          <Input
                            className="font-mono text-xs"
                            value={form.module_name}
                            onChange={(e) => p.onFormChange({ module_name: e.target.value })}
                          />
                        </Field>
                      </div>
                    </>
                  )}

                  {language && (
                    <div className="rounded-md border bg-background p-2.5 text-xs">
                      <div className="mb-1.5 font-medium">Bộ công cụ {language.display_name}</div>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="secondary">{language.test_framework}</Badge>
                        <Badge variant="secondary">{language.coverage_tool.split(" (")[0]}</Badge>
                        <Badge variant="secondary">{language.mutation_tool.split(" (")[0]}</Badge>
                      </div>
                      {env && !env.ok && (
                        <p className="mt-2 flex gap-1.5 text-destructive">
                          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
                          <span>
                            {env.message} {env.install_hint && <code className="font-mono">{env.install_hint}</code>}
                          </span>
                        </p>
                      )}
                      {env?.ok && !mutationOk && (
                        <p className="mt-2 text-warning">Chưa cài công cụ mutation, chỉ chạy phần coverage.</p>
                      )}
                    </div>
                  )}
                </FieldGroup>
              </SidebarGroupContent>
            </SidebarGroup>

            <SidebarSeparator />

            <SidebarGroup>
              <SidebarGroupLabel>Cấu hình agent</SidebarGroupLabel>
              <SidebarGroupContent className="px-2">
                <FieldGroup className="gap-4">
                  <Field orientation="horizontal" data-disabled={!mutationOk}>
                    <FieldLabel htmlFor="mut" className="text-sm font-normal">
                      Mutation testing
                    </FieldLabel>
                    <Switch
                      id="mut"
                      className="ml-auto"
                      checked={form.use_mutation && mutationOk}
                      disabled={!mutationOk}
                      onCheckedChange={(v) => p.onFormChange({ use_mutation: v })}
                    />
                  </Field>
                  <Field orientation="horizontal">
                    <FieldLabel htmlFor="mem" className="text-sm font-normal">
                      Bộ nhớ tự học
                    </FieldLabel>
                    <Switch
                      id="mem"
                      className="ml-auto"
                      checked={form.use_memory}
                      onCheckedChange={(v) => p.onFormChange({ use_memory: v })}
                    />
                  </Field>
                  <SliderField label="Số vòng tối đa" value={form.max_iterations} min={1} max={10}
                    onChange={(v) => p.onFormChange({ max_iterations: v })} />
                  <SliderField label="Ngưỡng line coverage" unit="%" value={form.line_threshold} min={50} max={100}
                    onChange={(v) => p.onFormChange({ line_threshold: v })} />
                  <SliderField label="Ngưỡng branch coverage" unit="%" value={form.branch_threshold} min={50}
                    max={100} onChange={(v) => p.onFormChange({ branch_threshold: v })} />
                  <SliderField label="Ngưỡng mutation score" unit="%" value={form.mutation_threshold} min={50}
                    max={100} disabled={!form.use_mutation || !mutationOk}
                    onChange={(v) => p.onFormChange({ mutation_threshold: v })} />
                  <SliderField label="Số mutant tối đa" value={form.max_mutants} min={5} max={40}
                    disabled={!form.use_mutation || !mutationOk}
                    onChange={(v) => p.onFormChange({ max_mutants: v })} />
                </FieldGroup>
              </SidebarGroupContent>
            </SidebarGroup>

            <SidebarSeparator />

            <SidebarGroup>
              <SidebarGroupLabel>LLM</SidebarGroupLabel>
              <SidebarGroupContent className="px-2">
                <FieldGroup className="gap-3">
                  <Field>
                    <FieldLabel className="text-xs">Nhà cung cấp</FieldLabel>
                    <Select
                      value={form.provider}
                      onValueChange={(v) =>
                        p.onFormChange({
                          provider: v,
                          model: v === p.meta?.default_provider ? p.meta.default_model : (p.meta?.providers[v] ?? ""),
                        })
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.keys(p.meta?.providers ?? {}).map((name) => (
                          <SelectItem key={name} value={name}>
                            {name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field>
                    <FieldLabel className="text-xs">Model</FieldLabel>
                    <Input
                      className="font-mono text-xs"
                      value={form.model}
                      onChange={(e) => p.onFormChange({ model: e.target.value })}
                    />
                    {form.provider === "mock" && (
                      <FieldDescription className="text-xs">
                        LLM giả lập — chỉ để thử pipeline, không dùng làm kết quả.
                      </FieldDescription>
                    )}
                  </Field>
                </FieldGroup>
              </SidebarGroupContent>
            </SidebarGroup>
          </>
        ) : (
          <SidebarGroup>
            <SidebarGroupLabel>Log đã lưu ({p.logs.length})</SidebarGroupLabel>
            <SidebarGroupContent className="px-2">
              <FieldGroup className="gap-4">
                <Field>
                  <Select value={p.selectedLog} onValueChange={p.onSelectLog}>
                    <SelectTrigger className="w-full font-mono text-xs">
                      <SelectValue placeholder="Chọn log" />
                    </SelectTrigger>
                    <SelectContent className="max-h-80">
                      {p.logs.map((l) => (
                        <SelectItem key={l.name} value={l.name} className="font-mono text-xs">
                          {l.name.replace(/\.json$/, "")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                {(() => {
                  const l = p.logs.find((x) => x.name === p.selectedLog)
                  if (!l) return null
                  return (
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 rounded-md border bg-background p-2.5 text-xs">
                      <dt className="text-muted-foreground">Ngôn ngữ</dt>
                      <dd className="text-right">{l.language}</dd>
                      <dt className="text-muted-foreground">Số vòng</dt>
                      <dd className="text-right tabular-nums">{l.iterations}</dd>
                      <dt className="text-muted-foreground">Line cov.</dt>
                      <dd className="text-right tabular-nums">{l.line_coverage ?? "—"}%</dd>
                      <dt className="text-muted-foreground">Mutation</dt>
                      <dd className="text-right tabular-nums">
                        {l.mutation_score === null ? "—" : `${l.mutation_score}%`}
                      </dd>
                      <dt className="text-muted-foreground">Nghi bug</dt>
                      <dd className="text-right tabular-nums">{l.suspected_bugs}</dd>
                      <dt className="col-span-2 mt-1 truncate font-mono text-[11px] text-muted-foreground">
                        {l.model}
                      </dt>
                    </dl>
                  )
                })()}
                <SliderField label="Tốc độ phát lại (giây/vòng)" value={p.speed} min={0} max={3} step={0.5}
                  unit="s" onChange={p.onSpeedChange} />
                <FieldDescription className="text-xs">
                  Phát lại một lần chạy đã lưu — không gọi LLM, không cần mạng.
                </FieldDescription>
              </FieldGroup>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t p-3">
        {p.busy ? (
          <Button variant="outline" className="w-full" onClick={p.onStop}>
            <Square /> Dừng hiển thị
          </Button>
        ) : p.mode === "run" ? (
          <Button className="w-full" disabled={!p.canRun} onClick={p.onRun}>
            <Play /> Chạy agent
          </Button>
        ) : (
          <Button className="w-full" disabled={!p.selectedLog} onClick={p.onReplay}>
            <History /> Phát lại
          </Button>
        )}
      </SidebarFooter>
    </Sidebar>
  )
}
