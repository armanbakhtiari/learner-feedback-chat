"""
Pydantic models for structured outputs
"""

from typing import Dict, Literal, Optional
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