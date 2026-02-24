#!/usr/bin/env python3
"""
Test Harness - Backend-only entry point for testing the multi-agent feedback chatbot.

Runs the full pipeline:
1. Evaluate training modules (parallel)
2. Initialize vector database (RAG)
3. Generate initial feedback
4. Process pre-defined user messages one-by-one
5. Log all agent calls to a DOCX file
"""

import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent_TEST"

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from agent_logger import AgentLogger
from test_messages import TEST_MESSAGES
from backend.evaluator import run_evaluations
from backend.chat_agent import ChatAgent


def main():
    start_time = time.time()

    print("\n" + "=" * 70)
    print("  TEST HARNESS - Multi-Agent Feedback Chatbot")
    print("=" * 70 + "\n")

    # --- Initialize logger ---
    logger = AgentLogger(output_dir="outputs")
    print(f"DOCX will be saved to: {logger.output_path}\n")

    # =========================================================================
    # PHASE 1: Evaluations
    # =========================================================================
    logger.log_section_header("Phase 1: Training Evaluations")
    print("=" * 70)
    print("PHASE 1: Running evaluations on training modules...")
    print("=" * 70)

    evaluations = run_evaluations(logger=logger)

    elapsed = time.time() - start_time
    print(f"\nEvaluations completed in {elapsed:.1f}s")

    # =========================================================================
    # PHASE 2: Create ChatAgent (initializes RAG / vector DB)
    # =========================================================================
    logger.log_section_header("Phase 2: Chat Agent Initialization & Initial Feedback")
    print("\n" + "=" * 70)
    print("PHASE 2: Creating ChatAgent (vector DB will initialize)...")
    print("=" * 70)

    chat_agent = ChatAgent(evaluations=evaluations, logger=logger)

    elapsed = time.time() - start_time
    print(f"\nChatAgent created in {elapsed:.1f}s total")

    # =========================================================================
    # PHASE 3: Initial feedback
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Generating initial feedback...")
    print("=" * 70)

    initial_message = "Bonjour! Je voudrais voir ma rétroaction."
    logger.log_user_message(0, initial_message)

    response = chat_agent.chat(initial_message, web_search_enabled=False)

    print(f"\n--- Initial Feedback ---")
    print(response.get("response", "")[:500])
    print("--- End ---\n")

    elapsed = time.time() - start_time
    print(f"Initial feedback generated in {elapsed:.1f}s total")

    # =========================================================================
    # PHASE 4: Process pre-defined user messages
    # =========================================================================
    logger.log_section_header("Phase 3: Pre-defined User Messages")
    print("\n" + "=" * 70)
    print(f"PHASE 4: Processing {len(TEST_MESSAGES)} pre-defined user messages...")
    print("=" * 70)

    for i, message in enumerate(TEST_MESSAGES, start=1):
        print(f"\n{'=' * 60}")
        print(f"  USER MESSAGE {i}/{len(TEST_MESSAGES)}")
        print(f"  \"{message[:80]}{'...' if len(message) > 80 else ''}\"")
        print(f"{'=' * 60}")

        logger.log_user_message(i, message)

        msg_start = time.time()
        response = chat_agent.chat(message, web_search_enabled=False)
        msg_elapsed = time.time() - msg_start

        # Print response summary
        resp_text = response.get("response", "")
        has_viz = response.get("has_code", False)
        citations = response.get("citations", [])

        print(f"\n--- Response (took {msg_elapsed:.1f}s) ---")
        print(resp_text[:300])
        if has_viz:
            print("[Visualization generated]")
        if citations:
            print(f"[{len(citations)} citations]")
        print("--- End ---")

    # =========================================================================
    # Save and finish
    # =========================================================================
    logger.save()

    total_elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  DONE - Total time: {total_elapsed:.1f}s")
    print(f"  DOCX saved to: {logger.output_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
