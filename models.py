"""
Pydantic models for structured outputs
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ============= Pydantic Models for Structured Output =============

class CoverageAssessment(BaseModel):
    """Coverage assessment of learner's response"""
    score_assessment: Literal["High", "Medium", "Low"]
    justification: str = Field(description="Two-line justification")


class LogicalReasoningAssessment(BaseModel):
    """Logical reasoning assessment"""
    assessment: str = Field(description="One line justification")
    rating: Literal["Satisfactory", "Unsatisfactory"]


class CommunicationAssessment(BaseModel):
    """Communication assessment"""
    assessment: str = Field(description="Assessment of clarity, completeness, and professional language")
    rating: Literal["Excellent", "Good", "Needs Improvement"]


class SkillAssessment(BaseModel):
    """Individual skill assessment for a learning objective"""
    present_in_scenario: bool
    learner_assessment: Optional[Literal["Satisfactory", "Unsatisfactory"]] = None
    justification: Optional[str] = Field(None, description="One line justification")


class ScenarioEvaluation(BaseModel):
    """Evaluation for a single scenario"""
    expert_key_elements: List[str]
    coverage: CoverageAssessment
    logical_reasoning: LogicalReasoningAssessment
    communication: CommunicationAssessment
    skills_assessment: Dict[str, SkillAssessment]


class SituationEvaluation(BaseModel):
    """Evaluation for a situation containing multiple scenarios"""
    description: str = Field(description="One line description of the situation")
    scenarios: Dict[str, ScenarioEvaluation]


class TrainingEvaluation(BaseModel):
    """Complete evaluation for a training module"""
    situations: Dict[str, SituationEvaluation]


# ============= Learning Gaps (structured output) =============

class LearningGap(BaseModel):
    """A single learning gap tied to one learning objective."""
    learning_objective: str = Field(
        description="The learning objective (verbatim) this gap relates to"
    )
    gap_summary: str = Field(
        description="One-sentence summary of where the learner diverged from the experts"
    )
    justification: str = Field(
        description="Evidence-based justification citing the relevant scenarios/expert reasoning"
    )
    related_scenarios: List[str] = Field(
        default_factory=list,
        description="Identifiers of the scenarios where this gap was observed (e.g. 'situation 1 / scenario 2')"
    )


class LearningGapsResult(BaseModel):
    """Structured list of the learner's learning gaps."""
    gaps: List[LearningGap]


# ============= Generated Scenarios (structured output) =============

class NewScenario(BaseModel):
    """A newly generated Learning-by-Concordance scenario targeting the learner's gaps."""
    chain_of_thought: str = Field(
        description="Internal reasoning: which learning gap this scenario targets and how"
    )
    hypothesis: str = Field(
        description="The action/diagnostic hypothesis — the 'Si vous pensiez à ...' part"
    )
    new_information: str = Field(
        description="The neutral, objective new information — the 'Et qu'alors ...' part. "
                    "MUST state only a fact/event with no interpretation of its consequence."
    )
    targeted_learning_gaps: List[str] = Field(
        default_factory=list,
        description="The learning objective(s)/gap(s) this scenario is designed to address"
    )


class SituationScenarios(BaseModel):
    """The set of new scenarios generated for a single situation."""
    scenarios: List[NewScenario] = Field(
        description="The newly generated scenarios for this situation"
    )