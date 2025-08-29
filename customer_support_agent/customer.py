
from __future__ import annotations
import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# --- If your SDK matches these names, uncomment the next line and remove the stubs ---
from agents import Agent, Runner, function_tool, guardrail, ModelSettings

# --- Minimal stubs to make this script self-contained if your SDK isn't present ---
# Remove this section when using your real SDK
@dataclass
class ModelSettings:
    tool_choice: str = "auto"  # "auto" | "required" | "none"
    metadata: Optional[Dict[str, Any]] = None

class Agent:
    def __init__(self, name: str, instructions: str, tools: Optional[list] = None, model_settings: Optional[ModelSettings] = None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.model_settings = model_settings or ModelSettings()

class Runner:
    @staticmethod
    async def run(agent: Agent, msg_or_list: Any, *, metadata: Optional[Dict[str, Any]] = None) -> "RunResult":
        # This is a toy runner: it calls the first matching tool or returns a simple text
        text = msg_or_list if isinstance(msg_or_list, str) else str(msg_or_list)
        # Guardrail pass
        gr = _guardrail_civility(text)
        if gr.action == "block":
            return RunResult(final_output=gr.message, items=[{"type":"guardrail_block","message":gr.message}])
        normalized = gr.cleaned_text or text

        # Tool selection logic (toy):
        for tool in agent.tools:
            if hasattr(tool, "is_enabled") and tool.is_enabled and not tool.is_enabled(normalized):
                continue
            if tool.__name__ == "get_order_status" and re.search(r"\b(order|status|track)\b", normalized, re.I):
                try:
                    result = tool(order_id=_extract_order_id(normalized))
                except ToolFriendlyError as e:
                    result = {"error": True, "message": str(e)}
                return RunResult(final_output=_format_tool_response(result), items=[{"type":"tool","name":tool.__name__,"result":result}])

        # Handoff heuristic
        if _is_complex(normalized) or _is_negative(normalized):
            HANDOFF_LOG.append({"from": agent.name, "to": "HumanAgent", "reason": "complex_or_negative", "message": normalized})
            return RunResult(final_output="Transferring you to a human specialist for better assistance.", items=[{"type":"handoff","to":"HumanAgent"}])

        # FAQ-ish responses (toy):
        reply = _faq_answer(normalized)
        return RunResult(final_output=reply, items=[{"type":"message","text":reply}])

@dataclass
class RunResult:
    final_output: str
    items: List[Dict[str, Any]]

class ToolFriendlyError(Exception):
    pass

# --- END stubs ---

# ----------------------
# Global logging helpers
# ----------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger("support-bot")
TOOL_LOG: List[Dict[str, Any]] = []
HANDOFF_LOG: List[Dict[str, Any]] = []

# ----------------------
# Simulated data layer
# ----------------------
ORDER_DB = {
    "ORD-1001": {"status": "Shipped", "eta": "2025-09-02", "carrier": "DHL"},
    "ORD-1002": {"status": "Processing", "eta": "2025-09-05", "carrier": None},
    "ORD-1003": {"status": "Delivered", "eta": "2025-08-27", "carrier": "Leopard"},
}

# ----------------------
# Guardrail implementation
# ----------------------
@dataclass
class GuardrailResult:
    action: str  # "allow" | "block"
    message: Optional[str] = None
    cleaned_text: Optional[str] = None

# Example guardrail: flag profanity/insults; soft-rewrite mild negativity
BAD_WORDS = {"idiot", "stupid", "shut up", "fool", "dumb"}


def _guardrail_civility(user_text: str) -> GuardrailResult:
    text = user_text.strip()
    lowered = text.lower()
    if any(bad in lowered for bad in BAD_WORDS):
        msg = ("Let's keep things respectful so I can help you faster. "
               "Could you rephrase your question?")
        return GuardrailResult(action="block", message=msg)
    # Optionally do light cleanup (remove ALL CAPS yelling)
    cleaned = re.sub(r"([A-Z]{3,})", lambda m: m.group(1).capitalize(), text)
    return GuardrailResult(action="allow", cleaned_text=cleaned)

# If your SDK supports @guardrail decorator, you would do something like:
# @guardrail(name="civility", on_violation="return_warning")
# def civility_guardrail(text: str) -> GuardrailDecision: ...

# ----------------------
# Function tools
# ----------------------

def _extract_order_id(text: str) -> str:
    # Very simple matcher for tokens like ORD-1234 or plain 1234
    m = re.search(r"\b(ORD-\d{4}|\d{4})\b", text, re.I)
    if not m:
        raise ToolFriendlyError("Please provide a valid order ID (e.g., ORD-1002).")
    token = m.group(1).upper()
    return token if token.startswith("ORD-") else f"ORD-{token}"


def _is_order_query(text: str) -> bool:
    return bool(re.search(r"\b(order|status|track|tracking)\b", text, re.I))


def _format_tool_response(result: Dict[str, Any]) -> str:
    if result.get("error"):
        return f"Sorry, I couldn't find that order. {result.get('message','')}"
    return (
        f"Order Status: {result['status']}\n"
        f"ETA: {result['eta']}\n"
        f"Carrier: {result.get('carrier') or 'TBD'}"
    )


# Decorator emulation for is_enabled and error_function
class function_tool:
    def __init__(self, is_enabled=None, error_function=None):
        self.is_enabled = is_enabled
        self.error_function = error_function
    def __call__(self, fn):
        fn.is_enabled = self.is_enabled
        fn.error_function = self.error_function
        return fn


@function_tool(
    is_enabled=_is_order_query,
    error_function=lambda **kwargs: {"error": True, "message": "Order not found or invalid."},
)
def get_order_status(order_id: str) -> Dict[str, Any]:
    """Simulates fetching an order's status by ID."""
    LOGGER.info("Tool called: get_order_status(%s)", order_id)
    TOOL_LOG.append({"tool": "get_order_status", "args": {"order_id": order_id}})
    data = ORDER_DB.get(order_id)
    if not data:
        # Convert to a friendly tool-layer error so the agent can respond nicely
        raise ToolFriendlyError(f"Order {order_id} was not found.")
    return {"order_id": order_id, **data}


@function_tool()
def escalate_to_human(reason: str) -> Dict[str, Any]:
    LOGGER.info("Escalation requested: %s", reason)
    HANDOFF_LOG.append({"from": "BotAgent", "to": "HumanAgent", "reason": reason})
    return {"handoff": True, "to": "HumanAgent", "reason": reason}

# ----------------------
# Heuristics for handoff / sentiment / complexity
# ----------------------
NEGATIVE_WORDS = {"angry", "upset", "terrible", "worst", "not happy", "refund", "complaint"}


def _is_negative(text: str) -> bool:
    return any(w in text.lower() for w in NEGATIVE_WORDS)


def _is_complex(text: str) -> bool:
    # Toy heuristic: long questions with many question marks or multiple topics
    return len(text) > 240 or text.count("?") >= 2 or ("and" in text.lower() and "or" in text.lower())


# ----------------------
# FAQ helper
# ----------------------
FAQS = {
    "return policy": "You can return unopened items within 30 days for a full refund.",
    "shipping time": "Standard shipping takes 3–5 business days; expedited options are available.",
    "warranty": "All electronics include a 1-year limited warranty.",
}


def _faq_answer(text: str) -> str:
    t = text.lower()
    if "return" in t:
        return FAQS["return policy"]
    if "ship" in t or "delivery" in t:
        return FAQS["shipping time"]
    if "warranty" in t:
        return FAQS["warranty"]
    return (
        "I can help with basic FAQs and order tracking. "
        "Ask about returns, shipping, warranties, or say e.g. 'track order ORD-1002'."
    )

# ----------------------
# Agent definitions
# ----------------------
BOT_MODEL_SETTINGS = ModelSettings(
    tool_choice="auto",  # try "required" to force tool usage when available
    metadata={"role": "support-bot", "team": "CX", "store_id": "PK-01"},
)

HUMAN_MODEL_SETTINGS = ModelSettings(
    tool_choice="none",
    metadata={"role": "human-agent", "team": "CX-escalations"},
)

BotAgent = Agent(
    name="BotAgent",
    instructions=(
        "You are a polite customer support assistant.\n"
        "- Answer FAQs concisely.\n"
        "- Use tools for order lookups when the user mentions order/status/track.\n"
        "- If message seems negative or complex, escalate to a human.\n"
        "- Keep tone friendly and calm."
    ),
    tools=[get_order_status, escalate_to_human],
    model_settings=BOT_MODEL_SETTINGS,
)

HumanAgent = Agent(
    name="HumanAgent",
    instructions=(
        "You are a human support specialist.\n"
        "- Resolve complex issues empathetically.\n"
        "- Provide next steps, and if needed, collect contact details."
    ),
    tools=[],
    model_settings=HUMAN_MODEL_SETTINGS,
)

# ----------------------
# Demo runner
# ----------------------
async def chat_once(user_text: str, *, customer_id: str = "CUST-777") -> None:
    print(f"\nUser: {user_text}")
    result = await Runner.run(
        BotAgent,
        user_text,
        metadata={"customer_id": customer_id},  # demonstrate per-run metadata
    )
    print(f"Bot: {result.final_output}")

    # If handoff requested, run human agent
    if any(it.get("type") == "handoff" for it in result.items):
        human = await Runner.run(HumanAgent, user_text, metadata={"customer_id": customer_id})
        print(f"Human: {human.final_output}")


async def demo_script():
    # 1) Normal FAQ
    await chat_once("What's your return policy?")

    # 2) Order tracking (tool path)
    await chat_once("Can you track order ORD-1002?")

    # 3) Missing order id (tool error path)
    await chat_once("track my order please")

    # 4) Negative sentiment (guardrail & handoff)
    await chat_once("This is the worst, I want a refund now!!")

    # 5) Complex query (handoff)
    await chat_once("I placed two orders and changed address and payment, can you merge them and ship faster?")

    # Print logs
    print("\n--- TOOL LOG ---")
    for e in TOOL_LOG:
        print(e)
    print("\n--- HANDOFF LOG ---")
    for e in HANDOFF_LOG:
        print(e)


if __name__ == "__main__":
    asyncio.run(demo_script())
