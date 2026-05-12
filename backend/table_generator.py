"""
Performance table generator.

Calls Claude with the TABLE_GENERATOR_PROMPT to produce a Python matplotlib
script tailored to the evaluation JSON, executes it in-process, and returns
the resulting PNG as a base64-encoded string.
"""

import io
import json
import base64
import os
import re
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

from backend.example_table import TABLE_GENERATOR_PROMPT
from backend.llm_retry import invoke_with_retry

load_dotenv()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:python)?\s*\n(.*)\n```$", text, flags=re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def _patch_savefig_to_buffer(script: str) -> str:
    """Replace the model's plt.savefig("table1_detailed.png", ...) call with a
    write to the `_buf` BytesIO injected into the exec globals."""
    patched, n = re.subn(
        r'plt\.savefig\(\s*["\']table1_detailed\.png["\']\s*,',
        'plt.savefig(_buf, format="png",',
        script,
    )
    if n == 0:
        # Fallback: append our own save at the end, in case the model renamed.
        patched = script + '\nplt.savefig(_buf, format="png", dpi=180, bbox_inches="tight", facecolor="#F8F9FA")\n'
    return patched


def _exec_table_script(script: str) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    import numpy as np

    buf = io.BytesIO()
    exec_globals: Dict[str, Any] = {
        "__builtins__": __builtins__,
        "matplotlib": matplotlib,
        "plt": plt,
        "mpatches": mpatches,
        "GridSpec": GridSpec,
        "np": np,
        "io": io,
        "base64": base64,
        "_buf": buf,
    }
    try:
        exec(compile(script, "<table_generator>", "exec"), exec_globals)
    finally:
        plt.close("all")

    data = buf.getvalue()
    if not data:
        raise RuntimeError("Table script produced no PNG bytes")
    return data


def generate_performance_table(evaluations: Dict[str, Any]) -> str:
    """Generate the performance table PNG and return it as a base64 string."""
    print("\n🖼️  Generating performance table...")

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    messages = [
        SystemMessage(content=TABLE_GENERATOR_PROMPT),
        HumanMessage(content=json.dumps(evaluations, ensure_ascii=False)),
    ]
    response = invoke_with_retry(llm.invoke, messages)
    script = _strip_code_fences(response.content)
    script = _patch_savefig_to_buffer(script)

    png_bytes = _exec_table_script(script)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    print(f"✅ Performance table generated ({len(b64)} base64 chars)")
    return b64
