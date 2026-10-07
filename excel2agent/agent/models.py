"""Core data structures shared by the registry, executor, graph and renderers."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Workflow definitions (Excel = business definition, YAML = execution binding)
# --------------------------------------------------------------------------- #
@dataclass
class ParamSpec:
    """A parameter the agent can extract from the user's request."""
    name: str
    type: str = "string"                 # string | integer | number | boolean | object | array
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[list] = None
    pattern: Optional[str] = None        # regex used by the offline extractor
    keywords: Optional[dict] = None      # offline extractor: {value: [trigger words]}
    llm: bool = True                     # False = never exposed to the LLM (e.g. file paths: attachments/defaults only)

    def json_schema(self) -> dict:
        schema: dict[str, Any] = {"type": self.type, "description": self.description}
        if self.enum:
            schema["enum"] = self.enum
        if self.type == "array":
            schema["items"] = {"type": "string"}
        if self.type == "object":
            schema["additionalProperties"] = True
        return schema


@dataclass
class StepBinding:
    """How one Excel step is executed: which tool, with which arguments."""
    label: str                           # the step name as written in the Excel file
    tool: str
    args: dict = field(default_factory=dict)
    output: Optional[str] = None         # context key to store the result under
    on_error: str = "fail"               # fail | continue
    retries: int = 0
    when: Optional[str] = None           # optional condition expression to run the step


@dataclass
class WorkflowSpec:
    # ---- from Excel ---------------------------------------------------------
    id: str
    name: str
    trigger: str
    inputs: str
    steps_text: list[str]
    decision_logic: str
    tools_required: str
    expected_output: str
    # ---- from YAML binding --------------------------------------------------
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    params: list[ParamSpec] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    steps: list[StepBinding] = field(default_factory=list)
    report: dict = field(default_factory=dict)   # declarative final-report spec (build_report args)

    @property
    def tool_name(self) -> str:
        """Function name used when exposing this workflow to the LLM as a tool."""
        slug = "".join(ch if ch.isalnum() else "_" for ch in self.name.lower()).strip("_")
        while "__" in slug:
            slug = slug.replace("__", "_")
        return f"{self.id}_{slug}"

    def routing_text(self) -> str:
        return " ".join([self.name, self.trigger, self.inputs, self.expected_output,
                         self.description, " ".join(self.keywords)])


# --------------------------------------------------------------------------- #
# Runtime structures
# --------------------------------------------------------------------------- #
class ToolError(Exception):
    """Raised by tools for expected/handled failures (bad file, API down, ...)."""


@dataclass
class Halt:
    """Returned (inside a StepOutcome) when a decision rule stops the workflow."""
    status: str                          # needs_input | escalated | completed_early
    message: str
    missing: list[str] = field(default_factory=list)


@dataclass
class StepOutcome:
    value: Any = None
    summary: str = ""
    halt: Optional[Halt] = None
    decisions: list[str] = field(default_factory=list)   # human-readable decisions taken
    run_status: Optional[str] = None     # e.g. "escalated" - flags the run without stopping it


@dataclass
class StepRecord:
    index: int
    label: str
    tool: str
    status: str                          # ok | skipped | error | halted
    summary: str = ""
    duration_ms: float = 0.0
    attempts: int = 1
    error: Optional[str] = None
    decisions: list[str] = field(default_factory=list)


@dataclass
class RoutingDecision:
    workflow_id: Optional[str]
    params: dict
    confidence: float
    reasoning: str
    method: str                          # llm-tool-calling | offline-lexical | pending-followup
    candidates: list = field(default_factory=list)


@dataclass
class RunResult:
    request: str
    status: str                          # completed | needs_input | escalated | failed | no_match
    routing: Optional[RoutingDecision]
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    params: dict = field(default_factory=dict)
    steps: list[StepRecord] = field(default_factory=list)
    report: Optional[dict] = None
    message: str = ""
    run_id: str = ""
    llm_mode: str = "offline"
    total_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
