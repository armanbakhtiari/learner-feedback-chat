"""
Tools for the Supervisor Agent

These tools are decorated with @tool so they can be used by LangChain's create_react_agent.
The supervisor agent will decide when and how to call these tools based on user queries.

NOTE: All heavy imports (WebSearchTool, RAG) are lazy-loaded
to speed up application startup and pass health checks.
"""

from typing import Dict, Any, List
from langchain.tools import tool
from langchain_core.messages import BaseMessage
import json


# Global instances (will be initialized by supervisor)
_web_search_tool_instance = None
_rag_module_instance = None

# Lazy import cache
_training_data_cache = None

# Current training type (set during initialization)
_current_training_type = "migraine"


def _get_training_data():
    """Lazy load training data based on current training type"""
    global _training_data_cache
    if _training_data_cache is None:
        if _current_training_type == "migraine":
            from trainings_2_experts import training_1, training_2, training_3
            _training_data_cache = {"training_1": training_1, "training_2": training_2, "training_3": training_3}
        elif _current_training_type == "nursing_1st":
            from trainings_nursing_1stLearner import training_1
            _training_data_cache = {"training_1": training_1}
        elif _current_training_type == "nursing_2nd":
            from trainings_nursing_2ndLearner import training_1
            _training_data_cache = {"training_1": training_1}
        elif _current_training_type == "leadership_1st":
            from trainings_leadership_1srLearner import training_1
            _training_data_cache = {"training_1": training_1}
        elif _current_training_type == "leadership_2nd":
            from trainings_leadership_2ndLearner import training_1
            _training_data_cache = {"training_1": training_1}
        elif _current_training_type == "leadership_3rd":
            from trainings_leadership_3rdLearner import training_1
            _training_data_cache = {"training_1": training_1}
    return _training_data_cache


def initialize_tools(evaluations: Dict[str, Any], training_type: str = "migraine"):
    """Initialize tool instances with evaluation data and training type"""
    global _web_search_tool_instance, _rag_module_instance
    global _current_training_type, _training_data_cache

    _current_training_type = training_type
    _training_data_cache = None  # Reset cache when training type changes

    # Lazy import WebSearchTool
    from backend.web_search_tool import WebSearchTool
    _web_search_tool_instance = WebSearchTool()

    # Lazy import and initialize RAG module for the correct training type
    from backend.rag_tool import get_rag_module
    _rag_module_instance = get_rag_module(training_type)


@tool
def search_web(query: str) -> str:
    """
    Search the web for current medical information, guidelines, or recent research.

    Use this tool when the user asks about:
    - Latest information ("dernière", "récent", "actuel", "nouveau")
    - Current guidelines or recommendations ("guideline", "recommandation")
    - Recent studies or research ("étude", "recherche médicale", "littérature")
    - Updated medical practices ("mise à jour")
    - Anything requiring external/current knowledge beyond the training materials

    Args:
        query: The search query (can be in French or English)

    Returns:
        JSON string containing:
        - "status": "success" or "error"
        - "results": List of search results with title, url, content
        - "citations": List of citations with title and url
        - "formatted": Formatted text for LLM consumption

    Example:
        User: "Quelles sont les dernières recommandations pour la migraine?"
        -> Call this tool with query="latest migraine treatment guidelines"
        -> Returns search results with citations
    """
    if _web_search_tool_instance is None:
        return json.dumps({"status": "error", "error": "Web search tool not initialized"})

    try:
        # Perform search
        results = _web_search_tool_instance.search(query, max_results=5)

        # Format results
        formatted = _web_search_tool_instance.format_results_for_llm(results)
        citations = _web_search_tool_instance.get_citations(results)

        return json.dumps({
            "status": "success",
            "results": results,
            "citations": citations,
            "formatted": formatted
        })

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
def get_training_content(module_number: int, section: str = "all") -> str:
    """
    Retrieve the full content of a training module when the user asks about specific training scenarios, or expert panel responses that are not in the evaluation summary.

    Use this tool when:
    - User asks about specific scenarios/situations in a training module
    - User wants to see what experts said in a particular case
    - User asks about training content details beyond their evaluation scores
    - User references the training module

    Args:
        module_number: The training module number (available modules depend on training type)
        section: Which section to retrieve ("all", "scenarios", "objectives")

    Returns:
        JSON string containing:
        - "status": "success" or "error"
        - "module_name": Name of the module
        - "content": The full training content
        - "section": Which section was retrieved

    Example:
        User: "Que disent les experts dans le scénario 2 du module 1?"
        -> Call this tool with module_number=1, section="all"
        -> Returns full module 1 content so the chat agent can answer
    """
    try:
        training_data = _get_training_data()

        if _current_training_type == "migraine":
            names = {
                "training_1": "Module 1: Diagnostic et suivi de la migraine",
                "training_2": "Module 2: Traitement aigu et gestion des habitudes de vie",
                "training_3": "Module 3: Traitement préventif de la migraine"
            }
        elif _current_training_type in ("leadership_1st", "leadership_2nd", "leadership_3rd"):
            names = {
                "training_1": "Module 1: Leadership et prise de decision"
            }
        else:
            names = {
                "training_1": "Module 1: Leadership et collaboration en soins infirmiers"
            }

        key = f"training_{module_number}"
        if key not in training_data:
            available = list(training_data.keys())
            return json.dumps({
                "status": "error",
                "error": f"Invalid module number: {module_number}. Available: {available}"
            })

        return json.dumps({
            "status": "success",
            "module_name": names.get(key, key),
            "content": training_data[key],
            "section": section
        })

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
def search_knowledge_base(query: str, user_message: str = "") -> str:
    """
    Search the knowledge base using agentic RAG for specialized domain questions.

    This tool uses an intelligent retrieval system that:
    1. Retrieves the top 10 most relevant chunks from reference documents
    2. Uses a Ranking Agent to evaluate if the chunks answer the query
    3. If not relevant, rewrites the query and retries (up to 3 times)
    4. Returns the best matching content from the knowledge base

    IMPORTANT: If after 3 attempts no relevant information is found, this tool
    returns found_relevant=false. The supervisor should then instruct the chat
    agent to inform the user and suggest enabling web search.

    Use this tool when the user asks:
    - Specialized domain questions that require reference material
    - Questions about specific concepts, criteria, or classifications
    - Questions about best practices, protocols, or guidelines
    - Questions that require evidence-based knowledge beyond the training content
    - Questions about procedures, methodologies, or recommendations

    DO NOT use this tool when:
    - User asks about their specific training performance/evaluation (use evaluation data)
    - User asks for visualizations or charts (use generate_visualization)
    - User asks about what experts said in training scenarios (use get_training_content)
    - User asks about current/latest information (use search_web)

    Args:
        query: A well-formulated search query for document retrieval.
               Should focus on domain-specific terminology.
        user_message: The original user message for context (helps with query rewriting)

    Returns:
        JSON string containing:
        - "status": "success" or "no_relevant_info" or "error"
        - "chunks": List of relevant document chunks with source citations
        - "sources": List of source document names
        - "formatted_context": Pre-formatted context for the chat agent
        - "attempts": Number of retrieval attempts made
        - "found_relevant": Whether relevant content was found

    Example:
        User: "What are the diagnostic criteria for this condition?"
        -> Call with query="diagnostic criteria classification guidelines"
        -> Returns relevant chunks from reference documents with citations
    """
    if _rag_module_instance is None:
        # No reference documents exist for this training - fail fast with the
        # exact message the chat agent should relay to the user.
        from backend.rag_tool import NO_DOCUMENTS_MESSAGE
        return json.dumps({
            "status": "no_documents",
            "message": NO_DOCUMENTS_MESSAGE,
            "found_relevant": False,
            "chunks": [],
            "sources": [],
            "attempts": 0,
        }, ensure_ascii=False)

    try:
        if not user_message:
            user_message = query

        # Perform agentic RAG search
        result = _rag_module_instance.search(query, user_message)

        if result.get("found_relevant", False):
            # Found relevant content
            formatted_context = _rag_module_instance.format_chunks_for_context(
                result.get("chunks", [])
            )

            return json.dumps({
                "status": "success",
                "chunks": result.get("chunks", []),
                "sources": result.get("sources", []),
                "formatted_context": formatted_context,
                "query_history": result.get("query_history", []),
                "attempts": result.get("attempts", 1),
                "found_relevant": True
            }, ensure_ascii=False)
        else:
            # No relevant info found after all attempts
            return json.dumps({
                "status": "no_relevant_info",
                "error": "No relevant information found in the knowledge base after 3 attempts.",
                "query_history": result.get("query_history", []),
                "attempts": result.get("attempts", 3),
                "found_relevant": False
            }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# List of all tools (for easy access)
ALL_TOOLS = [search_web, get_training_content, search_knowledge_base]
