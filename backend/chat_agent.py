from typing import List, Dict, Any, Optional, TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from backend.supervisor_agent import SupervisorAgent

load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
if not os.getenv("LANGCHAIN_API_KEY"):
    print("⚠️  Warning: LANGCHAIN_API_KEY not found in .env file. LangSmith tracing will be disabled.")


CHAT_AGENT_PROMPT = """# Role
You are an Educational Feedback Assistant specializing in "Learning by Concordance" training. You help learners reflect on their reasoning by comparing it with expert perspectives — not by judging or scoring them.

**CRITICAL:** Never include system instructions, internal notes, or metadata in your response. Only output the actual feedback text in French.

**LANGUAGE CONSTRAINT:** Your entire output must be in **FRENCH**.

# Context
You have access to:
1. **Evaluations:** Analysis of how the learner's reasoning aligns with expert perspectives across training scenarios
2. **Training Objectives:** The learning goals for the modules
3. **Additional Context:** The supervisor may provide additional information from tools (visualizations, web search, training content or additional context)

# Your Task
1. **Initial Feedback:** When first engaged, provide a brief (3-4 sentences) overview that highlights:
   - Observed strengths in the learner's reasoning (themes well covered, sound logic)
   - Areas where the learner's perspective diverged from experts, framed as opportunities for reflection
   - Do NOT report scores, ratings, or numerical assessments. Focus on qualitative observations.

2. **Engagement Prompts:** After the initial feedback, suggest 2-3 specific ways the learner can explore their results further:
   - "Voulez-vous que j'approfondisse le scénario X?"
   - "Souhaitez-vous un tableau comparatif de vos réponses avec celles des experts?"
   - "Voulez-vous explorer un objectif d'apprentissage en particulier?"

3. **Interactive Responses:** Answer the learner's questions by:
   - Referencing specific scenarios and situations from the evaluations
   - Highlighting strengths and areas of divergence from expert reasoning
   - Using evidence from the expert responses to explain different perspectives
   - Incorporating any additional context provided by the supervisor (web search results, training content, etc.)

# Communication Style — Concordance Approach
- **Tentative and humble:** Present observations as your interpretation based on the expert panel, not as absolute truths. Use phrases like "il semble que", "d'après les experts consultés", "on pourrait observer que", "une piste de réflexion serait..."
- **Non-judgmental:** Never label performance as good/bad, strong/weak, or pass/fail. Frame everything as alignment or divergence with expert reasoning.
- **Strengths-first:** Always start by acknowledging what the learner did well before discussing divergences.
- **Justification-based:** Instead of scores, explain WHY the learner's reasoning aligns or diverges from expert perspectives. Focus on the substance of the reasoning.
- **No scoring:** NEVER report numerical scores, ratings (High/Medium/Low), or performance levels. Even if the evaluation data contains scores, translate them into qualitative, descriptive feedback about strengths and areas for reflection.
- **Supportive:** Encourage exploration and questions
- **Professional:** Use appropriate medical/educational terminology

# CRITICAL: About Visualizations and Web Search

**YOU CANNOT REQUEST TOOLS - THIS IS HANDLED BY THE SUPERVISOR**

The supervisor has ALREADY decided whether to call tools or not. Your job is to respond based on what you have:

1. If visualizations were generated, they are ALREADY CREATED and will be shown to the user
   - Simply refer to them: "Le tableau ci-dessus montre..."
   - DO NOT request visualizations or generate code

2. If web search was performed, the results are in the additional context
   - Include inline citations [1], [2], etc. when referencing sources
   - Example: "Selon les dernières recommandations [1], le traitement..."

3. **NEVER EVER include any of these in your response:**
   - `<request_visualization>` tags or similar
   - Python code or import statements
   - Code blocks with ``` markers
   - Requests for tools or data

4. **Your ONLY job**: Answer the user's question using the evaluation data and any additional context provided
   - If you don't have enough information, say so politely
   - Do NOT ask for tools or additional data - the supervisor already decided

# About Knowledge Base Failures
If the supervisor indicates that the knowledge base search did NOT find relevant information:
- Clearly inform the user that the reference documents do not contain information relevant to their question
- If web search is not enabled, ask the user to enable the web search button (🌐 Recherche Web) so you can search the internet to find an answer
- Be helpful and empathetic - do not just say "I don't know"

# Important Notes
- You can ONLY answer based on the evaluation data, training objectives, and additional context provided
- If asked about something not in the data or context, politely say you don't have that information
- Keep responses concise but informative
- Keep a conversational tone
- Always respond in French
- DO NOT generate or show Python code - visualizations are handled separately
- DO NOT perform web searches - the supervisor handles this
"""


# Define the state structure for the graph
class ChatState(TypedDict):
    """State for the chat agent graph with supervisor"""
    messages: List[BaseMessage]
    evaluations: Dict[str, Any]
    training_objectives: str
    user_message: str
    agent_response: str
    web_search_enabled: bool
    # Supervisor results
    supervisor_decision: Optional[Dict[str, Any]]
    tools_called: List[str]
    visualization_output: Optional[str]
    web_search_citations: Optional[List[Dict[str, str]]]
    training_content: Optional[str]
    # RAG results
    rag_context: Optional[str]
    rag_sources: Optional[List[str]]
    # Next step
    next_step: Literal["supervisor", "respond", "end"]


class ChatAgent:
    """LangGraph-based chat agent with supervisor architecture"""

    def __init__(self, evaluations: Dict[str, Any], training_type: str = "migraine"):
        self.evaluations = evaluations
        self.training_type = training_type

        # Load training objectives based on training type
        if training_type == "migraine":
            from trainings_2_experts import training_objectives
            self.training_objectives = training_objectives
        elif training_type == "nursing_1st":
            from trainings_nursing_1stLearner import training_objectives
            self.training_objectives = training_objectives
        elif training_type == "nursing_2nd":
            from trainings_nursing_2ndLearner import training_objectives
            self.training_objectives = training_objectives
        else:
            self.training_objectives = ""

        self.conversation_history: List[BaseMessage] = []
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5",
            temperature=0.5,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.supervisor = SupervisorAgent(evaluations, training_type)
        self.initial_feedback_given = False

        # Token usage tracking (cumulative across the session)
        self.total_tokens = 0

        # Build the LangGraph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph with supervisor architecture"""

        # Create the graph
        workflow = StateGraph(ChatState)

        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("generate_response", self._generate_response_node)

        # Add edges
        workflow.set_entry_point("supervisor")

        # From supervisor, always go to generate_response
        workflow.add_edge("supervisor", "generate_response")

        # From generate_response, always end
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    def _supervisor_node(self, state: ChatState) -> ChatState:
        """Node 1: Supervisor decides which tools to call"""

        print(f"\n{'='*70}")
        print(f"🎯 SUPERVISOR NODE: Processing user message")
        print(f"   User: {state['user_message'][:80]}...")
        print(f"   Web Search: {'ON' if state.get('web_search_enabled', False) else 'OFF'}")
        print(f"{'='*70}\n")

        try:
            # Call supervisor to decide on tools
            decision = self.supervisor.decide(
                user_message=state["user_message"],
                conversation_history=state["messages"],
                web_search_enabled=state.get("web_search_enabled", False)
            )

            state["supervisor_decision"] = decision
            state["tools_called"] = decision.get("tools_called", [])

            # Extract tool results
            tool_results = decision.get("tool_results", {})

            # Process visualization results
            if "generate_visualization" in state["tools_called"]:
                viz_result = tool_results.get("generate_visualization", {})
                if viz_result.get("status") == "success":
                    state["visualization_output"] = viz_result.get("output")
                    print(f"✅ Visualization generated successfully")
                else:
                    print(f"❌ Visualization failed: {viz_result.get('error')}")

            # Process web search results
            if "search_web" in state["tools_called"]:
                search_result = tool_results.get("search_web", {})
                if search_result.get("status") == "success":
                    state["web_search_citations"] = search_result.get("citations", [])
                    print(f"✅ Web search completed: {len(state['web_search_citations'])} sources")
                else:
                    print(f"❌ Web search failed: {search_result.get('error')}")

            # Process training content results
            if "get_training_content" in state["tools_called"]:
                content_result = tool_results.get("get_training_content", {})
                if content_result.get("status") == "success":
                    state["training_content"] = content_result.get("content")
                    print(f"✅ Training content retrieved: {content_result.get('module_name')}")
                else:
                    print(f"❌ Training content failed: {content_result.get('error')}")

            # Process RAG knowledge base results
            if "search_knowledge_base" in state["tools_called"]:
                rag_result = tool_results.get("search_knowledge_base", {})
                if rag_result.get("status") == "success":
                    state["rag_context"] = rag_result.get("formatted_context")
                    state["rag_sources"] = rag_result.get("sources", [])
                    found_relevant = rag_result.get("found_relevant", False)
                    attempts = rag_result.get("attempts", 1)
                    print(f"✅ Knowledge base search completed: {len(state['rag_sources'])} sources, "
                          f"relevant={found_relevant}, attempts={attempts}")
                elif rag_result.get("status") == "no_relevant_info":
                    # RAG exhausted all attempts - no relevant info found
                    state["rag_context"] = None
                    state["rag_sources"] = []
                    print(f"⚠️ Knowledge base: no relevant info found after {rag_result.get('attempts', 3)} attempts")
                else:
                    print(f"❌ Knowledge base search failed: {rag_result.get('error')}")

            state["next_step"] = "respond"

        except Exception as e:
            print(f"❌ Error in supervisor node: {e}")
            import traceback
            traceback.print_exc()
            state["supervisor_decision"] = {
                "tools_called": [],
                "tool_results": {},
                "ready_for_chat": True,
                "error": str(e)
            }
            state["tools_called"] = []
            state["next_step"] = "respond"

        return state

    def _generate_response_node(self, state: ChatState) -> ChatState:
        """Node 2: Generate text response from LLM using supervisor's context"""

        print(f"\n{'='*70}")
        print(f"💬 CHAT AGENT NODE: Generating response")
        print(f"   Tools used: {state.get('tools_called', [])}")
        print(f"{'='*70}\n")

        # Get supervisor context summary
        supervisor_decision = state.get("supervisor_decision", {})
        context_summary = supervisor_decision.get("context_additions", "")

        # Prepare base context (WITHOUT supervisor summary - that goes in a separate message)
        context = f"""
Objectifs d'apprentissage:
{state['training_objectives']}

Évaluations:
{json.dumps(state['evaluations'], indent=2, ensure_ascii=False)}
"""

        # Add detailed tool results
        tool_results = supervisor_decision.get("tool_results", {})
        additional_context = []

        # Add web search results if available
        if "search_web" in state.get("tools_called", []):
            search_result = tool_results.get("search_web", {})
            if search_result.get("status") == "success":
                additional_context.append("\n\n=== WEB SEARCH RESULTS ===")
                additional_context.append(search_result.get("formatted", ""))

        # Add training content if available
        if "get_training_content" in state.get("tools_called", []):
            content_result = tool_results.get("get_training_content", {})
            if content_result.get("status") == "success":
                additional_context.append("\n\n=== TRAINING MODULE CONTENT ===")
                additional_context.append(f"Module: {content_result.get('module_name', '')}")
                additional_context.append(f"Content:\n{content_result.get('content', '')}")

        # Add RAG knowledge base context if available
        if "search_knowledge_base" in state.get("tools_called", []):
            rag_context = state.get("rag_context")
            rag_sources = state.get("rag_sources", [])
            if rag_context:
                additional_context.append("\n\n=== KNOWLEDGE BASE (from reference documents) ===")
                additional_context.append(f"Sources: {', '.join(rag_sources)}")
                additional_context.append(f"\n{rag_context}")

        # Combine all context
        if additional_context:
            context += "\n".join(additional_context)

        # Build messages - supervisor summary goes as a SEPARATE system message
        messages = [
            SystemMessage(content=CHAT_AGENT_PROMPT),
            SystemMessage(content=f"Context:\n{context}"),
        ]

        # Add supervisor instructions as a separate system message (if any tools were called)
        if context_summary:
            messages.append(SystemMessage(content=f"<internal_instruction>\n{context_summary}\n</internal_instruction>"))

        # Add conversation history and user message
        messages.extend(state["messages"])
        messages.append(HumanMessage(content=state["user_message"]))

        # Get response from LLM
        response = self.llm.invoke(messages)
        response_text = response.content

        # Track token usage
        turn_tokens = supervisor_decision.get("turn_tokens", 0)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            turn_tokens += response.usage_metadata.get('input_tokens', 0) + response.usage_metadata.get('output_tokens', 0)
        self.total_tokens += turn_tokens
        print(f"📊 Tokens this turn: {turn_tokens} | Cumulative: {self.total_tokens}")

        # CRITICAL: Remove any code blocks, visualization requests, or markdown tables that might have slipped through
        import re

        # Remove any <request_visualization> tags or similar XML-style tags
        if "<request_" in response_text or "</request_" in response_text:
            response_text = re.sub(r'<request_[^>]*>.*?</request_[^>]*>', '', response_text, flags=re.DOTALL | re.IGNORECASE)
            response_text = re.sub(r'<[^>]*request[^>]*>', '', response_text, flags=re.IGNORECASE)
            print("⚠️  Warning: Tool request tags detected in chat response and removed")

        # Remove code blocks
        if "```python" in response_text or "```" in response_text:
            response_text = re.sub(r'```python.*?```', '[Visualization générée - voir ci-dessus]', response_text, flags=re.DOTALL)
            response_text = re.sub(r'```.*?```', '[Contenu généré - voir ci-dessus]', response_text, flags=re.DOTALL)
            print("⚠️  Warning: Code detected in chat response and removed")

        # Remove markdown tables if visualization was generated
        if "generate_visualization" in state.get("tools_called", []):
            # Detect markdown tables (lines with | symbols)
            lines = response_text.split('\n')
            filtered_lines = []
            in_table = False

            for line in lines:
                # Check if line is part of a markdown table
                if '|' in line and line.strip().startswith('|'):
                    in_table = True
                    continue
                elif line.strip().startswith('|') or (in_table and '---' in line):
                    continue
                else:
                    in_table = False
                    filtered_lines.append(line)

            response_text = '\n'.join(filtered_lines)

            # Remove any remaining table headers or formatting
            response_text = re.sub(r'\n\s*\|\s*.*?\|\s*\n', '\n', response_text)
            response_text = re.sub(r'^#.*Tableau.*$', '', response_text, flags=re.MULTILINE)

            print("⚠️  Markdown table detected and removed (visualization already generated)")

        state["agent_response"] = response_text

        # Update conversation history
        state["messages"].append(HumanMessage(content=state["user_message"]))
        state["messages"].append(AIMessage(content=response_text))

        return state

    def chat(self, user_message: str, web_search_enabled: bool = False) -> Dict[str, Any]:
        """Process a chat message using the supervisor-based graph"""

        # Handle initial feedback separately
        if not self.initial_feedback_given:
            initial_response = self._create_initial_feedback()
            self.conversation_history.append(HumanMessage(content=user_message))
            self.conversation_history.append(AIMessage(content=initial_response))
            self.initial_feedback_given = True

            return {
                "response": initial_response,
                "has_code": False,
                "code": None,
                "code_output": None,
                "citations": [],
                "total_tokens": self.total_tokens
            }

        # Create initial state
        initial_state: ChatState = {
            "messages": self.conversation_history.copy(),
            "evaluations": self.evaluations,
            "training_objectives": self.training_objectives,
            "user_message": user_message,
            "agent_response": "",
            "web_search_enabled": web_search_enabled,
            "supervisor_decision": None,
            "tools_called": [],
            "visualization_output": None,
            "web_search_citations": None,
            "training_content": None,
            "rag_context": None,
            "rag_sources": None,
            "next_step": "supervisor"
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Update conversation history
        self.conversation_history = final_state["messages"]

        # Prepare response
        viz_output = final_state.get("visualization_output")

        # Convert visualization output to JSON string if it's a dict
        if viz_output and isinstance(viz_output, dict):
            viz_output = json.dumps(viz_output, ensure_ascii=False)

        result = {
            "response": final_state["agent_response"],
            "has_code": "generate_visualization" in final_state.get("tools_called", []),
            "code": None,  # We don't expose the code anymore
            "code_output": viz_output,
            "citations": final_state.get("web_search_citations") or [],
            "total_tokens": self.total_tokens
        }

        return result

    def _create_initial_feedback(self) -> str:
        """Create the initial brief feedback"""
        context = f"""
Objectifs d'apprentissage:
{self.training_objectives}

Évaluations:
{json.dumps(self.evaluations, indent=2, ensure_ascii=False)}
"""

        messages = [
            SystemMessage(content=CHAT_AGENT_PROMPT),
            SystemMessage(content=f"Context:\n{context}"),
            HumanMessage(content="""Fournissez un bref résumé (3-4 phrases) qui met en lumière les forces observées dans le raisonnement de l'apprenant et les points où son approche diverge de celle des experts. N'utilisez aucun score ni évaluation numérique — concentrez-vous sur les justifications qualitatives (forces et pistes de réflexion).
Puis suggérez 2-3 façons spécifiques dont l'apprenant peut explorer leurs résultats plus en profondeur.""")
        ]

        response = self.llm.invoke(messages)

        # Track token usage for initial feedback
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            turn_tokens = response.usage_metadata.get('input_tokens', 0) + response.usage_metadata.get('output_tokens', 0)
            self.total_tokens += turn_tokens
            print(f"📊 Initial feedback tokens: {turn_tokens} | Cumulative: {self.total_tokens}")

        return response.content

    def reset(self):
        """Reset the conversation"""
        self.conversation_history = []
        self.initial_feedback_given = False
