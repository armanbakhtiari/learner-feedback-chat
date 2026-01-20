from typing import List, Dict, Any
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()


class WebSearchTool:
    """Tool for performing web searches using Tavily API"""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY", "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")
        self.client = TavilyClient(api_key=api_key)

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform a web search and return results with citations.

        Args:
            query: The search query
            max_results: Maximum number of results to return

        Returns:
            List of search results with title, url, and content
        """
        try:
            print(f"🔍 Searching web for: {query}")

            # Perform search
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=True
            )

            results = []

            # Extract results
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0)
                })

            # Add direct answer if available
            answer = response.get("answer")
            if answer:
                results.insert(0, {
                    "title": "Direct Answer",
                    "url": "",
                    "content": answer,
                    "score": 1.0
                })

            print(f"✅ Found {len(results)} results")
            return results

        except Exception as e:
            print(f"❌ Error performing web search: {e}")
            import traceback
            traceback.print_exc()
            return []

    def format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """
        Format search results for LLM consumption.

        Args:
            results: List of search results

        Returns:
            Formatted string with search results
        """
        if not results:
            return "No search results found."

        formatted = "Web Search Results:\n\n"

        for i, result in enumerate(results, 1):
            formatted += f"[{i}] {result['title']}\n"
            if result['url']:
                formatted += f"URL: {result['url']}\n"
            formatted += f"Content: {result['content']}\n\n"

        return formatted

    def get_citations(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract citations from search results.

        Args:
            results: List of search results

        Returns:
            List of citations with title and url
        """
        citations = []

        for result in results:
            if result['url']:  # Skip direct answer which has no URL
                citations.append({
                    "title": result['title'],
                    "url": result['url']
                })

        return citations
