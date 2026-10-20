"use client";

import { IconEye, IconLock } from "./Icons";
import type { ScenarioKind } from "@/lib/types";

/** How many cards a scenario has — the "step" a fully revealed scenario reaches. */
export const cardCount = (kind?: ScenarioKind) => (kind === "judgment" ? 1 : 2);

/** The question asked above the response scale. */
export const scaleQuestion = (kind?: ScenarioKind, scale?: string | null) =>
  kind === "judgment"
    ? "Le comportement observé est :"
    : scale === "concordance"
      ? "Cette nouvelle information rend votre hypothèse :"
      : "Cette nouvelle information rend votre hypothèse d'action :";

type Card = { title: string; subtitle: string; text: string; tone: "brand" | "amber" };

const TONES = {
  brand: { box: "border-brand/30 bg-brand/5", title: "text-brand" },
  amber: { box: "border-amber-300 bg-amber-50", title: "text-amber-700" },
};

/**
 * A scenario's prompt as distinct cards, laid out like the SENSAI authoring document:
 * "Si vous pensiez à… (votre hypothèse d'action)" then "Et qu'alors vous savez que…
 * (nouvelle information)", or a single "Comportement observé" card for a judgment scenario.
 *
 * With `onReveal`, the cards start closed and open one at a time, in order — the learner
 * considers the hypothesis before seeing what challenges it. `step` is how many are open.
 * Without it, every card is shown (previews, the completed evaluation).
 */
export default function ScenarioPrompt({
  hypothesis,
  newInformation,
  kind,
  scale,
  step,
  onReveal,
}: {
  hypothesis: string;
  newInformation: string;
  kind?: ScenarioKind;
  scale?: string | null;
  step?: number;
  onReveal?: () => void;
}) {
  const cards: Card[] =
    kind === "judgment"
      ? [{ title: "Comportement observé", subtitle: "(le comportement à juger)", text: hypothesis, tone: "brand" }]
      : [
          {
            title: "Si vous pensiez à…",
            // Migraine hypotheses are diagnoses, not actions.
            subtitle: scale === "concordance" ? "(votre hypothèse)" : "(votre hypothèse d'action)",
            text: hypothesis,
            tone: "brand",
          },
          {
            title: "Et qu'alors vous savez que…",
            subtitle: "(nouvelle information sur la situation)",
            text: newInformation,
            tone: "amber",
          },
        ];
  const open = onReveal ? (step ?? 0) : cards.length;

  return (
    <div className={`grid gap-3 ${cards.length > 1 ? "sm:grid-cols-2" : ""}`}>
      {cards.map((card, i) => {
        const tone = TONES[card.tone];
        const header = (
          <p className="text-sm">
            <span className={`font-semibold ${tone.title}`}>{card.title}</span>{" "}
            <span className="text-xs text-slate-500">{card.subtitle}</span>
          </p>
        );

        if (i < open)
          return (
            <div key={i} className={`rounded-lg border p-3 ${tone.box}`}>
              {header}
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800">{card.text}</p>
            </div>
          );

        if (i === open)
          return (
            <button
              key={i}
              type="button"
              onClick={onReveal}
              className={`flex min-h-24 flex-col rounded-lg border border-dashed p-3 text-left transition hover:shadow-sm ${tone.box}`}
            >
              {header}
              <span className="mt-auto flex items-center gap-1.5 pt-3 text-xs font-medium text-slate-600">
                <IconEye width={15} height={15} />
                Cliquer pour afficher
              </span>
            </button>
          );

        return (
          <div
            key={i}
            className="flex min-h-24 flex-col rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3"
          >
            <p className="text-sm">
              <span className="font-semibold text-slate-400">{card.title}</span>{" "}
              <span className="text-xs text-slate-400">{card.subtitle}</span>
            </p>
            <span className="mt-auto flex items-center gap-1.5 pt-3 text-xs text-slate-400">
              <IconLock width={14} height={14} />
              Affichez d&apos;abord votre hypothèse
            </span>
          </div>
        );
      })}
    </div>
  );
}
