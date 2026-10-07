"""WF009 Employee Task Assignment - task understanding, skill matching, workload, ranking."""
from __future__ import annotations

import re
from typing import Optional

from ..llm import LLMError
from ..models import Halt, StepOutcome, ToolError
from . import ToolContext, register_tool
from .data_tools import read_rows


def _skills(v) -> list[str]:
    if isinstance(v, list):
        return [s.strip().lower() for s in v if str(s).strip()]
    return [s.strip().lower() for s in re.split(r"[;,]", str(v or "")) if s.strip()]


def _hours(v) -> Optional[float]:
    """Parse effort like 8, '8', '8h', '8-10' (upper bound) -> float, or None."""
    nums = re.findall(r"\d+(?:\.\d+)?", str(v or ""))
    return float(nums[-1]) if nums else None


ROLE_ALIASES = {"developer": ["developer", "engineer", "dev", "programmer"], "designer": ["designer"],
                "data analyst": ["analyst", "data"], "marketing": ["marketing", "marketer", "seo"]}


def _role_matches(employee_role: str, requested: str) -> bool:
    e, r = employee_role.lower(), requested.lower()
    if e == r or e in r or r in e:
        return True
    return any(w in r for w in ROLE_ALIASES.get(e, []))


@register_tool("understand_task", "Employee/task database", "Resolve the task and its required skills")
def understand_task(ctx: ToolContext, employees_path: str, tasks_path: str, description: Optional[str] = None,
                    task_id: Optional[str] = None, required_skills=None, priority: Optional[str] = None,
                    deadline: Optional[str] = None, role: Optional[str] = None,
                    estimated_hours=None, default_hours: int = 8,
                    extra_skill_vocabulary: Optional[list] = None) -> StepOutcome:
    decisions: list[str] = []
    if description and not re.sub(r"\b(this|that|the|a|an|my|urgent|new|high|priority|critical|task|it)\b|\W", "",
                                  description.lower()):
        decisions.append(f"Description '{description}' is only a reference to a task, not a description")
        description = None
    tasks = read_rows(ctx.path(tasks_path))
    task: dict = {}
    if task_id:
        task = next((t for t in tasks if t["task_id"].upper() == task_id.upper()), {})
        if not task:
            msg = f"Task {task_id} not found in the task database. Please describe the task instead."
            return StepOutcome(None, msg, halt=Halt("needs_input", msg, ["task_description"]))
        decisions.append(f"Task loaded from database by ID {task_id}")
    elif not description:
        open_tasks = [t for t in tasks if t["status"] == "open" and not t.get("assignee")
                      and (not priority or t["priority"] == priority)]
        if len(open_tasks) == 1:
            task = open_tasks[0]
            decisions.append(f"No description given -> the only open, unassigned {priority or ''} task in the "
                             f"task database was used: {task['task_id']}")
        else:
            msg = ("Please describe the task (what needs doing, required skills, deadline). "
                   + (f"I found {len(open_tasks)} open {priority + ' ' if priority else ''}tasks, so I can't tell which one you mean: "
                      + ", ".join(f"{t['task_id']} ({t['title']})" for t in open_tasks) if open_tasks else ""))
            return StepOutcome(None, msg.strip(), halt=Halt("needs_input", msg.strip(), ["task_description"]),
                               decisions=["Task ambiguous -> asking user"])
    else:
        task = {"task_id": "NEW", "title": description[:80], "description": description}

    skills = _skills(required_skills) or _skills(task.get("required_skills"))
    if not skills:
        vocab = sorted({s for e in read_rows(ctx.path(employees_path)) for s in _skills(e["skills"])}
                       | set(_skills(extra_skill_vocabulary)))
        text = f"{task.get('title', '')} {task.get('description', '')}"
        if ctx.llm is not None and ctx.llm.available:
            try:
                res = ctx.llm.json("Extract the technical skills required for this task. Use the vocabulary terms "
                                   "where they apply; add other essential skills in lower case if needed. "
                                   "Return {\"skills\": [...], \"estimated_hours\": int|null}.",
                                   f"Vocabulary: {vocab}\nTask: {text}")
                raw = _skills(res.get("skills"))
                skills = [s for s in raw if s in vocab]
                dropped = [s for s in raw if s not in vocab]
                if dropped:
                    decisions.append(f"Skills not held by anyone in the company vocabulary ignored for matching: {dropped}")
                if res.get("estimated_hours") and not estimated_hours and not task.get("estimated_hours"):
                    estimated_hours = _hours(res["estimated_hours"])
                decisions.append(f"Required skills extracted by {ctx.llm.mode}: {skills}")
            except LLMError as exc:
                decisions.append(f"LLM skill extraction failed ({exc}) -> keyword matching")
        if not skills:
            low = text.lower()
            skills = [s for s in vocab if re.search(rf"\b{re.escape(s)}\b", low)]
            decisions.append(f"Required skills matched from skill vocabulary: {skills or 'none found'}")
    if not skills:
        decisions.append("No specific skills identified -> candidates ranked on capacity and seniority only")

    result = {
        "task_id": task.get("task_id"), "title": task.get("title"), "description": task.get("description"),
        "required_skills": skills, "priority": (priority or task.get("priority") or "normal").lower(),
        "deadline": deadline or task.get("deadline") or "not specified",
        "estimated_hours": _hours(estimated_hours) or _hours(task.get("estimated_hours")) or float(default_hours),
        "role": (role or "").title() or None,
    }
    if result["deadline"] == "not specified":
        decisions.append("Deadline not provided -> marked 'not specified' (not invented)")
    if not (estimated_hours or task.get("estimated_hours")):
        decisions.append(f"Effort not provided -> default estimate of {default_hours}h used for capacity check")
    return StepOutcome(result, f"{result['task_id']}: '{result['title']}' needs {', '.join(skills) or 'no specific skills'}; "
                               f"priority {result['priority']}, deadline {result['deadline']}", decisions=decisions)


@register_tool("compare_skills", "ranking logic", "Score each employee's skill match for the task")
def compare_skills(ctx: ToolContext, employees_path: str, task: dict) -> StepOutcome:
    emps = read_rows(ctx.path(employees_path))
    decisions = []
    if task.get("role"):
        role_emps = [e for e in emps if _role_matches(e["role"], task["role"])]
        decisions.append(f"Role filter '{task['role']}': {len(role_emps)} of {len(emps)} employees")
        emps = role_emps
    if not emps:
        raise ToolError(f"No employees with role '{task.get('role')}' in the employee database")
    req = set(task["required_skills"])
    out = []
    for e in emps:
        have = set(_skills(e["skills"]))
        matched = sorted(req & have)
        out.append({**e, "matched_skills": matched, "missing_skills": sorted(req - have),
                    "skill_match": round(len(matched) / len(req), 2) if req else 1.0})
    return StepOutcome(out, "; ".join(f"{e['name']} {e['skill_match']:.0%}" for e in out), decisions=decisions)


@register_tool("check_workload", "Employee/task database", "Compute available capacity and availability")
def check_workload(ctx: ToolContext, candidates: list, task: dict) -> StepOutcome:
    out = []
    for c in candidates:
        avail = float(c["weekly_capacity_hours"]) - float(c["current_workload_hours"])
        on_leave = str(c.get("on_leave", "no")).lower() in ("yes", "true", "1")
        out.append({**c, "available_hours": avail, "on_leave": on_leave,
                    "utilisation": f"{float(c['current_workload_hours']) / float(c['weekly_capacity_hours']):.0%}",
                    "has_capacity": (not on_leave) and avail >= task["estimated_hours"]})
    return StepOutcome(out, f"{sum(c['has_capacity'] for c in out)} of {len(out)} have ≥ {task['estimated_hours']:.0f}h free "
                            f"and are not on leave")


@register_tool("rank_candidates", "ranking logic", "Weighted ranking: skills, capacity, seniority")
def rank_candidates(ctx: ToolContext, candidates: list, task: dict, weights: dict) -> StepOutcome:
    sen = {"junior": 0.3, "mid": 0.6, "senior": 1.0}
    urgent = task["priority"] in ("urgent", "high", "critical")
    out = []
    for c in candidates:
        cap = 0.0 if c["on_leave"] else max(0.0, min(1.0, c["available_hours"] / max(task["estimated_hours"], 1)))
        w_sen = weights.get("seniority", 0) * (1.5 if urgent else 1.0)
        score = (weights["skills"] * c["skill_match"] + weights["capacity"] * cap + w_sen * sen.get(c.get("seniority"), 0.5))
        score /= (weights["skills"] + weights["capacity"] + w_sen)
        out.append({**c, "score": round(score, 3)})
    out.sort(key=lambda c: -c["score"])
    for i, c in enumerate(out, 1):
        c["rank"] = i
    return StepOutcome(out, "Ranking: " + " > ".join(f"{c['name']} ({c['score']})" for c in out[:4]),
                       decisions=[f"Score = skills×{weights['skills']} + capacity×{weights['capacity']} + seniority×"
                                  f"{weights.get('seniority', 0)}{' (×1.5 for urgent)' if urgent else ''}; "
                                  "capacity = free hours / task hours (capped at 1)"])


@register_tool("select_employee", "decision rule", "Pick the best suitable employee or escalate")
def select_employee(ctx: ToolContext, ranked: list, min_skill_match: float) -> StepOutcome:
    suitable = [c for c in ranked if c["has_capacity"] and c["skill_match"] >= min_skill_match]
    reasons = []
    for c in ranked:
        why = []
        if c["on_leave"]:
            why.append("on leave")
        elif not c["has_capacity"]:
            why.append(f"only {c['available_hours']:.0f}h free")
        if c["skill_match"] < min_skill_match:
            why.append(f"skill match {c['skill_match']:.0%} < {min_skill_match:.0%}")
        c["status"] = "✔ suitable" if not why else "✘ " + "; ".join(why)
    if not suitable:
        reasons.append(f"No employee has ≥{min_skill_match:.0%} of the required skills AND enough capacity -> ESCALATE to manager")
        return StepOutcome({"selected": None, "ranked": ranked, "escalated": True}, "No suitable employee - escalated",
                           decisions=reasons, run_status="escalated")
    best = suitable[0]
    reasons.append(f"Selected {best['name']}: skill match {best['skill_match']:.0%}, {best['available_hours']:.0f}h free, "
                   f"{best['seniority']}")
    return StepOutcome({"selected": best, "ranked": ranked, "escalated": False},
                       f"Selected {best['name']} ({best['employee_id']})", decisions=reasons)


@register_tool("assignment_summary", "reporting", "Write the assignment / escalation summary")
def assignment_summary(ctx: ToolContext, task: dict, selection: dict) -> StepOutcome:
    best = selection["selected"]
    if best is None:
        rec = "ESCALATED - no suitable employee"
        reasoning = ("No candidate meets both the skill requirement and the capacity needed. Options: re-prioritise "
                     "existing work, extend the deadline, or bring in additional help.")
    else:
        rec = f"{best['name']} ({best['employee_id']}, {best['seniority']} {best['role']})"
        alt = [c for c in selection["ranked"] if c is not best]
        reasoning = (f"Has {len(best['matched_skills'])}/{len(task['required_skills']) or 0} required skills "
                     f"({', '.join(best['matched_skills']) or 'n/a'}) and {best['available_hours']:.0f}h free this week "
                     f"(task needs {task['estimated_hours']:.0f}h).")
        if alt:
            reasoning += " Others not chosen: " + "; ".join(f"{c['name']} - {c['status'].lstrip('✘ ')}" for c in alt[:3]
                                                             if c["status"].startswith("✘")) + "."
    summary = {"recommended": rec, "reasoning": reasoning, "priority": task["priority"],
               "deadline": task["deadline"], "task_summary": f"{task['task_id']}: {task['title']}",
               "required_skills": ", ".join(task["required_skills"]) or "none specified",
               "estimated_hours": task["estimated_hours"]}
    return StepOutcome(summary, rec)
