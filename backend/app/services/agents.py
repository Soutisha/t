import json
import re
from typing import TypedDict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.models import Mechanic
from app.models.advocacy import AdvocacyProduct, FitmentRecord
from app.models.toolbank import RewardLedgerEntry, ToolProduct, ToolInventory
from app.models.copilot import KnowledgeDocument, KnowledgeChunk
from app.services.copilot import retrieve_chunks, extractive_answer

class AgentState(TypedDict, total=False):
    message: str
    user_id: str
    db: Any
    intent: str
    response: str
    trace: list[dict]
    requires_human_approval: bool

def classify_intent(message: str) -> str:
    text = message.lower()
    if re.search(r"\b(reserve|redeem|approve|issue|send|update|delete|submit|create|dispatch|award)\b", text):
        return "action_planning"
    if any(k in text for k in ("fitment", "compatible", "compatibility", "vehicle", "bike model", "car model")):
        return "fitment"
    if any(k in text for k in ("reward", "points", "balance", "redeem")):
        return "rewards"
    if any(k in text for k in ("tool bank", "tool request", "tools available", "tool catalogue")):
        return "toolbank"
    if any(k in text for k in ("product", "tyre", "tire", "sku", "specification", "pressure", "warranty", "manual", "how do")):
        return "knowledge"
    if any(k in text for k in ("mechanic", "passport", "certificate", "skill")):
        return "mechanic_support"
    return "general"

def _trace(state: AgentState, agent: str, outcome: str, count: int = 0):
    state.setdefault("trace", []).append({"agent": agent, "outcome": outcome, "records_consulted": count})

def route_node(state: AgentState) -> AgentState:
    state["intent"] = classify_intent(state["message"])
    _trace(state, "supervisor_router", f"Routed to {state['intent']}")
    return state

def knowledge_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    approved = select(KnowledgeDocument.id).where(KnowledgeDocument.status == "approved")
    chunks = db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(approved))).all()
    matches = retrieve_chunks(state["message"], chunks)
    matches = [m for m in matches if m["score"] >= 0.12]
    contexts = []
    for i, match in enumerate(matches[:4], 1):
        chunk = match["chunk"]
        doc = db.get(KnowledgeDocument, chunk.document_id)
        if doc and doc.status == "approved":
            contexts.append({"citation_id": f"S{i}", "title": doc.title,
                "page_number": chunk.page_number, "content": chunk.content})
    if contexts:
        state["response"] = extractive_answer(state["message"], contexts)
        state["response"] += "\n\nSources: " + "; ".join(
            f"[{x['citation_id']}] {x['title']} (page {x['page_number']})" for x in contexts)
    else:
        state["response"] = "I could not find enough information in approved Eurogrip documents. I will not guess specifications, compatibility, warranty or safety details. Please consult an authorised Eurogrip representative."
    _trace(state, "knowledge_agent", "Approved-document retrieval completed" if contexts else "No approved evidence; abstained", len(contexts))
    return state

def fitment_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    # Never infer fitment from text similarity; report only existing verified records.
    terms = [t for t in re.findall(r"[\w-]+", state["message"].lower()) if len(t) > 2]
    rows = db.scalars(select(FitmentRecord).where(FitmentRecord.verification_status == "verified").limit(100)).all()
    matches = []
    for row in rows:
        product = db.get(AdvocacyProduct, row.product_id)
        haystack = f"{row.vehicle_reference} {product.product_name if product else ''} {product.sku if product else ''}".lower()
        if terms and sum(1 for t in terms if t in haystack) >= min(2, len(terms)):
            matches.append((row, product))
    if matches:
        state["response"] = "Existing verified fitment records matching the request:\n" + "\n".join(
            f"- {p.product_name} ({p.sku}) for vehicle reference '{r.vehicle_reference}' — record {r.id}"
            for r,p in matches[:5] if p)
        state["response"] += "\n\nThis is a lookup of historical verified records, not a new fitment approval. Confirm the exact vehicle variant and current manufacturer guidance before installation."
    else:
        state["response"] = "No matching verified fitment record was found. I cannot determine compatibility from the available data. Please obtain confirmation from an authorised Eurogrip fitment source."
    _trace(state, "fitment_agent", "Verified fitment lookup only; no compatibility inference", len(matches))
    return state

def rewards_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    mechanic = db.scalar(select(Mechanic).where(Mechanic.user_id == state["user_id"]))
    if not mechanic:
        state["response"] = "No mechanic profile is linked to this account. Complete mechanic onboarding to view mechanic rewards."
        _trace(state, "rewards_agent", "Mechanic profile not found")
        return state
    credits = db.scalar(select(func.coalesce(func.sum(RewardLedgerEntry.points), 0)).where(
        RewardLedgerEntry.mechanic_id == mechanic.id,
        RewardLedgerEntry.entry_type == "credit")) or 0
    debits = db.scalar(select(func.coalesce(func.sum(RewardLedgerEntry.points), 0)).where(
        RewardLedgerEntry.mechanic_id == mechanic.id,
        RewardLedgerEntry.entry_type.in_(("debit", "reversal")))) or 0
    state["response"] = f"Your recorded reward balance is {int(credits)-int(debits)} points (credits {int(credits)}, debits/reversals {int(debits)}). This is a read-only balance lookup."
    _trace(state, "rewards_agent", "Own reward ledger queried")
    return state

def toolbank_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    rows = db.scalars(select(ToolProduct).where(ToolProduct.active.is_(True)).order_by(ToolProduct.name).limit(20)).all()
    if not rows:
        state["response"] = "No active tools are currently listed in the Tool Bank."
    else:
        items = []
        for product in rows:
            inventory = db.scalar(select(ToolInventory).where(ToolInventory.product_id == product.id))
            available = inventory.available_quantity if inventory else 0
            items.append(f"- {product.name} ({product.sku}) — {available} available; {product.points_cost} points")
        state["response"] = "Tool Bank catalogue snapshot:\n" + "\n".join(items) + "\n\nAvailability is based on the current recorded inventory; no reservation has been made."
    _trace(state, "toolbank_agent", "Active tool catalogue and inventory queried", len(rows))
    return state

def mechanic_support_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    mechanic = db.scalar(select(Mechanic).where(Mechanic.user_id == state["user_id"]))
    if mechanic:
        state["response"] = (f"Mechanic profile found: {mechanic.mechanic_code}. "
            f"Verification status: {mechanic.verification_status.value}. "
            f"Experience recorded: {mechanic.experience_years} years. "
            "For certification, skill verification or profile changes, use the Mechanic Passport workflow.")
        _trace(state, "mechanic_support_agent", "Own mechanic profile queried", 1)
    else:
        state["response"] = "No mechanic profile is linked to this account. Use the mechanic onboarding workflow first."
        _trace(state, "mechanic_support_agent", "Mechanic profile not found")
    return state

def action_planning_agent(state: AgentState) -> AgentState:
    state["requires_human_approval"] = True
    state["response"] = (
        "This request appears to require a change to system state. I have not executed it. "
        "A separate authorised workflow must validate the request, show the exact proposed change, "
        "and obtain explicit human approval before execution. No reward, reservation, fitment approval, "
        "profile update, dispatch or message has been created."
    )
    _trace(state, "action_planner", "Mutation detected; execution blocked pending a separate approval workflow")
    return state

def general_agent(state: AgentState) -> AgentState:
    state["response"] = ("I can help with approved Eurogrip knowledge, existing verified fitment records, "
        "your own reward balance, Tool Bank catalogue and your Mechanic Passport profile. "
        "Please ask a specific question in one of those areas.")
    _trace(state, "general_assistant", "Clarification offered")
    return state

def run_agent_workflow(message: str, user_id: str, db: Session) -> dict:
    initial: AgentState = {"message": message, "user_id": user_id, "db": db,
                           "trace": [], "requires_human_approval": False}
    try:
        from langgraph.graph import StateGraph, END
        graph = StateGraph(AgentState)
        graph.add_node("router", route_node)
        graph.add_node("knowledge", knowledge_agent)
        graph.add_node("fitment", fitment_agent)
        graph.add_node("rewards", rewards_agent)
        graph.add_node("toolbank", toolbank_agent)
        graph.add_node("mechanic_support", mechanic_support_agent)
        graph.add_node("general", general_agent)
        graph.add_node("action_planning", action_planning_agent)
        graph.set_entry_point("router")
        graph.add_conditional_edges("router", lambda s: s["intent"], {
            "knowledge": "knowledge", "fitment": "fitment", "rewards": "rewards",
            "toolbank": "toolbank", "mechanic_support": "mechanic_support",
            "action_planning": "action_planning", "general": "general"})
        for node in ("knowledge","fitment","rewards","toolbank","mechanic_support","action_planning","general"):
            graph.add_edge(node, END)
        result = graph.compile().invoke(initial)
        engine = "langgraph"
    except ImportError:
        # Local fallback preserves the same deterministic node graph while LangGraph is not installed.
        result = route_node(initial)
        nodes = {"knowledge":knowledge_agent, "fitment":fitment_agent, "rewards":rewards_agent,
                 "toolbank":toolbank_agent, "mechanic_support":mechanic_support_agent,
                 "action_planning":action_planning_agent, "general":general_agent}
        result = nodes[result["intent"]](result)
        engine = "deterministic_fallback"
    return {"intent": result["intent"], "response": result["response"],
            "trace": result["trace"], "engine": engine,
            "requires_human_approval": result.get("requires_human_approval", False)}
