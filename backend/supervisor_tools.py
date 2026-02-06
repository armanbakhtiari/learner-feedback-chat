"""
Tools for the Supervisor Agent

These tools are decorated with @tool so they can be used by LangChain's create_react_agent.
The supervisor agent will decide when and how to call these tools based on user queries.

NOTE: All heavy imports (CodeGenerationTool, WebSearchTool, RAG) are lazy-loaded
to speed up application startup and pass health checks.
"""

from typing import Dict, Any, List
from langchain.tools import tool
from langchain_core.messages import BaseMessage
import json


# Global instances (will be initialized by supervisor)
_code_tool_instance = None
_web_search_tool_instance = None
_rag_module_instance = None

# Lazy import cache
_training_data_cache = None


def _get_training_data():
    """Lazy load training data"""
    global _training_data_cache
    if _training_data_cache is None:
        from trainings_2_experts import training_1, training_2, training_3
        _training_data_cache = (training_1, training_2, training_3)
    return _training_data_cache


def initialize_tools(evaluations: Dict[str, Any]):
    """Initialize tool instances with evaluation data"""
    global _code_tool_instance, _web_search_tool_instance, _rag_module_instance
    
    # Lazy import CodeGenerationTool
    from backend.code_tool import CodeGenerationTool
    _code_tool_instance = CodeGenerationTool(evaluations)
    
    # Lazy import WebSearchTool
    from backend.web_search_tool import WebSearchTool
    _web_search_tool_instance = WebSearchTool()
    
    # Lazy import and initialize RAG module
    from backend.rag_tool import get_rag_module
    _rag_module_instance = get_rag_module()


@tool
def generate_visualization(user_request: str, conversation_history: str, data_context: str = "", include_evaluation_data: bool = False) -> str:
    """
    Generate a visualization (chart, table, graph) based on the user's request.

    Use this tool when the user asks for:
    - Tables ("tableau", "table")
    - Charts or graphs ("graphique", "chart", "graph")
    - Visual comparisons ("comparer", "comparaison")
    - Statistics display ("statistique", "diagramme", "courbe", "histogramme")

    Args:
        user_request: The user's message requesting a visualization. 
                      IMPORTANT: Include the SPECIFIC DATA or CONTEXT that should be visualized!
                      If the user asks to visualize data from a previous response, include that data here.
        conversation_history: JSON string of recent conversation messages
        data_context: Optional additional context or data to visualize (e.g., retrieved content, 
                      previous assistant responses with specific data, tables, or lists that 
                      should be visualized)
        include_evaluation_data: Set to True ONLY if the visualization is about the learner's 
                                 performance, evaluation scores, or training results.
                                 Set to False if visualizing other data (diagnostic criteria, 
                                 guidelines, knowledge base content, etc.)

    Returns:
        JSON string containing:
        - "status": "success" or "error"
        - "code": The generated Python code (if successful)
        - "output": Base64 image and summary data (if successful)
        - "error": Error message (if failed)

    Examples:
        1. User asks about their performance:
           -> include_evaluation_data=True, data_context="" (evaluation data will be included)
        
        2. User asks to visualize diagnostic criteria from knowledge base:
           -> include_evaluation_data=False, data_context="Les critères: 1)..., 2)..."
    """
    if _code_tool_instance is None:
        return json.dumps({"status": "error", "error": "Code tool not initialized"})

    try:
        # Parse conversation history
        history = json.loads(conversation_history) if conversation_history else []

        # Convert to BaseMessage objects
        from langchain_core.messages import HumanMessage, AIMessage
        messages = []
        for msg in history:
            if msg.get("type") == "human":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("type") == "ai":
                messages.append(AIMessage(content=msg.get("content", "")))

        # If data_context is provided, add it as a synthetic message for context
        if data_context:
            # Add the specific data context as a message so the code tool can see it
            messages.append(AIMessage(content=f"[Relevant Context for Visualization]:\n{data_context}"))
        
        # Combine user request with data context for better understanding
        full_request = user_request
        if data_context:
            full_request = f"{user_request}\n\n[Data to Visualize]:\n{data_context}"

        # Generate visualization - pass flag for whether to include evaluation data
        result = _code_tool_instance.generate_code(full_request, messages, include_evaluation_data)

        if result:
            # result["output"] is already a dict, not a JSON string
            output_data = result.get("output", {})
            
            # If output_data is a string (error case), parse it
            if isinstance(output_data, str):
                try:
                    output_data = json.loads(output_data)
                except Exception as e:
                    print(f"❌ Failed to parse visualization output: {e}")
                    output_data = {"error": str(output_data)}
            
            return json.dumps({
                "status": "success",
                "code": result.get("code", ""),
                "output": output_data  # This is now guaranteed to be a dict
            }, ensure_ascii=False)
        else:
            return json.dumps({"status": "error", "error": "Failed to generate visualization"})

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


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
    Retrieve the full content of a training module when the user asks about specific training scenarios,
    clinical cases, or expert panel responses that are not in the evaluation summary.

    Use this tool when:
    - User asks about specific scenarios/situations in a training module
    - User wants to see what experts said in a particular case
    - User asks about training content details beyond their evaluation scores
    - User references specific module numbers (1, 2, or 3)

    Args:
        module_number: The training module number (1, 2, or 3)
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
        # Get training data lazily
        training_1, training_2, training_3 = _get_training_data()
        
        # Map module numbers to training content
        modules = {
            1: {
                "name": "Module 1: Diagnostic et suivi de la migraine",
                "content": training_1
            },
            2: {
                "name": "Module 2: Traitement aigu et gestion des habitudes de vie",
                "content": training_2
            },
            3: {
                "name": "Module 3: Traitement préventif de la migraine",
                "content": training_3
            }
        }

        if module_number not in modules:
            return json.dumps({
                "status": "error",
                "error": f"Invalid module number: {module_number}. Must be 1, 2, or 3."
            })

        module = modules[module_number]

        return json.dumps({
            "status": "success",
            "module_name": module["name"],
            "content": module["content"],
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
        - "status": "success" or "error"
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
        return json.dumps({"status": "error", "error": "RAG module not initialized"})
    
    try:
        # If no user message provided, use query as context
        if not user_message:
            user_message = query
        
        # Perform agentic RAG search
        result = _rag_module_instance.search(query, user_message)
        
        if result.get("status") == "success":
            # Format chunks for context
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
                "found_relevant": result.get("found_relevant", False)
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "query_history": result.get("query_history", [])
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# List of all tools (for easy access)
ALL_TOOLS = [generate_visualization, search_web, get_training_content, search_knowledge_base]
