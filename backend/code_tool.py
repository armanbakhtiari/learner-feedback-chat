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
You are a Creative Python Visualization Expert. Your specialty is creating beautiful, unique, and informative data visualizations.

# Task
Generate Python code to create visualizations (charts, tables, graphs) based on the provided data and context.

# CRITICAL REQUIREMENTS (Technical - Must Follow)
1. **MUST define a function called `generate_visualization(evaluations: dict) -> dict`**
2. **Function must return a dictionary with keys: "image_base64" and "summary_data"**
3. **Do NOT use plt.show() - it won't work in this environment**
4. **Do NOT save to file - convert figure to base64 string**
5. **All labels, titles, and text must be in French**
6. **ALWAYS use plt.close() after saving to buffer**

# CREATIVE FREEDOM (Encouraged)
Be creative with your visualizations! Vary your approach each time:

**Color Schemes** - Don't always use the same colors! Try:
- Professional blues and grays
- Warm sunset gradients (oranges, reds, yellows)
- Cool ocean themes (teals, blues, aquas)
- Nature-inspired (greens, browns, earth tones)
- Vibrant contrasts (purples, pinks, cyans)
- Monochromatic with accent color
- Seaborn color palettes: 'viridis', 'plasma', 'husl', 'Set2', 'coolwarm', 'RdYlBu'

**Visualization Types** - Choose the best type for the data:
- Bar charts (horizontal or vertical, grouped or stacked)
- Pie charts, donut charts
- Line graphs with area fills
- Heatmaps for comparisons
- Radar/spider charts for multi-dimensional data
- Tables with styled cells (use matplotlib table or custom drawings)
- Combination charts (bar + line)
- Treemaps, bubble charts

**Styling Ideas**:
- Rounded corners on bars
- Gradient fills
- Custom fonts and sizes
- Shadow effects
- Different background colors (not always white!)
- Annotations and callouts
- Icons or emojis in text
- Grid styles (dotted, dashed, or hidden)

# Available Libraries
- matplotlib.pyplot as plt (with all styling options)
- pandas as pd
- numpy as np
- seaborn as sns (for beautiful statistical visualizations)
- base64, io, json

# Code Structure (Must Follow)
```python
def generate_visualization(evaluations: dict) -> dict:
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    import seaborn as sns
    import base64
    import io

    # 1. Extract and prepare data
    # ... your data preparation code ...

    # 2. Create visualization (BE CREATIVE!)
    fig, ax = plt.subplots(figsize=(12, 8))
    # ... your creative plotting code ...

    # 3. Convert to base64
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()

    # 4. Return result
    return {
        "image_base64": image_base64,
        "summary_data": {...}  # Any relevant summary
    }
```

# Important
- Generate ONLY the function code
- Use the CONTEXT PROVIDED to create the visualization - this is what the user wants visualized!
- If context includes specific data (tables, lists, comparisons), visualize THAT data
- If context is about evaluations, use the evaluations dict
- Be creative with styling while keeping the output professional and readable
"""


class CodeGenerationTool:
    def __init__(self, evaluations: Dict[str, Any]):
        self.evaluations = evaluations
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5",
            temperature=0.7,  # Higher temperature for creative visualizations
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    def generate_code(self, user_request: str, conversation_history: List[BaseMessage]) -> Optional[Dict[str, Any]]:
        """Generate and execute Python code for visualization"""

        print(f"🔧 Code generation tool called for: {user_request[:50]}...")

        # Extract relevant context from conversation history
        context_parts = []
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            if hasattr(msg, 'content') and msg.content:
                # Truncate very long messages but keep enough context
                content = msg.content[:2000] if len(msg.content) > 2000 else msg.content
                role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                context_parts.append(f"[{role}]: {content}")
        
        conversation_context = "\n\n".join(context_parts) if context_parts else "No previous context."

        # Create prompt for code generation with FULL context
        messages = [
            SystemMessage(content=CODE_GENERATION_PROMPT),
            HumanMessage(content=f"""# USER REQUEST
{user_request}

# CONVERSATION CONTEXT (Use this to understand what data to visualize!)
{conversation_context}

# EVALUATION DATA STRUCTURE (Available in the function)
{json.dumps(self._get_data_sample(), indent=2, ensure_ascii=False)}

# INSTRUCTIONS
1. Look at the CONVERSATION CONTEXT above - it contains the specific data the user wants visualized
2. If the user mentions data from the conversation (tables, lists, comparisons), create a visualization of THAT data
3. Use the evaluation data structure only if the user asks about their performance/evaluation
4. Be creative with colors, styles, and visualization types!

Generate Python code to create this visualization.
""")
        ]

        # Get code from LLM
        print(f"📝 Requesting code from Claude...")
        print(f"📋 Context provided: {len(conversation_context)} chars from {len(context_parts)} messages")
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
