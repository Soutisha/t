import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.db.session import get_db
from app.models.models import User
from app.models.agents import AgentRun
from app.schemas.agents import AgentRunRequest, AgentRunFeedback
from app.services.agents import run_agent_workflow

router = APIRouter()

@router.post("/agents/run", status_code=201)
def run_agents(payload: AgentRunRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    message = payload.message.strip()
    if len(message) < 3:
        raise HTTPException(status_code=422, detail="Please provide a more specific request.")
    result = run_agent_workflow(message, user.id, db)
    run = AgentRun(user_id=user.id, request_text=message, intent=result["intent"],
        status="completed", response_text=result["response"],
        trace_json=json.dumps(result["trace"], separators=(",", ":")),
        requires_human_approval=result["requires_human_approval"])
    db.add(run)
    db.commit()
    return {"data": {"run_id": run.id, "intent": run.intent, "status": run.status,
        "engine": result["engine"], "response": run.response_text,
        "agent_trace": result["trace"],
        "requires_human_approval": run.requires_human_approval,
        "side_effects_performed": False,
        "safety_note": "This release runs read-only agents. It does not reserve tools, issue rewards, approve fitments, change profiles or send messages."}}

@router.get("/agents/runs/{run_id}")
def get_agent_run(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if not run or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent run not found.")
    return {"data": {"run_id": run.id, "intent": run.intent, "status": run.status,
        "request": run.request_text, "response": run.response_text,
        "agent_trace": json.loads(run.trace_json),
        "requires_human_approval": run.requires_human_approval,
        "created_at": run.created_at}}

@router.post("/agents/runs/{run_id}/feedback")
def feedback_agent_run(run_id: str, payload: AgentRunFeedback,
                       user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if not run or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent run not found.")
    # Feedback is kept as a separate audit event in the trace.
    trace = json.loads(run.trace_json)
    trace.append({"agent": "user_feedback", "outcome": payload.feedback,
                  "comment": payload.comment})
    run.trace_json = json.dumps(trace, separators=(",", ":"))
    db.commit()
    return {"data": {"run_id": run.id, "feedback": payload.feedback}}
