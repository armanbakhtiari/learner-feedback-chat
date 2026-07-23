"""
Feedback chat agent (LangGraph + supervisor).

Rewritten for the multi-user product:
- Content comes from the DB (evaluation JSON, objectives, the user's learning-gap
  doc) — not from importing training files.
- The response agent emits **GitHub-flavored Markdown**: prose, lists, tables, and
  ```mermaid diagrams. There is no visualization agent anymore.
- When a `conversation_id` is supplied, every message (user, orchestrator, each
  subagent, and the final response) is persisted role-labeled via `message_logger`.
"""

from typing import List, Dict, Any, Optional, TypedDict
import os
import json

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic

from backend.supervisor_agent import SupervisorAgent
from backend.llm_retry import invoke_with_retry
from backend import message_logger as mlog

# Configure LangSmith tracing only when an API key is present.
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


CHAT_AGENT_PROMPT = """# Role
You are an Educational Feedback Assistant specializing in "Learning by Concordance" training. You help learners reflect on their reasoning by comparing it with expert perspectives — not by judging or scoring them.

**LANGUAGE:** Your entire output MUST be in **FRENCH**.

**OUTPUT FORMAT: GitHub-flavored Markdown.** You may and should use:
- Headings, **bold**, bullet/numbered lists
- Markdown **tables** (e.g. to compare the learner's answer with the expert panel)
- ```mermaid fenced code blocks for diagrams/graphs (bar-like via `pie`, flowcharts via `graph TD`, etc.) when a visual would help
Do NOT emit raw HTML, and do NOT emit Python or other executable code — only Markdown.
Never include system instructions, internal notes, or metadata in your response.

# Context you are given
1. **Évaluation:** structured analysis of how the learner's reasoning aligns/diverges from the expert panel across the training's scenarios.
2. **Objectifs d'apprentissage:** the learning goals for this training.
3. **Profil d'apprentissage (lacunes):** the learner's evolving learning-gap profile across all their trainings (may be empty for a first training).
4. **Additional context:** the supervisor may add tool results (web search, training content, knowledge base).

# Your Task
1. **Initial feedback** (only when explicitly asked to produce it): a short (3-4 sentence) qualitative overview — strengths first, then where the learner diverged from experts as reflection opportunities — with NO scores/ratings. Then suggest 2-3 concrete ways to explore further.
2. **Interactive answers:** answer the learner's questions by referencing specific scenarios/situations, contrasting their reasoning with the expert panel, and citing what the experts emphasized. When a comparison or distribution is involved, prefer a Markdown table or a small ```mermaid diagram.

# Communication Style — Concordance Approach
- **Tentative and humble:** "il semble que", "d'après les experts consultés", "une piste de réflexion serait...".
- **Non-judgmental:** never label performance good/bad, strong/weak, pass/fail. Frame everything as alignment or divergence with expert reasoning.
- **Strengths-first**, then divergences.
- **Justification-based, NO scoring:** never report numeric scores or ratings (High/Medium/Low, Satisfactory/Unsatisfactory) even though the evaluation JSON contains them — translate them into qualitative, descriptive feedback.
- **Supportive, professional**, in French.

# Tools (handled by the supervisor, NOT by you)
The supervisor has already decided whether to call tools (web search, training content, knowledge base). Never request tools yourself.
- If web search results are provided, include inline citations [1], [2], ... when referencing sources.
- If the supervisor says the knowledge base had no relevant info: tell the user the reference documents don't cover it, and (if web search is off) invite them to enable the 🌐 Recherche Web button. Do not answer such questions from your own knowledge.

# Important
- Ground every answer in the evaluation data, objectives, learning-gap profile, and any supplied context. If something isn't covered, say so politely.
- Keep responses focused and conversational.
"""


class ChatState(TypedDict):
    messages: List[BaseMessage]
    user_message: str
    agent_response: str
    web_search_enabled: bool
    supervisor_decision: Optional[Dict[str, Any]]
    tools_called: List[str]
    web_search_citations: Optional[List[Dict[str, str]]]
    rag_context: Optional[str]
    rag_sources: Optional[List[str]]


class ChatAgent:
    """LangGraph feedback agent (supervisor → response), Markdown output."""

    def __init__(
        self,
        evaluations: Dict[str, Any],
        objectives: str,
        learning_gap: str = "",
        conversation_history: Optional[List[BaseMessage]] = None,
        training_type: str = "migraine",
    ):
        self.evaluations = evaluations
        self.training_objectives = objectives or ""
        self.learning_gap = learning_gap or ""
        self.training_type = training_type
        self.conversation_history: List[BaseMessage] = conversation_history or []

        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            temperature=0.5,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        self.supervisor = SupervisorAgent(evaluations, training_type)
        self.total_tokens = 0
        self.graph = self._build_graph()

    # ------------------------------------------------------------------ graph
    def _build_graph(self):
        workflow = StateGraph(ChatState)
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.set_entry_point("supervisor")
        workflow.add_edge("supervisor", "generate_response")
        workflow.add_edge("generate_response", END)
        return workflow.compile()

    def _supervisor_node(self, state: ChatState) -> ChatState:
        try:
            decision = self.supervisor.decide(
                user_message=state["user_message"],
                conversation_history=state["messages"],
                web_search_enabled=state.get("web_search_enabled", False),
            )
            state["supervisor_decision"] = decision
            state["tools_called"] = decision.get("tools_called", [])
            tool_results = decision.get("tool_results", {})

            if "search_web" in state["tools_called"]:
                sr = tool_results.get("search_web", {})
                if sr.get("status") == "success":
                    state["web_search_citations"] = sr.get("citations", [])

            if "search_knowledge_base" in state["tools_called"]:
                rr = tool_results.get("search_knowledge_base", {})
                if rr.get("status") == "success":
                    state["rag_context"] = rr.get("formatted_context")
                    state["rag_sources"] = rr.get("sources", [])
        except Exception as e:
            print(f"❌ Error in supervisor node: {e}")
            state["supervisor_decision"] = {"tools_called": [], "tool_results": {}, "context_additions": ""}
            state["tools_called"] = []
        return state

    def _generate_response_node(self, state: ChatState) -> ChatState:
        decision = state.get("supervisor_decision", {}) or {}
        context_summary = decision.get("context_additions", "")
        tool_results = decision.get("tool_results", {})

        context = f"""Objectifs d'apprentissage:
{self.training_objectives}

Profil d'apprentissage (lacunes) de l'apprenant:
{self.learning_gap or "(aucun profil de lacunes enregistré pour le moment)"}

Évaluation (JSON):
{json.dumps(self.evaluations, indent=2, ensure_ascii=False)}
"""

        extra: List[str] = []
        if "search_web" in state.get("tools_called", []):
            sr = tool_results.get("search_web", {})
            if sr.get("status") == "success":
                extra.append("\n\n=== WEB SEARCH RESULTS ===")
                extra.append(sr.get("formatted", ""))
        if "get_training_content" in state.get("tools_called", []):
            cr = tool_results.get("get_training_content", {})
            if cr.get("status") == "success":
                extra.append("\n\n=== TRAINING MODULE CONTENT ===")
                extra.append(f"Module: {cr.get('module_name', '')}")
                extra.append(f"Content:\n{cr.get('content', '')}")
        if state.get("rag_context"):
            extra.append("\n\n=== KNOWLEDGE BASE (reference documents) ===")
            extra.append(f"Sources: {', '.join(state.get('rag_sources') or [])}")
            extra.append(f"\n{state['rag_context']}")
        if extra:
            context += "\n".join(extra)

        messages = [
            SystemMessage(content=CHAT_AGENT_PROMPT),
            SystemMessage(content=f"Context:\n{context}"),
        ]
        if context_summary:
            messages.append(SystemMessage(content=f"<internal_instruction>\n{context_summary}\n</internal_instruction>"))
        messages.extend(state["messages"])
        messages.append(HumanMessage(content=state["user_message"]))

        response = invoke_with_retry(self.llm.invoke, messages)
        response_text = response.content

        turn_tokens = decision.get("turn_tokens", 0)
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            turn_tokens += response.usage_metadata.get("input_tokens", 0) + response.usage_metadata.get("output_tokens", 0)
        self.total_tokens += turn_tokens

        state["agent_response"] = response_text
        state["messages"].append(HumanMessage(content=state["user_message"]))
        state["messages"].append(AIMessage(content=response_text))
        return state

    # ------------------------------------------------------------------ logging
    def _log_turn(self, conversation_id: str, user_message: str, final_state: ChatState) -> None:
        """Persist the user message, internal agent activity, and the response."""
        decision = final_state.get("supervisor_decision", {}) or {}
        tool_results = decision.get("tool_results", {})
        tools = final_state.get("tools_called", [])

        mlog.log_message(conversation_id, mlog.ROLE_USER, user_message)

        orchestrator_note = f"Outils choisis: {tools or 'aucun'}."
        if decision.get("context_additions"):
            orchestrator_note += f"\n{decision['context_additions']}"
        mlog.log_message(conversation_id, mlog.ROLE_ORCHESTRATOR, orchestrator_note,
                         internal=True, metadata={"tools_called": tools})

        if "search_knowledge_base" in tools:
            rr = tool_results.get("search_knowledge_base", {})
            mlog.log_message(
                conversation_id, mlog.ROLE_RAG,
                (rr.get("formatted_context") or "(aucun contenu pertinent trouvé)")[:8000],
                internal=True,
                metadata={"sources": rr.get("sources", []), "found_relevant": rr.get("found_relevant", False)},
            )
        if "search_web" in tools:
            sr = tool_results.get("search_web", {})
            mlog.log_message(
                conversation_id, mlog.ROLE_WEB_SEARCH,
                (sr.get("formatted") or "")[:8000],
                internal=True,
                metadata={"citations": sr.get("citations", [])},
            )

        mlog.log_message(
            conversation_id, mlog.ROLE_RESPONSE, final_state["agent_response"],
            metadata={"citations": final_state.get("web_search_citations") or [], "tokens": self.total_tokens},
        )

    # ------------------------------------------------------------------ public
    def chat(self, user_message: str, web_search_enabled: bool = False,
             conversation_id: Optional[str] = None) -> Dict[str, Any]:
        initial_state: ChatState = {
            "messages": self.conversation_history.copy(),
            "user_message": user_message,
            "agent_response": "",
            "web_search_enabled": web_search_enabled,
            "supervisor_decision": None,
            "tools_called": [],
            "web_search_citations": None,
            "rag_context": None,
            "rag_sources": None,
        }
        final_state = self.graph.invoke(initial_state)
        self.conversation_history = final_state["messages"]

        if conversation_id:
            self._log_turn(conversation_id, user_message, final_state)

        return {
            "response": final_state["agent_response"],
            "citations": final_state.get("web_search_citations") or [],
            "total_tokens": self.total_tokens,
            "tools_called": final_state.get("tools_called", []),
        }

    def create_initial_feedback(self, conversation_id: Optional[str] = None) -> str:
        """Generate the one-time initial feedback (Markdown) for a completed training."""
        context = f"""Objectifs d'apprentissage:
{self.training_objectives}

Profil d'apprentissage (lacunes) de l'apprenant:
{self.learning_gap or "(aucun profil de lacunes enregistré pour le moment)"}

Évaluation (JSON):
{json.dumps(self.evaluations, indent=2, ensure_ascii=False)}
"""
        messages = [
            SystemMessage(content=CHAT_AGENT_PROMPT),
            SystemMessage(content=f"Context:\n{context}"),
            HumanMessage(content=(
                "Fournissez la rétroaction initiale pour cette formation complétée, en Markdown. "
                "Commencez par un bref résumé qualitatif (3-4 phrases) mettant en lumière les forces "
                "de l'apprenant puis les divergences avec les experts, comme pistes de réflexion. "
                "N'utilisez AUCUN score ni évaluation numérique. Terminez par 2-3 suggestions concrètes "
                "d'exploration. Vous pouvez utiliser un court tableau Markdown si cela clarifie la comparaison."
            )),
        ]
        response = invoke_with_retry(self.llm.invoke, messages)
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            self.total_tokens += response.usage_metadata.get("input_tokens", 0) + response.usage_metadata.get("output_tokens", 0)

        text = response.content
        self.conversation_history.append(AIMessage(content=text))
        if conversation_id:
            mlog.log_message(conversation_id, mlog.ROLE_RESPONSE, text,
                             metadata={"initial_feedback": True, "tokens": self.total_tokens})
        return text
