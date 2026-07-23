"use client";

import { useEffect, useRef, useState } from "react";

/** Renders a ```mermaid code block to SVG (client-only, dynamic import). */
export default function Mermaid({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
        const id = "m" + Math.random().toString(36).slice(2);
        const { svg } = await mermaid.render(id, chart);
        if (active && ref.current) ref.current.innerHTML = svg;
      } catch {
        if (active) setFailed(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [chart]);

  if (failed) {
    return <pre className="my-3 overflow-x-auto rounded bg-slate-100 p-3 text-xs">{chart}</pre>;
  }
  return <div ref={ref} className="my-3 flex justify-center overflow-x-auto" />;
}
