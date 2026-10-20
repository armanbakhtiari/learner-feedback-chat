export type Likert =
  // "concordance" scale — how the new information changes the hypothesis
  | "Fortement affaiblie"
  | "Affaiblie"
  | "Inchangée"
  | "Renforcée"
  | "Fortement renforcée"
  // "pertinence" scale — how pertinent the hypothesis/action remains
  | "Pas du tout pertinente"
  | "Peu pertinente"
  | "Ni plus ni moins pertinente"
  | "Pertinente"
  | "Très pertinente"
  // "appropriee" scale — whether the new information makes the decision more or less appropriate
  | "Beaucoup moins appropriée"
  | "Moins appropriée"
  | "Ni plus ni moins appropriée"
  | "Plus appropriée"
  | "Beaucoup plus appropriée"
  // "pertinence_relative" scale — whether the new information makes the action more or less pertinent
  | "Beaucoup moins pertinente"
  | "Moins pertinente"
  | "Plus pertinente"
  | "Beaucoup plus pertinente"
  // "acceptabilite" scale — how acceptable an observed behaviour is (4 values, no middle)
  | "Tout à fait inacceptable"
  | "Inacceptable"
  | "Acceptable"
  | "Tout à fait acceptable";

/**
 * Response scales, keyed by `Training.likert_scale` (or a scenario's own override). Must
 * stay in sync with `backend/likert.py` and the `likert_scale` Postgres enum.
 */
export const LIKERT_SCALES: Record<string, Likert[]> = {
  concordance: [
    "Fortement affaiblie",
    "Affaiblie",
    "Inchangée",
    "Renforcée",
    "Fortement renforcée",
  ],
  pertinence: [
    "Pas du tout pertinente",
    "Peu pertinente",
    "Ni plus ni moins pertinente",
    "Pertinente",
    "Très pertinente",
  ],
  appropriee: [
    "Beaucoup moins appropriée",
    "Moins appropriée",
    "Ni plus ni moins appropriée",
    "Plus appropriée",
    "Beaucoup plus appropriée",
  ],
  pertinence_relative: [
    "Beaucoup moins pertinente",
    "Moins pertinente",
    "Ni plus ni moins pertinente",
    "Plus pertinente",
    "Beaucoup plus pertinente",
  ],
  acceptabilite: ["Tout à fait inacceptable", "Inacceptable", "Acceptable", "Tout à fait acceptable"],
};

export const DEFAULT_LIKERT_SCALE = "concordance";

/** The scale a training uses, falling back to the default for older rows. */
export const likertValues = (scale?: string | null): Likert[] =>
  LIKERT_SCALES[scale || DEFAULT_LIKERT_SCALE] ?? LIKERT_SCALES[DEFAULT_LIKERT_SCALE];

/**
 * How a scenario is posed: "reasoning" = a hypothesis then a new piece of information;
 * "judgment" = a single observed behaviour to judge (`new_information` is empty).
 */
export type ScenarioKind = "reasoning" | "judgment";

export interface ExpertAnswer {
  expert_label: string;
  likert: Likert | null;
  justification: string;
}

export interface Scenario {
  id: string;
  scenario_index: number;
  kind?: ScenarioKind;
  /** Overrides the training's scale when set (the GRH training mixes two). */
  likert_scale?: string | null;
  hypothesis: string;
  new_information: string;
  response?: { likert: Likert | null; justification: string | null } | null;
}

export interface Situation {
  id: string;
  situation_index: number;
  title: string;
  text: string;
  scenarios: Scenario[];
}

export interface Training {
  id: string;
  title: string;
  domain: string;
  origin: string;
  /** Which response scale this training's scenarios use — see LIKERT_SCALES. */
  likert_scale?: string;
  learning_objectives: string[];
  situations?: Situation[];
}

/** Read-only preview of a bank training, shown before adding it to the dashboard. */
export interface TrainingPreview {
  id: string;
  title: string;
  likert_scale?: string;
  learning_objectives: string[];
  situations: {
    title: string | null;
    text: string;
    scenarios: { hypothesis: string; new_information: string; kind?: ScenarioKind }[];
  }[];
}

export interface EvalTableRow {
  scenario_id: string;
  kind?: ScenarioKind;
  likert_scale?: string | null;
  hypothesis: string;
  new_information: string;
  response: { likert: Likert | null; justification: string | null } | null;
  expert_key_elements: string[];
  themes_addressed: string;
  themes_missed: string;
  reasoning: string;
  communication: string;
  /** The expert panel — present on tables built (or rebuilt) since it was added. */
  experts?: ExpertAnswer[];
}

export interface EvalTableSituation {
  title: string;
  description: string;
  scenarios: EvalTableRow[];
}

export interface EvalTable {
  situations: EvalTableSituation[];
}

export interface UserTraining {
  id: string;
  training_id: string;
  status: "not_started" | "in_progress" | "completed";
  training?: Training;
  situation_titles?: string[];
  eval_table?: EvalTable | null;
  completed_at?: string | null;
}

export interface LearningGapVersion {
  id: string;
  content: string;
  structured: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_training_id: string;
  title: string;
  created_at: string;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface NotificationRow {
  id: string;
  type: string;
  title: string;
  body: string | null;
  read: boolean;
  user_training_id: string | null;
  created_at: string;
}

export interface Suggestion {
  training_id: string;
  title: string;
  rationale: string;
  objectives?: string[];
}
