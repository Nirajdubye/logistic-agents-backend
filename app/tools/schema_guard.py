"""
Three-layer defense against the assistant ever disclosing database schema
(table names, column names, table counts, structure) to the user - no
matter how the question is phrased, and no matter which agent (report,
operations, general, policy, or any future agent) ends up handling it.

WHY THREE LAYERS, NOT ONE:
Layers 1 and 2 try to catch a bad REQUEST before it reaches an LLM with
tool access. Both are intent-based, and intent-based checks can always be
bypassed by a phrasing the layer didn't anticipate.

Layer 3 does not try to guess intent at all. It checks the literal
CONTENT of the outgoing response against the real schema. This is the
layer that actually can't be phrased around - but it must be careful not
to flag a LEGITIMATE record answer just because that record's fields
happen to share names with real columns (e.g. "Customer Code: PGL8508,
Full Name: Kristen Klein" is normal business data, not a schema leak,
even though "customer_code" and "full_name" are real column names).

To avoid that false positive, layer 3 uses three signals, checked in
order:
  1. Explicit schema/structure LANGUAGE in the output itself (e.g. the
     text literally says "column names", "schema of", "table
     structure") - this alone is enough to flag, regardless of anything
     else, since normal record answers never talk about themselves this way.
  2. Real DATA VALUES present (an email address, a long digit run like a
     phone number) - if present and (1) didn't already fire, this is
     treated as a legitimate record answer and is NOT flagged, even if
     several column-name-shaped labels appear alongside that data.
  3. Only if neither (1) nor (2) applies: a real TABLE name mentioned
     together with real COLUMN names, or a large bare bulk-list of
     column names with no framing data at all - these patterns don't
     occur in normal single-record answers.

WIRING POINTS (in your orchestrator):
    1. Before routing a query to any agent:
         guard_response = pre_route_schema_guard(query, llm=llm)
         if guard_response is not None:
             return guard_response   # short-circuit - no LLM/tool call at all

    2. After ANY agent (report/operations/general/policy) produces its
       final answer, before it is returned to the user:
         final_content = post_response_schema_guard(final_content)
"""

import re
from functools import lru_cache

# ---------------------------------------------------------------------
# Shared canned refusal - identical wording everywhere on purpose, so
# behavior can't drift session to session or agent to agent.
# ---------------------------------------------------------------------
SCHEMA_REFUSAL_MESSAGE = (
    "I'm not able to share details about the database's internal "
    "structure or schema. I can help you look up specific business "
    "records instead - shipments, invoices, customers, cargo releases, "
    "and similar - or run an analysis on that data. What would you "
    "like to know?"
)


# =======================================================================
# LAYER 1 - regex pre-filter
# =======================================================================
_SCHEMA_META_PATTERNS = [
    r"\bhow many tables?\b",
    r"\btable names?\b",
    r"\bcolumn names?\b",
    r"\bfirst \d+ (tables?|names?|columns?)\b",
    r"\bschema (of|for)\b",
    r"\bcolumns? (does|of|in|for)\b",
    r"\bdatabase (structure|architecture|design)\b",
    r"\bwhen (was|is) .*(table|column).* (created|made|added)\b",
    r"\bdoes (table|column) .* exist\b",
    r"\btable structure\b",
    r"\bdata (model|type)s? (of|for) .* table\b",
    r"\bcreate table\b",
    r"\bddl\b",
    r"\berd\b",
]
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _SCHEMA_META_PATTERNS]


def regex_flags_schema_question(query: str) -> bool:
    """Layer 1: fast keyword/pattern check on the incoming query."""
    return any(p.search(query) for p in _COMPILED_PATTERNS)


# =======================================================================
# LAYER 2 - semantic classifier gate
# =======================================================================
_CLASSIFIER_PROMPT = """Classify the following user message as either:

SCHEMA_INTENT - the user is trying to learn about the database's
internal structure: table names, column names, data types, constraints,
table counts, ERDs, DDL/CREATE TABLE statements, ORM/Pydantic models
mirroring a table, or similar - even if phrased indirectly or
disguised as a coding/documentation request.

BUSINESS_INTENT - the user is asking about actual business data or
records (a specific shipment, invoice, customer, statistics/counts
about business entities, etc.) - not about how the database itself is
built.

Respond with exactly one word: SCHEMA_INTENT or BUSINESS_INTENT.

Message: {query}"""


def llm_flags_schema_question(query: str, llm) -> bool:
    """Layer 2: one cheap classification call against your app's LLM."""
    try:
        result = llm.invoke(_CLASSIFIER_PROMPT.format(query=query))
        text = getattr(result, "content", str(result)).strip().upper()
        return "SCHEMA_INTENT" in text
    except Exception:
        # Fail OPEN on classifier errors - layer 3 still protects the output.
        return False


def pre_route_schema_guard(query: str, llm=None) -> str | None:
    """Call BEFORE routing. Returns the canned refusal if flagged, else None."""
    if regex_flags_schema_question(query):
        return SCHEMA_REFUSAL_MESSAGE
    if llm is not None and llm_flags_schema_question(query, llm):
        return SCHEMA_REFUSAL_MESSAGE
    return None


# =======================================================================
# LAYER 3 - output-side schema-leak scanner (the real backstop)
# =======================================================================

# Generic words that double as column/table names and appear naturally
# in normal business answers - never counted toward a leak on their own.
_GENERIC_TERMS_TO_IGNORE = {
    "id", "email", "status", "description", "name", "date", "type",
    "phone_number", "country", "amount", "notes", "created_at",
    "updated_at", "subject",
}

# Patterns indicating the response contains REAL DATA VALUES (an actual
# retrieved record), not just field labels - e.g. an email address or a
# phone-number-length digit run. Presence of these means "this is a
# record answer", which suppresses the weaker column-name-only signal.
_REAL_DATA_VALUE_PATTERNS = [
    re.compile(r"[\w.\-]+@[\w.\-]+\.\w+"),  # email address
    re.compile(r"\b\d{7,}\b"),               # phone-number-like digit run
]


def _looks_like_real_record_data(text: str) -> bool:
    return any(p.search(text) for p in _REAL_DATA_VALUE_PATTERNS)


@lru_cache(maxsize=1)
def _load_real_schema_terms() -> dict:
    """Loads and caches actual table/column names once per process."""
    from app.tools.db_readonly_tool import get_database_schema

    schema = get_database_schema()
    tables = {t.lower() for t in schema.keys()}
    columns = {
        col["column"].lower()
        for cols in schema.values()
        for col in cols
    }
    distinctive_columns = columns - _GENERIC_TERMS_TO_IGNORE
    return {"tables": tables, "columns": columns, "distinctive": distinctive_columns}


def response_leaks_schema(response_text: str, min_bulk_hits: int = 4) -> bool:
    """Layer 3: flags a response as a schema leak using three signals,
    checked in order - see module docstring for the reasoning behind
    each one.
    """
    # Signal 1: explicit schema/structure language in the output itself.
    # This alone is decisive, regardless of anything else in the text.
    if any(p.search(response_text) for p in _COMPILED_PATTERNS):
        return True

    # Signal 2: real data values present (email, phone-like digits) ->
    # this is a legitimate record answer, not a schema disclosure, even
    # if it uses column-name-shaped field labels. Suppress the weaker
    # column-only signal below.
    if _looks_like_real_record_data(response_text):
        return False

    terms = _load_real_schema_terms()
    lowered = response_text.lower()

    table_hits = [
        t for t in terms["tables"]
        if re.search(rf"\b{re.escape(t)}\b", lowered)
    ]
    column_hits = [
        c for c in terms["distinctive"]
        if re.search(rf"\b{re.escape(c)}\b", lowered)
    ]

    # Signal 3a: a real table name mentioned together with real column
    # names - normal record answers don't name the table they came from.
    if table_hits and column_hits:
        return True

    # Signal 3b: a large bare bulk-list of column names with no framing
    # data at all (no email/phone found above, no table name mentioned).
    if len(column_hits) >= min_bulk_hits:
        return True

    return False


def post_response_schema_guard(response_text: str, min_bulk_hits: int = 4) -> str:
    """Call AFTER any agent produces its final answer, before returning
    it to the user."""
    try:
        if response_leaks_schema(response_text, min_bulk_hits=min_bulk_hits):
            return SCHEMA_REFUSAL_MESSAGE
    except Exception:
        # Fail CLOSED - if we can't verify against real schema, err
        # toward the safer canned message rather than risk a real leak.
        return SCHEMA_REFUSAL_MESSAGE
    return response_text


if __name__ == "__main__":
    print(regex_flags_schema_question("how many tables exist in db"))       # True
    print(regex_flags_schema_question("give me shipment SHP-123 status"))   # False
    print(response_leaks_schema(
        "The customers table has customer_code, full_name, company_name"
    ))  # True (table + column combo)
    print(response_leaks_schema(
        "Dieter Cunningham has 7 warehouse receipts, all pending."
    ))  # False
    print(response_leaks_schema(
        "Customer Code: PGL8508, Company Name: Maldonado and Mcgowan Traders, "
        "Full Name: Kristen Klein, Email: hylopifap@mailinator.com, "
        "Phone Number: 15031557659"
    ))  # False - real data present, not a leak