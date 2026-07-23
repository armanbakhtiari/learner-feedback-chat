"use client";

import DOMPurify from "isomorphic-dompurify";

/** Renders the LLM-generated evaluation HTML fragment, sanitized. */
export default function EvalTableHtml({ html }: { html: string }) {
  const clean = DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "style", "iframe", "form", "input"],
    FORBID_ATTR: ["onerror", "onclick", "onload"],
  });
  return <div className="overflow-x-auto text-sm" dangerouslySetInnerHTML={{ __html: clean }} />;
}
