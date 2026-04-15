from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
import os
import sys
from pathlib import Path
import concurrent.futures
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

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


def run_evaluations(training_type: str = "migraine") -> Dict[str, Dict[str, Any]]:
    """Run evaluations for training modules based on training type"""
    print("\n" + "="*80)
    print(f"🚀 Starting Evaluations for training type: {training_type}")
    print("="*80)

    if training_type == "migraine":
        from trainings_2_experts import training_1, training_2, training_3
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

    elif training_type == "nursing_1st":
        from trainings_nursing_1stLearner import training_1
        eval_1 = evaluate_training(training_1, "Nursing Leadership (1st Learner)")
        print("\n✅ Evaluation completed!")
        return {"training_1": eval_1}

    elif training_type == "nursing_2nd":
        from trainings_nursing_2ndLearner import training_1
        eval_1 = evaluate_training(training_1, "Nursing Leadership (2nd Learner)")
        print("\n✅ Evaluation completed!")
        return {"training_1": eval_1}

    elif training_type == "leadership_1st":
        from trainings_leadership_1srLearner import training_1
        eval_1 = evaluate_training(training_1, "Leadership (1st Learner)")
        print("\n✅ Evaluation completed!")
        return {"training_1": eval_1}

    elif training_type == "leadership_2nd":
        from trainings_leadership_2ndLearner import training_1
        eval_1 = evaluate_training(training_1, "Leadership (2nd Learner)")
        print("\n✅ Evaluation completed!")
        return {"training_1": eval_1}

    elif training_type == "leadership_3rd":
        from trainings_leadership_3rdLearner import training_1
        eval_1 = evaluate_training(training_1, "Leadership (3rd Learner)")
        print("\n✅ Evaluation completed!")
        return {"training_1": eval_1}

    else:
        raise ValueError(f"Unknown training type: {training_type}")
