"""
Gives the report agent the ability to run SQL it writes itself, based on
natural language - while making it structurally impossible (not just
prompt-discouraged) to run anything that writes data.

TWO INDEPENDENT LAYERS OF PROTECTION, so a prompt-injection attempt or a
model mistake can't slip through just one:

1. APP-LEVEL: validate_readonly_sql() rejects the query text itself if it
   contains any write/DDL keyword, multiple statements, or doesn't start
   with SELECT/WITH. This runs BEFORE the query ever reaches Postgres.

2. DATABASE-LEVEL: `SET TRANSACTION READ ONLY` is issued before running
   the query. Even if a query somehow got past layer 1 (e.g. a write
   hidden inside a function call our keyword list didn't catch), Postgres
   itself will refuse to execute any write statement in a read-only
   transaction and raise an error instead of executing it.

RECOMMENDED THIRD LAYER (not yet wired in, needs your DB admin access):
create a dedicated Postgres role that only has SELECT grants at all,
and point this tool at that role specifically via a separate connection
string, instead of reusing the same read-write app user:

    CREATE ROLE report_agent_readonly WITH LOGIN PASSWORD '...';
    GRANT CONNECT ON DATABASE your_db TO report_agent_readonly;
    GRANT USAGE ON SCHEMA public TO report_agent_readonly;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO report_agent_readonly;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON TABLES TO report_agent_readonly;

This is the most bulletproof layer since it holds even if there's a bug
in our own Python validation code - the database user physically cannot
write, no matter what SQL text reaches it. Worth doing before production
use; layers 1+2 below are solid but are still application-level logic.
"""

import re
from sqlalchemy import text
from app.database.connection import SessionLocal

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate",
    "grant", "revoke", "create", "replace", "merge", "call",
    "execute", "copy", "vacuum", "reindex", "cluster", "lock",
    "commit", "rollback", "savepoint", "set",
]

MAX_ROWS_DEFAULT = 200


def validate_readonly_sql(sql: str) -> str | None:
    """Returns an error message if the SQL is unsafe, or None if it's OK."""
    stripped = sql.strip().rstrip(";")

    if ";" in stripped:
        return "Multiple SQL statements are not allowed - submit exactly one SELECT statement."

    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return "Only SELECT (or WITH ... SELECT) statements are allowed."

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", lowered):
            return (
                f"Query rejected: contains forbidden keyword '{kw}'. "
                "Only read-only SELECT queries are permitted."
            )

    return None


def get_database_schema() -> dict:
    """
    Returns real table/column names and types from the actual database, so
    the agent can write accurate SQL grounded in what really exists,
    instead of guessing column names and getting them wrong.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """))
        rows = result.fetchall()
    finally:
        db.close()

    schema: dict = {}
    for table_name, column_name, data_type in rows:
        schema.setdefault(table_name, []).append({"column": column_name, "type": data_type})
    return schema


def run_readonly_query(sql: str, max_rows: int = MAX_ROWS_DEFAULT) -> dict:
    """
    Executes a SELECT query and returns rows as a list of dicts.
    Always returns a dict - never raises - so a bad/unsafe query reports
    cleanly back to the agent instead of crashing the chat loop.
    """
    error = validate_readonly_sql(sql)
    if error:
        return {"status": "error", "message": error}

    # Auto-apply a row cap if the query doesn't already have one, so a
    # broad "show me everything" query can't dump an entire large table
    # into the conversation.
    lowered = sql.lower()
    query_to_run = sql if "limit" in lowered else f"{sql.rstrip(';')} LIMIT {max_rows}"

    db = SessionLocal()
    try:
        # Layer 2: tell Postgres itself this transaction may only read,
        # independent of whether our own keyword check above was fooled.
        db.execute(text("SET TRANSACTION READ ONLY"))
        result = db.execute(text(query_to_run))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"status": "success", "row_count": len(rows), "columns": columns, "rows": rows}
    except Exception as e:
        return {"status": "error", "message": f"Query failed: {e}"}
    finally:
        db.rollback()  # read-only transaction - nothing to commit, rollback is always safe
        db.close()


if __name__ == "__main__":
    print(get_database_schema())