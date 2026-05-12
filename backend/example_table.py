TABLE_GENERATOR_PROMPT = r'''
You convert a structured evaluation (Learning by Concordance, nursing
education) into ONE runnable Python script that reproduces the table in
`table1_detailed.png` using the CODE TEMPLATE below.

================================================================================
INPUT (JSON the user message will contain)
================================================================================
{
  "situations": {
    "situation 1": {
      "description": "<clinical situation description>",
      "scenarios": {
        "scenario 1": {
          "expert_key_elements": ["...", "..."],
          "coverage": {
            "score_assessment": "Low" | "Medium" | "High",
            "justification": "Thèmes abordés : ...\nThèmes manquants : ..."
          },
          "logical_reasoning": {
            "assessment": "<free text>",
            "rating": "Unsatisfactory" | "Needs Improvement" | "Satisfactory" | "Good" | "Very Good"
          },
          "communication": {
            "assessment": "<free text>",
            "rating": "Unsatisfactory" | "Needs Improvement" | "Satisfactory" | "Good" | "Very Good"
          },
          "skills_assessment": {
            "<skill name>": {
              "present_in_scenario": true | false,
              "learner_assessment": "...",
              "justification": "<free text>"
            }
          }
        },
        ...
      }
    },
    ...
  }
}

Justifications may be in French or English; output cells must be in English.

================================================================================
WHAT VARIES PER EVALUATION
================================================================================
Both the training content AND the learner's answers change from one
evaluation to the next. The visual format does NOT. Specifically, every
one of the following can differ between calls — assume nothing about them:

- Number of situations               (>= 1; the example shows 2)
- Number of scenarios per situation  (>= 1; the example shows 3 + 3)
- Total number of scenarios          (= number of data rows)
- Situation `description`            (clinical topic, wording, language)
- Situation short title              (derived 1–3 word English label)
- `expert_key_elements` per scenario (different themes per training)
- Themes covered / missed in each `coverage.justification`
- All `score_assessment` / `rating` values (any value from the rating maps)
- Skill name(s) in `skills_assessment`  (the "Competency:" shown in the
                                         subtitle; not always the same as
                                         in the example)
- Language of free-text justifications (French or English)

Treat the `data` rows currently shown in the CODE TEMPLATE as an
ILLUSTRATIVE EXAMPLE from ONE specific evaluation. For every new input you
receive, regenerate the rows from scratch based on the JSON; do not reuse
any of the example titles, themes, or ratings unless they truly appear in
the new input. The number of rows must equal the total number of scenarios
in the input — not always 6.

================================================================================
RATING MAPS (apply verbatim; never expose raw harsh terms in the table)
================================================================================
COVERAGE_MAP = {
    "Low":     "Early",
    "Medium":  "Partial",
    "High":    "Achieved",
}

REASONING_MAP = {
    "Unsatisfactory":    "Developing",
    "Needs Improvement": "Developing",
    "Satisfactory":      "Emerging",
    "Good":              "Established",
    "Very Good":         "Strong",
}

COMMUNICATION_MAP = {
    "Unsatisfactory":    "Early",
    "Needs Improvement": "Early",
    "Satisfactory":      "Developing",
    "Good":              "Developing",
    "Very Good":         "Established",
}

================================================================================
CODE TEMPLATE (this is the canonical visual format — do not change anything
outside the clearly marked EDIT regions)
================================================================================
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np

fig = plt.figure(figsize=(20, 14))
fig.patch.set_facecolor('#F8F9FA')

gs = GridSpec(1, 1, figure=fig)
ax = fig.add_subplot(gs[0, 0])
ax.axis('off')

title = fig.text(0.5, 0.97, "Learning by Concordance — Detailed Scenario Review",
                 ha='center', va='top', fontsize=16, fontweight='bold', color='#2C3E50')
# === EDIT 1: subtitle ========================================================
# Format: "Situations <range> · <N> Scenarios · Competency: <skill name>"
#   <range>      = "1", "1 & 2", "1–3", ... depending on number of situations
#   <N>          = total number of scenarios across all situations
#   <skill name> = dominant skill name from skills_assessment (typically
#                  the same across scenarios)
fig.text(0.5, 0.935, "Situations 1 & 2 · 6 Scenarios · Competency: Communication & Collaborative Leadership",
         ha='center', va='top', fontsize=10, color='#555555')
# =============================================================================

col_labels = ["Scenario", "Situation", "Coverage\nof Key Themes", "Logical\nReasoning", "Communication\nQuality",
              "Themes Addressed (Learner)", "Key Themes Not Yet Addressed"]

# === EDIT 2: data rows =======================================================
# One row per scenario, ordered situation-by-situation, scenario-by-scenario.
# Columns, in order, are:
#   0 "Sx"                    -> global scenario index ("S1", "S2", ... across all situations)
#   1 "Sit. N\n<short title>" -> N is the situation's local index;
#                                <short title> is a 1–3 word English title
#                                derived from the situation's description,
#                                broken with \n if needed
#   2 Coverage label          -> COVERAGE_MAP[coverage.score_assessment]
#   3 Logical Reasoning label -> REASONING_MAP[logical_reasoning.rating]
#   4 Communication label     -> COMMUNICATION_MAP[communication.rating]
#   5 Themes Addressed        -> short English summary extracted from the
#                                "Thèmes abordés" portion of
#                                coverage.justification (≤ 2 lines, break with \n)
#   6 Themes Not Yet Addressed-> short English summary extracted from the
#                                "Thèmes manquants" portion of
#                                coverage.justification (≤ 2 lines, break with \n)
#
# NOTE: the rows below are an ILLUSTRATIVE EXAMPLE from one specific
# evaluation (2 situations × 3 scenarios on a nutrition topic). You MUST
# replace the entire `data` list to reflect the current input — different
# situation titles, different number of rows, different themes, different
# ratings, possibly a different clinical domain entirely. The expert
# `expert_key_elements` and themes shown here will almost never match a
# new evaluation.
data = [
    ["S1", "Sit. 1\nNutritional\ndiscrepancy",
     "Partial", "Emerging", "Developing",
     "Followed nutrition sheet;\nconsidered medical reason",
     "Dysphagia risk; legal obligation;\ncollaborative alternative"],
    ["S2", "Sit. 1\nNutritional\ndiscrepancy",
     "Early", "Developing", "Early",
     "Considered patient emotion\nand immediate wishes",
     "Active prescription; clinical validation;\nteam coordination; scope of practice"],
    ["S3", "Sit. 1\nNutritional\ndiscrepancy",
     "Early", "Developing", "Early",
     "Recognized a clinical\nresponsibility issue exists",
     "Information validation; nurse collaboration;\nlate-note verification; proactive leadership"],
    ["S4", "Sit. 2\nEarly nutritional\nrisk detection",
     "Early", "Developing", "Early",
     "Avoided unnecessary\ndisturbance to patient",
     "Proactive data collection; weight assessment;\ncontribution to clinical evaluation"],
    ["S5", "Sit. 2\nEarly nutritional\nrisk detection",
     "Early", "Developing", "Early",
     "Identified reduced intake;\nwanted rapid intervention",
     "Nurse reporting; medication link analysis;\ngraduated approach before supplements"],
    ["S6", "Sit. 2\nEarly nutritional\nrisk detection",
     "Early", "Developing", "Early",
     "Identified dental prosthesis\nas a mechanical cause",
     "Immediate appetite stimulation; meal enrichment;\ntemporary food texture adaptation"],
]
# =============================================================================

col_widths = [0.04, 0.08, 0.07, 0.07, 0.08, 0.28, 0.34]
col_positions = [0.01]
for w in col_widths[:-1]:
    col_positions.append(col_positions[-1] + w)

header_y = 0.89
row_height = 0.10
header_color = '#2C3E50'
row_colors = ['#FFFFFF', '#F2F4F7']

# Draw header
for i, (label, x) in enumerate(zip(col_labels, col_positions)):
    ax.text(x + col_widths[i] * 0.5, header_y + 0.01, label,
            ha='center', va='center', fontsize=8.5, fontweight='bold', color='white',
            transform=ax.transAxes)
    rect = mpatches.FancyBboxPatch((x, header_y - 0.02), col_widths[i] - 0.003, 0.055,
                                    boxstyle="square,pad=0", linewidth=0,
                                    facecolor=header_color, transform=ax.transAxes, clip_on=False)
    ax.add_patch(rect)

# Draw rows
for row_idx, row in enumerate(data):
    y = header_y - 0.02 - (row_idx + 1) * row_height
    bg = row_colors[row_idx % 2]
    rect = mpatches.FancyBboxPatch((col_positions[0], y), sum(col_widths) - 0.003, row_height - 0.005,
                                    boxstyle="square,pad=0", linewidth=0.5,
                                    facecolor=bg, edgecolor='#DDDDDD', transform=ax.transAxes, clip_on=False)
    ax.add_patch(rect)

    for col_idx, (cell, x) in enumerate(zip(row, col_positions)):
        align = 'center' if col_idx < 5 else 'left'
        xpos = x + col_widths[col_idx] * 0.5 if col_idx < 5 else x + 0.005
        fontsize = 8 if col_idx >= 5 else 8.5
        weight = 'bold' if col_idx == 0 else 'normal'
        color = '#2C3E50'

        if col_idx in [2, 3, 4]:
            cell_bg_map = {
                "Early":       "#FEF9E7",
                "Partial":     "#EAF2FB",
                "Developing":  "#EAF2FB",
                "Emerging":    "#EAF2FB",
                "Established": "#E8F6EF",
                "Strong":      "#E8F6EF",
                "Achieved":    "#E8F6EF",
            }
            cell_bg = cell_bg_map.get(cell, bg)
            crect = mpatches.FancyBboxPatch((x + 0.002, y + 0.005), col_widths[col_idx] - 0.007, row_height - 0.018,
                                             boxstyle="round,pad=0.005", linewidth=0,
                                             facecolor=cell_bg, transform=ax.transAxes, clip_on=False)
            ax.add_patch(crect)

        ax.text(xpos, y + row_height * 0.5 - 0.002, cell,
                ha=align, va='center', fontsize=fontsize, fontweight=weight,
                color=color, transform=ax.transAxes, linespacing=1.3)

legend_y = 0.04
fig.text(0.5, legend_y,
         "Assessment levels: Early · Developing · Emerging · Partial · Established "
         "— reflect degree of alignment with expert panel responses",
         ha='center', fontsize=8, color='#777777', style='italic')

plt.tight_layout(rect=[0, 0.04, 1, 0.93])
plt.savefig("table1_detailed.png", dpi=180, bbox_inches='tight', facecolor='#F8F9FA')
print("Saved: table1_detailed.png")
```

================================================================================
WHAT YOU MAY CHANGE / WHAT YOU MUST KEEP
================================================================================
Change ONLY:
- The subtitle string inside EDIT 1 (counts + competency name).
- The contents of the `data` list inside EDIT 2 (one row per scenario,
  derived from the input JSON using the rating maps and translation rules).

Keep IDENTICAL (byte-for-byte where reasonable):
- All imports, figure size, colors, fonts, sizes, paddings, positions,
  column widths, header text, footer text, `cell_bg_map`, save path,
  dpi, and the printed confirmation line.
- The number, order, and headers of columns.
- The drawing logic (header, rows, rating-cell rounded backgrounds).

================================================================================
OUTPUT FORMAT (STRICT)
================================================================================
- Return ONLY the filled-in Python source code (no markdown fences, no prose).
- The script must run as-is and write `table1_detailed.png` to the current
  working directory.
- Deterministic: same input -> same script.
'''.strip()