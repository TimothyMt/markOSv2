"""
Task Workflows — declarative workflow definitions for multi-step tasks.

WorkflowStep describes one step in a multi-agent workflow.
TASK_WORKFLOWS maps task name → ordered list of steps.
"""
from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """One step in a multi-agent workflow."""
    skill: str                        # operational skill name (or "haiku_direct")
    persona: str                      # persona key (e.g. "brand", "content")
    persona_name: str                 # display name (e.g. "Linh", "Nam")
    context_keys: list[str] = field(default_factory=list)  # session result keys to inject
    optional: bool = False            # if True, step failure is non-fatal


# Task 1: "Viết Content đơn" — Linh → Nam → Linh
WRITE_CONTENT_STEPS: list[WorkflowStep] = [
    WorkflowStep(
        skill="brand_direction",       # internal step: lightweight Haiku brand analysis
        persona="brand",
        persona_name="Linh",
        context_keys=[],
        optional=False,
    ),
    WorkflowStep(
        skill="post_write",            # operational skill: write the post
        persona="content",
        persona_name="Nam",
        context_keys=["brand_direction"],  # inject brand_direction from step 1
        optional=False,
    ),
    WorkflowStep(
        skill="post_voice_check",      # operational skill: brand voice check on draft
        persona="brand",
        persona_name="Linh",
        context_keys=["brand_direction", "post_write"],  # brand dir + Nam's draft
        optional=True,                 # skip if fails
    ),
]


TASK_WORKFLOWS: dict[str, list[WorkflowStep]] = {
    "write_content": WRITE_CONTENT_STEPS,
}
