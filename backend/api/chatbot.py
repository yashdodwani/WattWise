"""
api/chatbot.py — WattWise Conversational Chatbot API

POST /chatbot/query
  - Detects user intent from message keywords
  - Calls internal backend logic for billing, complaints, outages, appliances, energy usage
  - Falls back to Gemini LLM for general electricity questions
  - Escalates to support email if the issue remains unresolved after multiple attempts
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db.models import Appliance, Bill, Complaint, MeterReading, Meter, Outage
from db.session import get_db

# ── Gemini setup ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_gemini_client = None

def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None and GEMINI_API_KEY:
        try:
            import importlib
            google_genai = importlib.import_module('google.genai')
            _gemini_client = google_genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            # Gemini client not available or failed to initialize
            _gemini_client = None
    return _gemini_client


# ── Router ────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

SUPPORT_EMAIL = "support@intellismart.com"

DEFAULT_USER_AREA = "Surat"


# ── Request / Response Schemas ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    context: Optional[list[dict]] = []   # optional previous turns for escalation tracking


class ChatResponse(BaseModel):
    intent: str
    reply: str


# ── Intent Detection ──────────────────────────────────────────────────────────

INTENT_KEYWORDS: dict[str, list[str]] = {
    "billing": [
        "bill", "electricity bill", "current bill", "my bill",
        "billing", "how much do i owe", "amount due", "payment due",
    ],
    "pay_bill": [
        "pay bill", "pay my bill", "make payment", "pay now",
        "clear bill", "settle bill",
    ],
    "complaint": [
        "complaint", "report", "no power", "power outage", "voltage problem",
        "meter issue", "billing issue", "file complaint", "lodge complaint",
        "register complaint", "issue with",
    ],
    "outage": [
        "outage", "power cut", "electricity cut", "is there power",
        "power failure", "electricity outage", "cut in my area", "load shedding",
    ],
    "appliance_on": [
        "turn on", "switch on", "start", "enable", "power on",
    ],
    "appliance_off": [
        "turn off", "switch off", "stop", "disable", "power off",
        "shut down", "shutdown",
    ],
    "energy_usage": [
        "usage", "consumption", "how much electricity", "current load",
        "energy consumption", "power consumption", "current usage",
        "units used", "kwh",
    ],
    "escalate": [
        "not helpful", "still problem", "issue not solved", "complaint unresolved",
        "not resolved", "still facing", "no solution", "useless", "help me",
        "nobody helping", "not working",
    ],
}

APPLIANCE_NAMES = [
    "ac", "air conditioner", "heater", "fan", "washing machine",
    "refrigerator", "fridge", "tv", "television", "light", "geyser",
    "microwave", "oven", "computer", "laptop",
]


def detect_intent(message: str) -> str:
    """Return the best-matching intent string, or 'general_query'."""
    msg = message.lower()

    # Escalation check first (highest priority)
    if any(kw in msg for kw in INTENT_KEYWORDS["escalate"]):
        return "escalate"

    # Appliance control — check before generic "complaint" / "billing"
    has_appliance = any(name in msg for name in APPLIANCE_NAMES)
    if has_appliance:
        if any(kw in msg for kw in INTENT_KEYWORDS["appliance_off"]):
            return "appliance_off"
        if any(kw in msg for kw in INTENT_KEYWORDS["appliance_on"]):
            return "appliance_on"

    # Pay bill must precede generic billing check
    if any(kw in msg for kw in INTENT_KEYWORDS["pay_bill"]):
        return "pay_bill"

    for intent, keywords in INTENT_KEYWORDS.items():
        if intent in ("pay_bill", "appliance_on", "appliance_off", "escalate"):
            continue  # already handled above
        if any(kw in msg for kw in keywords):
            return intent

    return "general_query"


def _extract_appliance_name(message: str) -> Optional[str]:
    """Extract the first mentioned appliance name from the message."""
    msg = message.lower()
    for name in APPLIANCE_NAMES:
        if name in msg:
            return name
    return None


# ── Internal Handlers ─────────────────────────────────────────────────────────

def handle_billing(current_user, db: Session) -> str:
    """Fetch the latest unpaid bill and return a formatted string."""
    from sqlalchemy import desc

    bill = (
        db.query(Bill)
        .filter(Bill.user_id == current_user.id, Bill.status == "unpaid")
        .order_by(desc(Bill.created_at))
        .first()
    )

    if bill:
        due = bill.due_date.strftime("%B %d") if bill.due_date else "soon"
        return (
            f"Your current electricity bill is ₹{bill.amount:.2f} "
            f"(Bill ID: {bill.id}), due on {due}. "
            f"Would you like to pay it now?"
        )

    # Simulate if no DB bill exists
    meter = db.query(Meter).filter(Meter.user_id == current_user.id).first()
    if not meter:
        return "I couldn't find a meter linked to your account."

    readings = db.query(MeterReading).filter(MeterReading.meter_id == meter.id).all()
    units = round(sum(r.energy_kwh for r in readings), 2)
    amount = round(units * 7, 2)
    return (
        f"Your estimated electricity bill is ₹{amount:.2f} "
        f"for {units} units consumed. No due date set yet. "
        f"Would you like more details?"
    )


def handle_pay_bill(current_user, db: Session) -> str:
    """Pay the latest unpaid bill."""
    from sqlalchemy import desc

    bill = (
        db.query(Bill)
        .filter(Bill.user_id == current_user.id, Bill.status == "unpaid")
        .order_by(desc(Bill.created_at))
        .first()
    )

    if not bill:
        return "You have no unpaid bills at the moment. You're all clear! ✅"

    bill.status = "paid"
    db.commit()
    return (
        f"✅ Payment of ₹{bill.amount:.2f} for Bill ID {bill.id} was successful! "
        f"Your account is now up to date."
    )


def handle_complaint(message: str, current_user, db: Session) -> str:
    """Register a complaint based on the user's message."""
    # Determine complaint type from message
    msg = message.lower()
    if "voltage" in msg:
        ctype = "voltage_issue"
    elif "meter" in msg:
        ctype = "meter_issue"
    elif "billing" in msg or "bill" in msg:
        ctype = "billing_issue"
    elif "outage" in msg or "power" in msg or "electricity" in msg:
        ctype = "power_outage"
    else:
        ctype = "general_complaint"

    complaint = Complaint(
        user_id=current_user.id,
        type=ctype,
        description=message,
        status="OPEN",
        created_at=datetime.now(timezone.utc),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return (
        f"✅ Your complaint has been registered successfully.\n"
        f"Complaint ID: {complaint.id}\n"
        f"Type: {ctype.replace('_', ' ').title()}\n"
        f"Our team will resolve it shortly. "
        f"You can track it using Complaint ID {complaint.id}."
    )


def handle_outage(current_user, db: Session) -> str:
    """Return current outage status for the user's area."""
    user_area = DEFAULT_USER_AREA

    outage = (
        db.query(Outage)
        .filter(Outage.status == "ACTIVE", Outage.area == user_area)
        .first()
    )

    if not outage:
        return f"✅ No power outages reported in {user_area} right now. Power supply is normal."

    restore_str = (
        outage.expected_restore.strftime("%I:%M %p")
        if outage.expected_restore
        else "unknown"
    )
    return (
        f"⚠️ Active power outage in {outage.area}!\n"
        f"Reason: {outage.reason}\n"
        f"Expected restoration: {restore_str}. "
        f"We apologise for the inconvenience."
    )


def handle_appliance(
    action: str, message: str, current_user, db: Session
) -> str:
    """Turn an appliance on or off based on detected name."""
    appliance_name = _extract_appliance_name(message)

    if not appliance_name:
        return (
            "I couldn't identify which appliance you'd like to control. "
            "Please mention the appliance name (e.g., AC, fan, heater)."
        )

    # Fuzzy match in DB — case-insensitive contains
    appliances = (
        db.query(Appliance)
        .filter(Appliance.user_id == current_user.id)
        .all()
    )

    matched = next(
        (a for a in appliances if appliance_name in a.name.lower()),
        None,
    )

    if not matched:
        return (
            f"I couldn't find an appliance matching '{appliance_name}' in your account. "
            f"Please check the appliance list."
        )

    if action == "on":
        if matched.is_on:
            return f"{matched.name} is already ON. ✅"
        matched.is_on = True
        matched.last_started_at = datetime.now()
        db.commit()
        return f"✅ {matched.name} has been turned ON successfully."

    else:  # off
        if not matched.is_on:
            return f"{matched.name} is already OFF."
        matched.is_on = False
        matched.last_started_at = None
        db.commit()
        return f"✅ {matched.name} has been turned OFF successfully."


def handle_energy_usage(current_user, db: Session) -> str:
    """Return today's energy usage summary."""
    from sqlalchemy import desc
    from zoneinfo import ZoneInfo

    IST = ZoneInfo("Asia/Kolkata")
    today_start = (
        datetime.now(tz=IST)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )

    latest = (
        db.query(MeterReading)
        .order_by(desc(MeterReading.timestamp))
        .first()
    )

    today_readings = (
        db.query(MeterReading)
        .filter(MeterReading.timestamp >= today_start)
        .all()
    )

    today_kwh = round(sum(r.energy_kwh for r in today_readings), 3)
    current_load = round((latest.energy_kwh * 4) if latest else 0, 3)

    active_devices = (
        db.query(Appliance)
        .filter(Appliance.user_id == current_user.id, Appliance.is_on == True)
        .count()
    )

    predicted_bill = round(today_kwh * 7, 2)

    return (
        f"⚡ Energy Usage Summary:\n"
        f"• Current Load: {current_load} kW\n"
        f"• Today's Consumption: {today_kwh} kWh\n"
        f"• Predicted Bill (Today): ₹{predicted_bill}\n"
        f"• Active Devices: {active_devices}\n"
        f"Tip: Turn off unused appliances to save energy!"
    )


def handle_escalation() -> str:
    """Return escalation message to direct user to support."""
    return (
        "I'm sorry that the issue hasn't been resolved yet. 😔\n"
        f"Please contact our support team at **{SUPPORT_EMAIL}** for further assistance.\n"
        "Our team will help you immediately. You can also call our 24/7 helpline."
    )


def call_llm(message: str) -> str:
    """Call Gemini LLM for general electricity-related queries."""
    client = _get_gemini_client()

    if not client:
        return (
            "I'm here to help with WattWise! You can ask me about your bill, "
            "energy usage, appliances, outages, or file a complaint. "
            "For general questions, please ensure the AI service is configured."
        )

    system_prompt = (
        "You are WattWise AI assistant for a smart electricity platform.\n\n"
        "Help users with:\n"
        "- electricity usage\n"
        "- energy savings\n"
        "- billing questions\n"
        "- smart meter insights\n"
        "- appliance energy optimization\n\n"
        "Respond concisely and clearly.\n\n"
        f"User question: {message}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=system_prompt,
        )
        return response.text
    except Exception:
        return (
            "I'm having trouble reaching the AI service right now. "
            "Please try again later or ask me about your bill, appliances, or outages directly."
        )


# ── Main Endpoint ─────────────────────────────────────────────────────────────

@router.post("/query", response_model=ChatResponse)
def chatbot_query(
    request: ChatRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Universal conversational interface for WattWise.

    Detects intent and calls the appropriate backend handler.
    Falls back to Gemini LLM for general electricity questions.
    Escalates to support email if the user appears unsatisfied.
    """
    message = request.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    intent = detect_intent(message)

    try:
        if intent == "billing":
            reply = handle_billing(current_user, db)

        elif intent == "pay_bill":
            reply = handle_pay_bill(current_user, db)

        elif intent == "complaint":
            reply = handle_complaint(message, current_user, db)

        elif intent == "outage":
            reply = handle_outage(current_user, db)

        elif intent == "appliance_on":
            reply = handle_appliance("on", message, current_user, db)

        elif intent == "appliance_off":
            reply = handle_appliance("off", message, current_user, db)

        elif intent == "energy_usage":
            reply = handle_energy_usage(current_user, db)

        elif intent == "escalate":
            reply = handle_escalation()

        else:  # general_query → LLM fallback
            reply = call_llm(message)
            intent = "general_query"

    except HTTPException:
        raise
    except Exception as e:
        # Graceful degradation — don't expose internal errors
        reply = (
            "I encountered an issue processing your request. "
            "Please try again or contact support."
        )

    return ChatResponse(intent=intent, reply=reply)

