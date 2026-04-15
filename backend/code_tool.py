from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
import os
import json
import sys
import io
import base64
from dotenv import load_dotenv

_plt = None

ROOT_DIR = Path(__file__).parent.parent
SENSAI_LOGO_PATH = ROOT_DIR / "frontend" / "assets" / "sensai_logo.png"

def _get_plt():
    global _plt
    if _plt is None:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        _plt = plt
    return _plt


def _make_sensai_header():
    """Build the add_sensai_header(fig) helper injected into generated code.

    If a real SENSAI logo PNG exists at SENSAI_LOGO_PATH, draw it as a
    banner across the top of the figure. Otherwise fall back to a styled
    text banner that matches the SENSAI brand (dark navy background,
    light-blue 'S' and 'I', white middle letters).
    """
    plt = _get_plt()

    def add_sensai_header(fig, height_ratio: float = 0.13):
        # Shrink existing axes to make room for the header
        for ax in fig.axes:
            box = ax.get_position()
            new_height = box.height * (1 - height_ratio)
            ax.set_position([box.x0, box.y0, box.width, new_height])

        header_ax = fig.add_axes([0, 1 - height_ratio, 1, height_ratio])
        header_ax.set_xticks([])
        header_ax.set_yticks([])
        for spine in header_ax.spines.values():
            spine.set_visible(False)

        navy = "#0F2A47"
        accent = "#3E7CB1"

        if SENSAI_LOGO_PATH.exists():
            try:
                import matplotlib.image as mpimg
                img = mpimg.imread(str(SENSAI_LOGO_PATH))
                header_ax.set_facecolor(navy)
                header_ax.imshow(img, aspect="auto", extent=(0, 1, 0, 1))
                header_ax.set_xlim(0, 1)
                header_ax.set_ylim(0, 1)
                return header_ax
            except Exception:
                pass

        # Fallback: styled text banner
        header_ax.set_facecolor(navy)
        header_ax.set_xlim(0, 1)
        header_ax.set_ylim(0, 1)

        # Build "SENSAI" with first/last letters in accent color
        # Use a single styled text; matplotlib doesn't support multi-color text
        # easily, so render "S" + "ENSA" + "I" as three pieces.
        header_ax.text(0.45, 0.5, "S", ha="right", va="center",
                       fontsize=36, fontweight="bold", color=accent,
                       family="DejaVu Sans")
        header_ax.text(0.45, 0.5, "ENSA", ha="left", va="center",
                       fontsize=36, fontweight="bold", color="white",
                       family="DejaVu Sans")
        header_ax.text(0.62, 0.5, "I", ha="left", va="center",
                       fontsize=36, fontweight="bold", color=accent,
                       family="DejaVu Sans")
        return header_ax

    return add_sensai_header

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
7. **MUST call `add_sensai_header(fig)` (already injected into globals) immediately after creating the figure to render the SENSAI brand header at the top of every visualization. Do NOT add any other title above it. Do NOT define your own header.**


# CRITICAL: Do NOT hallucinate data keys or column names!

- **Read the EVALUATION DATA section carefully** before writing any code. The actual data with its
  real keys is provided below — use ONLY those keys.
- **NEVER invent or guess key/column names.** If unsure, iterate with `.keys()` or `.items()`
  to discover structure at runtime rather than hard-coding assumed names.
- **Use defensive access** (e.g., `.get("key", default)`) so the code won't crash on a KeyError.
- When building DataFrames, derive column names from the actual data — do NOT fabricate columns.
- This applies to ALL data: evaluation dicts, context data, knowledge base content, etc.

# CREATIVE FREEDOM (Encouraged)
Be creative with your visualizations! Vary your approach each time:

**Color Schemes — CRITICAL RULES:**
- **NEVER use green, red, amber, orange, or any warning-style color** — even outside a traffic-light scheme. Any saturated red/orange/amber implies judgment.
- **NEVER use colors that suggest pass/fail, good/bad, or performance levels.**
- Instead, use **neutral, tentative palettes** that present data without value judgment:
  - Professional blues and grays (recommended default — match the SENSAI brand)
  - Cool ocean themes (teals, blues, aquas)
  - Soft lavender and slate tones
  - Muted earth tones (tans, warm grays, soft browns)
  - Monochromatic gradients (light-to-dark of a single hue)
  - Seaborn color palettes: 'crest', 'mako', 'Blues', 'BuPu', 'PuBu' (avoid 'flare' and 'rocket' — they contain reds)
- Use color to distinguish categories, NOT to rank or evaluate them.

**Data Presentation — CRITICAL RULES:**
- **NEVER display numerical scores, ratings, or performance levels** (e.g., "High/Medium/Low", "Satisfactory/Unsatisfactory", "85%").
- Instead, focus on **qualitative comparisons**: themes covered vs. themes to explore, alignment with expert reasoning, areas of convergence/divergence.
- Labels should be descriptive and neutral (e.g., "Thèmes abordés", "Perspectives des experts", "Points de convergence") — not evaluative (e.g., "Score", "Performance", "Réussite").
- When showing comparisons, frame them as "learner perspective vs. expert perspective" — not as right/wrong.

**Visualization Types** - Choose the best type for the data:
- Bar charts (horizontal or vertical, grouped or stacked)
- Pie charts, donut charts
- Line graphs with area fills
- Heatmaps for comparisons (use neutral color scales)
- Radar/spider charts for multi-dimensional data
- Tables with styled cells (use matplotlib table or custom drawings)
- Combination charts (bar + line)
- Treemaps, bubble charts

**Styling Ideas**:
- Rounded corners on bars
- Gradient fills (neutral tones)
- Custom fonts and sizes
- Shadow effects
- Different background colors (not always white!)
- Annotations and callouts
- Icons or emojis in text
- Grid styles (dotted, dashed, or hidden)

# TABLES — STRICT RULES (must follow when generating any table)

Tables are notoriously bad when cells overflow. Follow ALL of these:

1. **Cell text MUST be ultra-short** — single keywords or phrases of ≤4 words. NEVER full sentences inside cells.
2. If the source content is a long sentence, **paraphrase it down to a short label** (e.g. "Communication claire", "Decision rapide"). Move the long version to `summary_data`, NOT into the cell.
3. **Cap the row count**: at most 6 rows. If you have more, group / synthesize.
4. **Cap the column count**: at most 4 columns.
5. **Set explicit column widths** that match the figure size: `table = ax.table(..., colWidths=[...])` with widths summing to ≤ 1.0. Give wider columns to text columns and narrower to label columns.
6. **Scale the row height**: `table.scale(1, 2.2)` (or higher) so cells have breathing room. Set `table.auto_set_font_size(False)` and `table.set_fontsize(10)` (or smaller).
7. **Wrap text inside cells**: iterate `for cell in table.get_celld().values(): cell.set_text_props(wrap=True, ha='center', va='center')`.
8. **Be creative with table SHAPE** — vary across requests:
   - Rounded header strip with a darker neutral fill, white text
   - Alternating row shading (very subtle: white / `#F4F6FA` / `#EAEEF5`)
   - Card-style table (no inner borders, only horizontal separators)
   - Two-column comparison table with an icon-prefixed header per column
   - Compact info-card grid (multiple small tables side by side)
9. **Hide the underlying axes** (`ax.axis('off')`) so the table is the only visible element below the SENSAI header.
10. **Figure size**: use `fig, ax = plt.subplots(figsize=(11, 0.9 * n_rows + 2))` so the figure scales with content and never gets cramped.
11. **No numerical scores, no "High/Medium/Low", no percentages, no "Réussi/Échoué".** Stick to qualitative, neutral labels.
12. **No warning-style colors** anywhere in the table (no red/orange/amber, even subtle).

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

    # 2. Create figure + add SENSAI brand header (REQUIRED, always first)
    fig, ax = plt.subplots(figsize=(12, 8))
    add_sensai_header(fig)  # injected helper - draws the SENSAI logo banner on top

    # 3. Create visualization (BE CREATIVE!)
    # ... your creative plotting code ...

    # 4. Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()

    # 5. Return result
    return {
        "image_base64": image_base64,
        "summary_data": {...}  # Any relevant summary
    }
```

Notes:
- `add_sensai_header(fig)` is provided by the runtime — just call it. Do NOT redefine it, do NOT import anything for it.
- Avoid `plt.tight_layout()` after `add_sensai_header` since it can clip the header. Use `bbox_inches='tight'` on `savefig` instead.

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

    def generate_code(self, user_request: str, conversation_history: List[BaseMessage], include_evaluation_data: bool = False) -> Optional[Dict[str, Any]]:
        """Generate and execute Python code for visualization
        
        Args:
            user_request: The user's visualization request
            conversation_history: List of conversation messages for context
            include_evaluation_data: If True, include evaluation data in the prompt.
                                     Only set to True for performance/training visualizations.
        """

        print(f"🔧 Code generation tool called for: {user_request[:50]}...")
        print(f"📊 Include evaluation data: {include_evaluation_data}")

        # Extract relevant context from conversation history
        context_parts = []
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            if hasattr(msg, 'content') and msg.content:
                # Truncate very long messages but keep enough context
                content = msg.content[:2000] if len(msg.content) > 2000 else msg.content
                role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                context_parts.append(f"[{role}]: {content}")
        
        conversation_context = "\n\n".join(context_parts) if context_parts else "No previous context."

        # Build the prompt - only include evaluation data if specifically needed
        if include_evaluation_data:
            # Include evaluation data for performance visualizations
            data_section = f"""# EVALUATION DATA (Available in the function as 'evaluations' parameter)
{json.dumps(self._get_data_sample(), indent=2, ensure_ascii=False)}

# INSTRUCTIONS
1. Use the EVALUATION DATA above to create visualizations comparing the learner's reasoning with expert perspectives
2. The data structure contains: training modules > situations > scenarios with coverage, reasoning, communication analyses
3. Do NOT display numerical scores or ratings — focus on qualitative themes (strengths, divergences, expert key elements)
4. Use neutral color palettes (blues, grays, teals) — NEVER red/green or traffic-light schemes
5. Be creative with styles and visualization types!"""
        else:
            # Don't include evaluation data - use conversation context only
            data_section = """# INSTRUCTIONS
1. Use the DATA in the CONVERSATION CONTEXT above to create the visualization
2. The data to visualize is provided in the context - DO NOT use evaluations data
3. Parse and extract the relevant data from the context, then visualize it
4. Be creative with colors, styles, and visualization types!
5. The function still receives 'evaluations' parameter but IGNORE it - use the context data instead"""

        # Create prompt for code generation
        messages = [
            SystemMessage(content=CODE_GENERATION_PROMPT),
            HumanMessage(content=f"""# USER REQUEST
{user_request}

# CONVERSATION CONTEXT (Contains the data to visualize)
{conversation_context}

{data_section}

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
        plt = _get_plt()
        exec_globals = {
            'evaluations': self.evaluations,
            'plt': plt,
            'base64': base64,
            'io': io,
            'json': json,
            'add_sensai_header': _make_sensai_header(),
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

    colors = ['#4a90d9', '#6c7a89', '#a3c1da']
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
