import { Highlight, themes } from "prism-react-renderer"
import { useTheme } from "next-themes"

import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

/** Khối code có số dòng; các dòng trong `spans` (test SUSPECTED_BUG) được tô đỏ. */
export function CodeViewer({
  code,
  language,
  spans = [],
  className,
}: {
  code: string
  language: string
  spans?: [number, number][]
  className?: string
}) {
  const { resolvedTheme } = useTheme()
  const theme = resolvedTheme === "dark" ? themes.oneDark : themes.github
  const flagged = (n: number) => spans.some(([a, b]) => a <= n && n <= b)

  return (
    <ScrollArea className={cn("rounded-lg border bg-card", className)}>
      <Highlight code={code.replace(/\n$/, "")} language={language} theme={theme}>
        {({ tokens, getLineProps, getTokenProps }) => (
          <pre className="py-3 pr-4 font-mono text-[13px] leading-6">
            {tokens.map((line, i) => {
              const bad = flagged(i + 1)
              const { className: lineClass, ...lineProps } = getLineProps({ line })
              return (
                <div
                  key={i}
                  {...lineProps}
                  className={cn(
                    "code-line",
                    lineClass,
                    bad && "border-l-2 border-destructive bg-destructive/10"
                  )}
                  style={undefined}
                >
                  <span className={cn("ln", bad && "text-destructive opacity-100")}>{i + 1}</span>
                  <span className="whitespace-pre">
                    {line.map((token, k) => (
                      <span key={k} {...getTokenProps({ token })} />
                    ))}
                  </span>
                </div>
              )
            })}
          </pre>
        )}
      </Highlight>
      <ScrollBar orientation="horizontal" />
    </ScrollArea>
  )
}

/** Diff theo dòng giữa hai bản code (thuật toán LCS đơn giản, đủ dùng cho file test vài trăm dòng). */
export function DiffViewer({ before, after }: { before: string; after: string }) {
  const a = before.split("\n")
  const b = after.split("\n")
  // lcs[i][j] = độ dài dãy con chung dài nhất của a[i:] và b[j:]
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1])

  const rows: { kind: " " | "+" | "-"; text: string }[] = []
  let i = 0
  let j = 0
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      rows.push({ kind: " ", text: a[i] })
      i++
      j++
    } else if (j < b.length && (i >= a.length || lcs[i][j + 1] >= lcs[i + 1][j])) {
      rows.push({ kind: "+", text: b[j++] })
    } else {
      rows.push({ kind: "-", text: a[i++] })
    }
  }
  const added = rows.filter((r) => r.kind === "+").length
  const removed = rows.filter((r) => r.kind === "-").length

  return (
    <div className="overflow-hidden rounded-lg border bg-card">
      <div className="flex items-center gap-3 border-b bg-muted/40 px-4 py-2 font-mono text-xs">
        <span className="text-success">+{added}</span>
        <span className="text-destructive">−{removed}</span>
        <span className="text-muted-foreground">dòng thay đổi so với vòng trước</span>
      </div>
      <ScrollArea className="max-h-[640px]">
        <pre className="py-2 font-mono text-[13px] leading-6">
          {rows.map((r, k) => (
            <div
              key={k}
              className={cn(
                "flex px-4",
                r.kind === "+" && "bg-success/10 text-success",
                r.kind === "-" && "bg-destructive/10 text-destructive"
              )}
            >
              <span className="w-5 shrink-0 select-none opacity-70">{r.kind}</span>
              <span className="whitespace-pre">{r.text}</span>
            </div>
          ))}
        </pre>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </div>
  )
}
