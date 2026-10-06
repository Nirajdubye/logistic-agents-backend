from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from app.tools.smtp_email_tool import send_email_smtp
from app.tools.chart_tool import get_chart_bytes, get_chart_title, get_chart_html


class SendEmailInput(BaseModel):
    recipient_email: str = Field(description="The exact recipient email address, already confirmed by the user.")
    subject: str = Field(description="Final email subject line, already shown to and confirmed by the user.")
    body: str = Field(
        description=(
            "Plain-text version of the email, ALWAYS required even when body_html is "
            "also provided. This is the fallback shown by clients/spam filters that "
            "don't render HTML - it should convey the same information as body_html "
            "in readable plain text (e.g. a simple text table, not raw HTML tags). If "
            "chart_ids are included, describe each chart's findings in words here too, "
            "since the images themselves won't show in a plain-text fallback."
        )
    )
    body_html: Optional[str] = Field(
        default=None,
        description=(
            "Optional HTML version of the email body, used only when the user asked "
            "for formatted content (e.g. a table). Use simple, safe HTML only: "
            "<table>/<tr>/<td>, <b>, <i>, <ul>/<li>, <p>, <br>. Never include "
            "<script>, <iframe>, external stylesheets, or externally-loaded images. "
            "Escape any special characters (&, <, >) that appear inside data values "
            "so the markup doesn't break. Do NOT include <img> tags for charts "
            "yourself - pass chart_ids instead and they will be embedded "
            "automatically in the correct place."
        ),
    )
    chart_ids: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional list of chart_id values returned by earlier create_chart "
            "calls. If the user wants MULTIPLE charts sent, pass ALL of their "
            "chart_ids together in this ONE list on a SINGLE call to this tool - "
            "never call send_email more than once to deliver multiple charts. "
            "Each chart image is looked up and embedded into the email "
            "automatically, in the order given - do not try to paste chart image "
            "data into body/body_html yourself, just pass the chart_ids."
        ),
    )


def _send_email(
    recipient_email: str,
    subject: str,
    body: str,
    body_html: Optional[str] = None,
    chart_ids: Optional[List[str]] = None,
):
    inline_images = []
    attached_chart_ids = []
    missing_chart_ids = []
    chart_html_blocks = []

    for chart_id in (chart_ids or []):
        chart_bytes = get_chart_bytes(chart_id)
        chart_title = get_chart_title(chart_id) or "Chart"

        if chart_bytes is None:
            missing_chart_ids.append(chart_id)
            continue

        chart_html_blocks.append(
            f'<br><p><img src="cid:{chart_id}" alt="{chart_title}" style="max-width:100%;"></p>'
        )
        inline_images.append({
            "cid": chart_id,
            "bytes": chart_bytes,
            "filename": f"{chart_id}.png",
        })
        attached_chart_ids.append(chart_id)

    if missing_chart_ids:
        return {
            "status": "error",
            "message": (
                f"chart_id(s) {missing_chart_ids} were not found (charts are only kept "
                "in memory for the current session - they may have expired or never "
                "existed). Ask the user if they'd like those charts regenerated. "
                "Nothing was sent - resolve this before retrying."
            ),
        }

    if chart_html_blocks:
        body_html = (body_html or f"<p>{body}</p>") + "".join(chart_html_blocks)

    # Debug visibility: confirms whether the agent actually generated HTML
    # or just labeled the draft "HTML" without producing real markup, and
    # exactly which chart_ids were actually attached (not just intended).
    print(f"[EMAIL TOOL CALL] body_html provided: {bool(body_html)}"
          f"{' (' + str(len(body_html)) + ' chars)' if body_html else ''}"
          f" | chart_ids attached: {attached_chart_ids}")

    result = send_email_smtp(
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        body_html=body_html,
        inline_images=inline_images if inline_images else None,
    )

    # Echo back exactly which charts were attached so the agent's confirmation
    # message is grounded in what actually happened, not what it intended to
    # send - do not claim charts were sent beyond what's listed here.
    if result.get("status") == "success":
        result["chart_ids_attached"] = attached_chart_ids

    return result


send_email_tool = StructuredTool.from_function(
    func=_send_email,
    name="send_email",
    description=(
        "Sends an email via SMTP, optionally with an HTML-formatted body (e.g. a "
        "table) and/or one or more previously-created charts (via chart_ids). Call "
        "this ONLY after the user has been shown the exact recipient, subject, and "
        "content, and has given an explicit, unambiguous 'yes/send it' "
        "confirmation. Never call this speculatively or without a confirmed draft. "
        "Call at most once per confirmed draft - if the user wants multiple charts "
        "sent, include all of them in chart_ids on that single call, never split "
        "across multiple send_email calls. After the call returns, base your "
        "confirmation message strictly on the chart_ids_attached field in the "
        "result - never state that a chart was sent if its id is not in that list."
    ),
    args_schema=SendEmailInput,
)