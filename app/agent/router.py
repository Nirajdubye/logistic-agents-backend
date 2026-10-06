from typing import Literal

from pydantic import BaseModel, Field

from app.agent.llm import llm


class Route(BaseModel):
    destination: Literal["operations", "policy", "both", "email", "report", "general"] = Field(
        description=(
            "operations: question is about ONE SPECIFIC record identified by a "
            "name, code, ID, or a named person/customer/driver (e.g., 'details of customer Maggie Castaneda', "
            "'show customer PGL1215', 'status of shipment SHP-123', 'details of invoice INV-100', "
            "'warehouse receipt WR-011', 'cargo release CR-011', 'quotation QT-50', 'driver Griffin Watts'). "
            "ONLY use 'operations' if the specific record belongs to one of these 7 supported operational entities: "
            "1. Customers (by customer code like PGL1063 or by customer name like 'Maggie Castaneda')\n"
            "2. Shipments (by shipment code like SHP-123)\n"
            "3. Warehouse Receipts (by receipt number like WR-011 / 2039)\n"
            "4. Cargo Releases (by release number like CR-011)\n"
            "5. Invoices (by invoice number like INV-100)\n"
            "6. Quotations (by quote number like QT-50)\n"
            "7. Drivers / Employees (by driver name like 'Griffin Watts')\n"
            "CRITICAL: If the question asks for full details or status of a SPECIFIC customer (by name or code), "
            "shipment, invoice, warehouse receipt, cargo release, quotation, or driver, you MUST route to 'operations'. "
            "Do NOT route to 'report' when a specific customer name/ID or supported record is requested.\n"
            "Operations tools ONLY support single-record lookups for these 7 entity types. They CANNOT list, count, "
            "or return 'all'/'latest' records, AND they DO NOT support tables/entities outside this list "
            "(such as pickup orders like PK-..., purchase shipments, warehouses, suppliers, expenses, etc.). "
            "If the message asks for a LIST, ALL records, or the LATEST/last N records, "
            "OR asks for a record of an entity type NOT supported by Operations (like pickup orders PK-..., "
            "purchase shipments, warehouses, suppliers), route to 'report' instead.\n"
            "This also covers plain fact-verification about a supported operational "
            "record with no compliance angle - e.g. 'verify this data is "
            "associated with any shipment', 'confirm this customer's status', "
            "'check if this invoice is paid' - these are factual lookups, not "
            "compliance checks, even though they use words like verify/confirm/"
            "check.\n"

            "policy: general question about how something works, refunds, "
            "fees, deadlines, storage limits, liability, conduct, or "
            "company rules — no specific record involved.\n"

            "both: question EXPLICITLY asks whether a SPECIFIC record is "
            "compliant, in breach, in violation, or against a named policy/rule/"
            "SOP/code of conduct - the message itself must reference compliance/"
            "violation/policy/rule/breach in some form. Do NOT use this route "
            "just because the word 'verify', 'check', or 'confirm' appears - "
            "'verify this data', 'can you confirm X', 'double check this' are "
            "PLAIN FACTUAL requests (does X exist, is Y true) unless they also "
            "explicitly ask about policy/compliance/violation. Plain verification "
            "of a fact (e.g. 'verify this customer has no shipments', 'confirm "
            "this invoice is paid') belongs in 'operations' or 'report' depending "
            "on whether it's a supported operational record or an aggregate/other entity - "
            "never 'both' unless compliance/policy/violation is explicitly part of the "
            "question.\n"

            "email: user explicitly wants something SENT/EMAILED/MAILED to an "
            "email address AND that content already exists or needs no further "
            "creation (e.g. 'email me the customer list', 'send that to "
            "x@example.com'). This takes priority over operations/policy/both. "
            "EXCEPTION: if the message asks to create/generate a chart, report, "
            "or analysis that does NOT YET EXIST *and* also asks to send/email "
            "it in the same message (e.g. 'create the chart of both and send "
            "it', 'make a report and email it to me'), route to 'report' instead "
            "- the artifact must be created before it can be sent, so creation "
            "takes precedence whenever both are requested together. Only route "
            "to 'email' directly when nothing needs to be generated first.\n"

            "report: question asks for an AGGREGATE, STATISTIC, COMPARISON, "
            "AVERAGE, TREND, or CHART/GRAPH across multiple records, OR "
            "asks for a LIST/ALL/LATEST-N of a record type with NO specific "
            "identifier given (e.g. 'list all cargo releases', 'what's the "
            "latest pickup order', 'how many permissions are there'), OR "
            "asks for a SPECIFIC record of a table/entity NOT supported by "
            "Operations Agent (e.g. pickup orders PK-..., purchase shipments, "
            "warehouses, suppliers, expenses, activities, etc.). "
            "Examples: 'what's the average X', 'compare last month to this "
            "month', 'show me a chart of Y', 'how many shipments were "
            "delayed last week', 'pickup order details for PK-102'. "
            "If the message asks to email a report/chart, still route here first "
            "(email comes as a natural follow-up once the report/chart exists)."
            "If a message asks to CREATE a chart/report AND send/"
            "email it in the same breath, this is the correct destination (not "
            "email) - creation always happens before sending. Once the chart/"
            "report already exists (a chart_id was already returned in this "
            "conversation) and the user just says 'send it'/'email it', THAT "
            "routes to 'email', not back here.\n"

            "general: greetings (hello, hi, good morning), small talk, "
            "thanks, goodbyes, questions about what the assistant can do, "
            "or anything with no operational or policy content. This is "
            "the default when the message doesn't clearly need a tool. "
            "CRITICAL: Do NOT route to 'general' if the user message is a follow-up, "
            "clarification, complaint, or question asking about operational data, records, "
            "or prior answers in this conversation (e.g. 'why did you say X', 'then why did you mention Y', "
            "'explain why', 'where is that detail', 'verify that'). "
            "Questions about prior operational statements or records MUST route to 'operations' or 'report', NEVER 'general'."
        )
    )


router_llm = llm.with_structured_output(Route)


def _format_recent_history(recent_history: list, max_turns: int = 3) -> str:
    """Formats the last few turns as plain text for the router prompt.
    Only the last `max_turns` user/assistant pairs are included - enough to
    resolve a follow-up reference like 'those months' or 'that invoice'
    without needing (or paying for) the entire conversation."""
    if not recent_history:
        return "(no prior messages)"

    trimmed = recent_history[-(max_turns * 2):]
    lines = []
    for msg in trimmed:
        role = msg.get("role", "unknown") if isinstance(msg, dict) else getattr(msg, "type", "unknown")
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def route_query(query: str, recent_history: list | None = None) -> str:
    context_block = _format_recent_history(recent_history or [])
    result = router_llm.invoke(
        "Classify the LATEST message below for routing, using the recent "
        "conversation as context - especially for follow-up messages that "
        "reference something from a prior turn (e.g. 'what are those "
        "months', 'email that to me', 'compare it to last week') rather "
        "than standing on their own.\n\n"
        f"Recent conversation:\n{context_block}\n\n"
        f"Latest message to classify: {query}"
    )
    print(f"[ROUTER] '{query}' -> {result.destination}")
    return result.destination