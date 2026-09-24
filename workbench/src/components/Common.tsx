import { labels } from "@/lib/api";
export function Badge({ value }: { value: string }) {
  return (
    <span className={"badge tone-" + value.replace(/[^\w-]/g, "")}>
      {labels[value] || value}
    </span>
  );
}
export function Empty({ text = "暂无数据" }: { text?: string }) {
  return (
    <div className="grid min-h-40 place-items-center p-8 text-center text-sm text-muted-foreground">
      {text}
    </div>
  );
}
export function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
export function Code({
  code = "",
  start = 1,
  line,
}: {
  code?: string;
  start?: number;
  line?: number;
}) {
  return (
    <pre className="code">
      {code.split("\n").map((text, i) => (
        <div className={i + start === line ? "code-selected" : ""} key={i}>
          <span className="line-number">{i + start}</span>
          <code>
            {text
              .split(
                /("[^"\n]*"|'[^'\n]*'|\b(?:def|class|return|import|from|if|else|async|await|None|True|False)\b|#.*$)/g,
              )
              .map((part, j) => (
                <span
                  key={j}
                  className={
                    /^["']/.test(part)
                      ? "code-string"
                      : /^#/.test(part)
                        ? "text-muted-foreground"
                        : /^(def|class|return|import|from|if|else|async|await|None|True|False)$/.test(
                              part,
                            )
                          ? "text-primary"
                          : ""
                  }
                >
                  {part}
                </span>
              ))}
          </code>
        </div>
      ))}
    </pre>
  );
}
