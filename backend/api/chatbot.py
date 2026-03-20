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
from db.models import Appliance, Bill, Complaint, MeterReading, Meter, Outage, User
from db.session import get_db

# ── NVIDIA/OpenRouter setup ──────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


# ── Router ────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

SUPPORT_EMAIL = "support@intellismart.com"



# ── Request / Response Schemas ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    context: Optional[list[dict]] = []   # optional previous turns for escalation tracking


class ChatResponse(BaseModel):
    intent: str
    reply: str


# ── Intent Detection ──────────────────────────────────────────────────────────

INTENT_KEYWORDS: dict[str, list[str]] = {
    "pay_bill": [
        "pay bill", "pay my bill", "make payment", "pay now",
        "clear bill", "settle bill", "complete payment",
    ],
    "complaint": [
        "file complaint", "lodge complaint", "register complaint",
        "create complaint", "submit complaint",
    ],
    "appliance_on": [
        "turn on", "switch on", "start the", "enable the", "power on the",
    ],
    "appliance_off": [
        "turn off", "switch off", "stop the", "disable the", "power off the",
        "shut down the", "shutdown the",
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

    # Appliance control — check for exact action phrases with appliance names
    has_appliance = any(name in msg for name in APPLIANCE_NAMES)
    if has_appliance:
        if any(kw in msg for kw in INTENT_KEYWORDS["appliance_off"]):
            return "appliance_off"
        if any(kw in msg for kw in INTENT_KEYWORDS["appliance_on"]):
            return "appliance_on"

    # Pay bill - only exact payment action phrases
    if any(kw in msg for kw in INTENT_KEYWORDS["pay_bill"]):
        return "pay_bill"

    # Complaint - only when explicitly filing/registering
    if any(kw in msg for kw in INTENT_KEYWORDS["complaint"]):
        return "complaint"

    # Everything else goes to LLM for intelligent response
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


def handle_outage(current_user: User, db: Session) -> str:
    """Return current outage status for the user's area."""
    user_area = current_user.location

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


def call_llm(message: str, current_user, db: Session) -> str:
    """Call NVIDIA model via OpenRouter for general electricity-related queries with user context."""
    if not OPENROUTER_API_KEY:
        return (
            "I'm here to help with WattWise! You can ask me about your bill, "
            "energy usage, appliances, outages, or file a complaint. "
            "For general questions, please ensure the AI service is configured."
        )

    # Gather user context for better responses
    from sqlalchemy import desc
    from zoneinfo import ZoneInfo

    IST = ZoneInfo("Asia/Kolkata")
    today_start = (
        datetime.now(tz=IST)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )

    # Get user's bill information
    bill = (
        db.query(Bill)
        .filter(Bill.user_id == current_user.id, Bill.status == "unpaid")
        .order_by(desc(Bill.created_at))
        .first()
    )

    # Get meter and usage data
    meter = db.query(Meter).filter(Meter.user_id == current_user.id).first()

    today_readings = []
    total_consumption = 0
    if meter:
        readings = db.query(MeterReading).filter(MeterReading.meter_id == meter.id).all()
        total_consumption = round(sum(r.energy_kwh for r in readings), 2)
        today_readings = (
            db.query(MeterReading)
            .filter(MeterReading.timestamp >= today_start, MeterReading.meter_id == meter.id)
            .all()
        )

    today_kwh = round(sum(r.energy_kwh for r in today_readings), 3)

    # Get appliances information
    appliances = db.query(Appliance).filter(Appliance.user_id == current_user.id).all()
    active_appliances = [a.name for a in appliances if a.is_on]
    all_appliances = [a.name for a in appliances]

    # Get outage information
    outage = None
    if current_user.location:
        outage = (
            db.query(Outage)
            .filter(Outage.status == "ACTIVE", Outage.area == current_user.location)
            .first()
        )

    # Build context for LLM
    bill_info = f"₹{bill.amount:.2f} (due on {bill.due_date.strftime('%B %d') if bill.due_date else 'TBD'})" if bill else "No unpaid bills"
    estimated_bill = round(total_consumption * 7, 2) if not bill else bill.amount

    outage_info = "No active outages" if not outage else f"Active outage in {outage.area}: {outage.reason}"

    system_prompt = f"""You are **WattBot**, an intelligent AI assistant for the WattWise Smart Energy Platform.

Your role is to help users understand and optimize their electricity usage, reduce costs, and interact with their smart energy system.

---

# 🔒 STRICT DOMAIN RULE

You are ONLY allowed to answer queries related to:
* Electricity usage
* Energy consumption patterns
* Appliance-level energy insights
* Billing and cost breakdown
* Tariffs and optimization
* Energy saving suggestions
* Outages and complaints

If the user asks ANYTHING outside this domain, you MUST refuse politely.

❌ Out-of-Scope Examples: "Who invented electricity?", "Who is the president of USA?", "Tell me a joke", "What is AI?"

Response format for out-of-scope:
"I'm WattBot, your energy assistant ⚡
I can help you with electricity usage, bills, and saving energy.
Please ask something related to your energy usage or WattWise services."

---

# 🧠 USER CONTEXT (USE THIS DATA)

- Name: {current_user.name}
- Location: {current_user.location if current_user.location else 'Not set'}
- Current Bill: {bill_info}
- Total Consumption: {total_consumption} kWh
- Today's Consumption: {today_kwh} kWh
- Estimated Bill Amount: ₹{estimated_bill}
- Active Appliances: {', '.join(active_appliances) if active_appliances else 'None'}
- Available Appliances: {', '.join(all_appliances) if all_appliances else 'None'}
- Outage Status: {outage_info}

You MUST use this data to generate personalized answers.
DO NOT hallucinate data.
If data is missing, say: "I don't have enough data to answer that accurately yet."

---

# 🧩 RESPONSE STYLE

* Be concise but insightful
* Sound like a smart energy advisor
* Use numbers when possible
* Give actionable suggestions
* Be user-friendly, not robotic

---

# 🎯 TASK EXAMPLES

## Bill Analysis
Example: "Why is my bill increasing?"
Response: Identify high consumption, mention specific appliances, mention time-of-day usage.

## Appliance Insights
Example: "Which appliance is using the most energy?"
Response: Use actual appliance data from context.

## Savings Suggestions
Example: "How can I save more money?"
Response: Provide specific, actionable tips based on user's appliances and usage.

---

# ⚠️ SAFETY RULES

* Never generate fake numbers
* Never assume missing data
* Never answer outside domain
* Always prioritize user-specific insights over generic advice

---

**User Question:** {message}

Respond as WattBot in a helpful, conversational tone using the user context above."""

    try:
        import requests
        import json

        response = requests.post(
            url=OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "nvidia/llama-3.1-nemotron-70b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            }),
            timeout=30
        )

        if response.status_code == 200:
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
        else:
            return (
                "I'm having trouble processing your request right now. "
                "Please try again or use specific commands like 'pay bill', 'turn on AC', or 'file complaint'."
            )

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            return (
                "I'm currently experiencing high demand. "
                "However, I can still help you with specific actions like:\n"
                "• Pay your bill (say 'pay my bill')\n"
                "• Control appliances (say 'turn on AC')\n"
                "• File complaints (say 'file complaint')"
            )
        return (
            "I'm having trouble processing your request right now. "
            "Please try again or use specific commands like 'pay bill', 'turn on AC', or 'file complaint'."
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
        if intent == "pay_bill":
            reply = handle_pay_bill(current_user, db)

        elif intent == "complaint":
            reply = handle_complaint(message, current_user, db)

        elif intent == "appliance_on":
            reply = handle_appliance("on", message, current_user, db)

        elif intent == "appliance_off":
            reply = handle_appliance("off", message, current_user, db)

        elif intent == "escalate":
            reply = handle_escalation()

        else:  # general_query → LLM for everything else
            reply = call_llm(message, current_user, db)
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

