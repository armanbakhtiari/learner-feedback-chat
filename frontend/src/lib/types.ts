export type Likert =
  | "Fortement affaiblie"
  | "Affaiblie"
  | "Inchangée"
  | "Renforcée"
  | "Fortement renforcée";

export const LIKERT_VALUES: Likert[] = [
  "Fortement affaiblie",
  "Affaiblie",
  "Inchangée",
  "Renforcée",
  "Fortement renforcée",
];

export interface Scenario {
  id: string;
  scenario_index: number;
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
  learning_objectives: string[];
  situations?: Situation[];
}

export interface UserTraining {
  id: string;
  training_id: string;
  status: "not_started" | "in_progress" | "completed";
  training?: Training;
  situation_titles?: string[];
  evaluation_html?: string | null;
  completed_at?: string | null;
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
