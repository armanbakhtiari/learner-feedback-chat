"""
Supervisor Agent

The supervisor agent decides which tools to call based on the user's query.
It uses Claude with tool binding to handle tool calling automatically.
"""

from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import os
import json

from backend.supervisor_tools import (
    ALL_TOOLS,
    initialize_tools,
    generate_visualization,
    search_web,
    get_training_content,
    search_knowledge_base
)


SUPERVISOR_SYSTEM_PROMPT = """You are a supervisor agent that decides which tools to call to help answer the user's question.

# Your Responsibilities:

1. **Analyze the user's request** and determine if any tools are needed
2. **Call the appropriate tool(s)** to gather necessary information
3. **Return the tool results** so the chat agent can generate the final response

# Available Tools:

- **generate_visualization**: Call ONLY when user EXPLICITLY asks for tables, charts, graphs, or visual displays
  - EXPLICIT keywords that REQUIRE visualization: "tableau", "graphique", "chart", "créer un tableau", "montrer un graphique", "afficher un diagramme"
  - DO NOT call for analysis questions like "où", "quand", "comment", "pourquoi", "quel scénario"
  - DO NOT call for questions that can be answered with text like "in which scenario", "where did I", "what was my performance"
  - ONLY call when the user explicitly wants a visual/tabular OUTPUT, not just an analysis

- **search_web**: Call when user asks about latest/recent/current information
  - Keywords: "dernière", "récent", "actuel", "nouveau"
  - ONLY if web_search_enabled is True

- **get_training_content**: Call when user asks about specific training scenarios or what experts said
  - Keywords: "scénario", "situation", "module", "experts disent", "formation"

- **search_knowledge_base**: Call for SPECIALIZED domain questions that require reference material
  - Use this for questions about: specific concepts, criteria, classifications, best practices, 
    protocols, guidelines, procedures, methodologies, recommendations
  - Keywords: "critères", "diagnostic", "traitement", "guideline", "recommandation", 
    "classification", "protocole", "procédure", "méthodologie"
  - Formulate a clear, domain-specific query when calling this tool
  - DO NOT use for questions about the user's specific performance or training results
  - This tool retrieves information from reference documents in the knowledge base

# Decision Guidelines:

- **BE CONSERVATIVE**: Most questions about the user's own performance can be answered without tools
- You can call MULTIPLE tools if needed, but ONLY if truly necessary
- If web search is disabled (web_search_enabled=false), do NOT call search_web
- If the question is asking for ANALYSIS or EXPLANATION of user's performance, do NOT call visualization tool
- If the question is asking for a VISUAL DISPLAY explicitly, then call visualization tool
- For specialized domain questions (not about user's performance), use search_knowledge_base
- Default to NO TOOLS unless you're certain a tool is needed

# Tool Selection Priority:

1. **User performance questions** → No tool needed (chat agent has evaluation data)
2. **Visualization requests** → generate_visualization
3. **Training scenario questions** → get_training_content
4. **Specialized domain questions** → search_knowledge_base
5. **Latest/current information** → search_web (if enabled)

# Important:

- You are NOT the chat agent - you only decide which tools to call
- After calling tools (or deciding no tools are needed), the results will be passed to the chat agent
- The chat agent will generate the final response to the user
- The chat agent has access to ALL evaluation data and can answer most questions without tools
- When using search_knowledge_base, formulate the query in domain-specific terms for better retrieval
"""


class SupervisorAgent:
    """Supervisor agent that decides which tools to call"""

    def __init__(self, evaluations: Dict[str, Any]):
        self.evaluations = evaluations

        # Initialize tools with evaluation data
        initialize_tools(evaluations)

        # Create LLM for supervisor with tool binding
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5",
            temperature=0.3,  # Lower temperature for more consistent decisions
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        # Bind tools to the LLM
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)

    def decide(
        self,
        user_message: str,
        conversation_history: List[BaseMessage],
        web_search_enabled: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze the user's request and decide which tools to call.

        Args:
            user_message: The user's current message
            conversation_history: List of previous messages
            web_search_enabled: Whether web search is enabled

        Returns:
            Dictionary containing:
            - tools_called: List of tool names that were called
            - tool_results: Results from each tool
            - ready_for_chat: Whether to proceed to chat agent
            - context_additions: Additional context for chat agent
        """
        print(f"\n{'='*60}")
        print(f"🎯 SUPERVISOR: Analyzing user request")
        print(f"   Web Search: {'ON' if web_search_enabled else 'OFF'}")
        print(f"{'='*60}")

        try:
            # Format conversation history
            chat_history = self._format_conversation_history(conversation_history)

            # Create prompt
            messages = [
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
                HumanMessage(content=f"""
User Request: {user_message}
Web Search Enabled: {web_search_enabled}
Recent Conversation: {chat_history}

Analyze the request and call appropriate tools. If no tools are needed, just respond with "No tools needed".
""")
            ]

            # Get initial response with tool calls
            response = self.llm_with_tools.invoke(messages)

            # Initialize results
            tools_called = []
            tool_results = {}

            # Process tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"\n🔧 Tools to call: {[tc['name'] for tc in response.tool_calls]}")

                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    print(f"\n📞 Calling tool: {tool_name}")
                    print(f"   Args: {tool_args}")

                    # Find and execute the tool
                    tool_func = None
                    for tool in ALL_TOOLS:
                        if tool.name == tool_name:
                            tool_func = tool
                            break

                    if tool_func:
                        try:
                            result = tool_func.invoke(tool_args)
                            tools_called.append(tool_name)
                            tool_results[tool_name] = json.loads(result) if isinstance(result, str) else result
                            print(f"   ✅ Success: {tool_name}")
                        except Exception as e:
                            print(f"   ❌ Error in {tool_name}: {e}")
                            tool_results[tool_name] = {"status": "error", "error": str(e)}
                    else:
                        print(f"   ⚠️  Tool not found: {tool_name}")
            else:
                print(f"\n✅ No tools needed for this query")

            # Generate summary of what was done
            context_summary = self._generate_context_summary(tools_called, tool_results)

            return {
                "tools_called": tools_called,
                "tool_results": tool_results,
                "ready_for_chat": True,
                "context_additions": context_summary
            }

        except Exception as e:
            print(f"\n❌ SUPERVISOR ERROR: {e}")
            import traceback
            traceback.print_exc()

            return {
                "tools_called": [],
                "tool_results": {},
                "ready_for_chat": True,
                "context_additions": "",
                "error": str(e)
            }

    def _format_conversation_history(self, messages: List[BaseMessage]) -> str:
        """Format conversation history for the supervisor"""
        formatted = []
        for msg in messages[-5:]:  # Only last 5 messages
            if isinstance(msg, HumanMessage):
                formatted.append({"type": "human", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted.append({"type": "ai", "content": msg.content})

        return json.dumps(formatted, ensure_ascii=False)

    def _generate_context_summary(self, tools_called: List[str], tool_results: Dict[str, Any]) -> str:
        """Generate a human-readable summary of what tools were called and what they produced"""
        if not tools_called:
            return ""

        summary_parts = []

        # Visualization summary
        if "generate_visualization" in tools_called:
            viz_result = tool_results.get("generate_visualization", {})
            if viz_result.get("status") == "success":
                summary_parts.append("A visualization has been generated and will appear as an image. Write a brief 1-2 sentence introduction starting with 'Le tableau ci-dessus présente...' then provide insights. Do NOT create markdown tables.")

        # Web search summary
        if "search_web" in tools_called:
            search_result = tool_results.get("search_web", {})
            if search_result.get("status") == "success":
                num_results = len(search_result.get("results", []))
                summary_parts.append(f"Web search completed with {num_results} sources. Use the search results in your answer and include inline citations [1], [2], [3].")

        # Training content summary
        if "get_training_content" in tools_called:
            content_result = tool_results.get("get_training_content", {})
            if content_result.get("status") == "success":
                module_name = content_result.get("module_name", "Unknown module")
                summary_parts.append(f"Training content retrieved: {module_name}. Use it to answer the user's question, referencing specific scenarios and expert opinions.")

        # RAG knowledge base summary
        if "search_knowledge_base" in tools_called:
            rag_result = tool_results.get("search_knowledge_base", {})
            if rag_result.get("status") == "success":
                sources = rag_result.get("sources", [])
                found_relevant = rag_result.get("found_relevant", False)
                sources_str = ", ".join(sources[:3]) if sources else "reference documents"
                
                if found_relevant:
                    summary_parts.append(
                        f"Knowledge base search completed. Relevant information found from: {sources_str}. "
                        f"Use this information to provide an evidence-based answer. "
                        f"Cite the source documents when referencing specific information."
                    )
                else:
                    summary_parts.append(
                        f"Knowledge base search completed. Limited relevant information found from: {sources_str}. "
                        f"Use the available information but note that it may not fully address the query. "
                        f"Consider suggesting the user consult additional resources if needed."
                    )

        return "\n".join(summary_parts)
