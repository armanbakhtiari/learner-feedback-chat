from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
import os
import sys
from pathlib import Path
import concurrent.futures
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from trainings_2_experts import training_1, training_2, training_3
from prompts import EVALUATOR_PROMPT
from models import TrainingEvaluation

load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
if not os.getenv("LANGCHAIN_API_KEY"):
    print("⚠️  Warning: LANGCHAIN_API_KEY not found in .env file. LangSmith tracing will be disabled.")


def get_claude_model():
    """Initialize Claude model"""
    return ChatAnthropic(
        model="claude-sonnet-4-5",
        temperature=0.3,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )


def evaluate_training(training_content: str, training_name: str) -> Dict[str, Any]:
    """Evaluate a single training module"""
    print(f"\n🔍 Evaluating {training_name}...")

    llm = get_claude_model()
    structured_llm = llm.with_structured_output(TrainingEvaluation)

    messages = [
        SystemMessage(content=EVALUATOR_PROMPT),
        HumanMessage(content=training_content)
    ]

    result = structured_llm.invoke(messages)
    evaluation_dict = result.model_dump()

    print(f"✅ {training_name} evaluation completed")
    return evaluation_dict


def run_evaluations() -> Dict[str, Dict[str, Any]]:
    """Run evaluations for all training modules in parallel"""
    print("\n" + "="*80)
    print("🚀 Starting Parallel Evaluations")
    print("="*80)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_1 = executor.submit(evaluate_training, training_1, "Training 1")
        future_2 = executor.submit(evaluate_training, training_2, "Training 2")
        future_3 = executor.submit(evaluate_training, training_3, "Training 3")

        eval_1 = future_1.result()
        eval_2 = future_2.result()
        eval_3 = future_3.result()

    print("\n✅ All evaluations completed!")

    return {
        "training_1": eval_1,
        "training_2": eval_2,
        "training_3": eval_3
    }
