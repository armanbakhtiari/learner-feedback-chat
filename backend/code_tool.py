from typing import Dict, Any, Optional, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
import os
import json
import sys
import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import base64
from dotenv import load_dotenv

load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Feedback_Chat_Agent"
if not os.getenv("LANGCHAIN_API_KEY"):
    print("⚠️  Warning: LANGCHAIN_API_KEY not found in .env file. LangSmith tracing will be disabled.")


CODE_GENERATION_PROMPT = """# Role
You are a Python Code Generation Expert specializing in data visualization for educational assessments.

# Task
Generate Python code to create visualizations (charts, tables, graphs) based on learner evaluation data.

# Context
You have access to evaluation data with this structure:
- Each training has multiple situations
- Each situation has multiple scenarios
- Each scenario has:
  - coverage assessment (High/Medium/Low)
  - logical_reasoning rating (Satisfactory/Unsatisfactory)
  - communication rating (Excellent/Good/Needs Improvement)
  - skills_assessment for each learning objective

# CRITICAL REQUIREMENTS
1. **MUST define a function called `generate_visualization(evaluations: dict) -> dict`**
2. **Function must return a dictionary with keys: "image_base64" and "summary_data"**
3. **Do NOT use plt.show() - it won't work in this environment**
4. **Do NOT save to file - convert figure to base64 string**
5. **All labels, titles, and text must be in French**

# Available Libraries
The following are already imported and available:
- matplotlib.pyplot as plt
- pandas as pd
- numpy as np
- base64, io, json

# Code Template (MUST FOLLOW THIS STRUCTURE)
```python
def generate_visualization(evaluations: dict) -> dict:
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    import base64
    import io

    # 1. Extract and prepare data from evaluations
    # ... your data preparation code ...

    # 2. Create visualization
    fig, ax = plt.subplots(figsize=(12, 8))
    # ... your plotting code ...

    # 3. Convert to base64
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()

    # 4. Return result
    return {
        "image_base64": image_base64,
        "summary_data": {...}  # Optional: any summary statistics
    }
```

# Important Notes
- DO NOT include any code outside the function
- DO NOT use plt.show()
- DO NOT save to file (plt.savefig('file.png'))
- ALWAYS use plt.close() after saving to buffer
- Return the dictionary as shown above

Generate ONLY the function code based on the user's request.
"""


class CodeGenerationTool:
    def __init__(self, evaluations: Dict[str, Any]):
        self.evaluations = evaluations
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5",
            temperature=0.3,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    def generate_code(self, user_request: str, conversation_history: List[BaseMessage]) -> Optional[Dict[str, Any]]:
        """Generate and execute Python code for visualization"""

        print(f"🔧 Code generation tool called for: {user_request[:50]}...")

        # Create prompt for code generation
        messages = [
            SystemMessage(content=CODE_GENERATION_PROMPT),
            HumanMessage(content=f"""
User request: {user_request}

Evaluation data structure (sample):
{json.dumps(self._get_data_sample(), indent=2, ensure_ascii=False)}

Generate Python code to fulfill this request.
""")
        ]

        # Get code from LLM
        print(f"📝 Requesting code from Claude...")
        response = self.llm.invoke(messages)
        code = self._extract_code(response.content)

        if not code:
            print(f"⚠️  No code extracted from LLM response")
            return None

        print(f"✅ Code extracted ({len(code)} chars)")
        print(f"🔍 First 200 chars: {code[:200]}...")

        # Execute code
        try:
            print(f"⚙️  Executing code...")
            result = self._execute_code(code)
            print(f"✅ Code executed successfully")
            return {
                "code": code,
                "output": result
            }
        except Exception as e:
            print(f"❌ Code execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "code": code,
                "output": f"Error executing code: {str(e)}"
            }

    def _get_data_sample(self) -> Dict[str, Any]:
        """Get a sample of the evaluation data"""
        if not self.evaluations:
            return {}

        # Get first training and first situation/scenario as sample
        first_training = list(self.evaluations.keys())[0]
        sample = {
            first_training: self.evaluations[first_training]
        }
        return sample

    def _extract_code(self, response: str) -> Optional[str]:
        """Extract Python code from LLM response"""
        # Remove markdown code blocks if present
        if "```python" in response:
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + len("```")
            end = response.find("```", start)
            return response[start:end].strip()
        else:
            return response.strip()

    def _execute_code(self, code: str) -> Dict[str, Any]:
        """Execute the generated code safely and return the result dictionary"""
        # Create a restricted execution environment
        exec_globals = {
            'evaluations': self.evaluations,
            'plt': plt,
            'base64': base64,
            'io': io,
            'json': json,
            '__builtins__': __builtins__
        }

        # Try to import common libraries
        try:
            import pandas as pd
            import numpy as np
            exec_globals['pd'] = pd
            exec_globals['np'] = np
        except ImportError:
            pass

        try:
            import seaborn as sns
            exec_globals['sns'] = sns
        except ImportError:
            pass

        try:
            # Execute the code
            exec(code, exec_globals)

            # Call the generated function
            if 'generate_visualization' in exec_globals:
                result = exec_globals['generate_visualization'](self.evaluations)
                # Return the dict directly, not as JSON string
                return result
            else:
                error_msg = "Error: No generate_visualization function found in generated code"
                print(f"❌ {error_msg}")
                return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error executing visualization code: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {"error": error_msg}


def example_visualization_code():
    """Example code for generating a visualization"""
    code = """
import matplotlib.pyplot as plt
import base64
import io
import json

def generate_visualization(evaluations: dict) -> dict:
    # Count coverage scores across all scenarios
    coverage_counts = {"High": 0, "Medium": 0, "Low": 0}

    for training_key, training_data in evaluations.items():
        if 'situations' in training_data:
            for sit_key, situation in training_data['situations'].items():
                if 'scenarios' in situation:
                    for scen_key, scenario in situation['scenarios'].items():
                        if 'coverage' in scenario:
                            score = scenario['coverage'].get('score_assessment', '')
                            if score in coverage_counts:
                                coverage_counts[score] += 1

    # Create bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    categories = list(coverage_counts.keys())
    values = list(coverage_counts.values())

    colors = ['#2ecc71', '#f39c12', '#e74c3c']
    ax.bar(categories, values, color=colors, alpha=0.7)

    ax.set_xlabel('Niveau de couverture', fontsize=12)
    ax.set_ylabel('Nombre de scénarios', fontsize=12)
    ax.set_title('Distribution de la couverture des éléments experts', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Convert to base64
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()

    return {
        "image_base64": image_base64,
        "summary_data": coverage_counts
    }
"""
    return code
