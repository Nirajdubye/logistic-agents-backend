from langchain_core.messages import AIMessage

from app.agent.llm import llm
from app.agent.checkpointer import checkpointer
from app.agent.prompt import GENERAL_PROMPT
from app.agent.router import route_query
from app.agent.operational_agent import operational_agent
from app.agent.policy_agent import policy_agent
from app.agent.email_agent import email_agent
from app.agent.report_agent import report_agent
from app.agent.utils import extract_text
from app.tools.schema_guard import pre_route_schema_guard, post_response_schema_guard


####################################################################
# General (non-routed) handling
####################################################################

def handle_general(query: str) -> str:
    response = llm.invoke([
        {"role": "system", "content": GENERAL_PROMPT},
        {"role": "user", "content": query},
    ])
    return extract_text(response)


####################################################################
# Orchestrator
####################################################################
# Routes each user message to the correct specialist agent(s) via a
# deterministic classifier (see router.py), rather than relying on an
# LLM's free-text judgment about when to defer. Returns output shaped
# like a normal LangGraph agent so chat.py and server.py stay unified.
####################################################################

class OrchestratorAgent:

    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer
        self._history: dict[str, list] = {}

    def _get_thread_id(self, config: dict | None) -> str:
        if config and "configurable" in config:
            return config["configurable"].get("thread_id", "default")
        return "default"

    def invoke(self, input: dict, config: dict | None = None):
        messages = input.get("messages", [])
        if not messages:
            raise ValueError("No messages provided to orchestrator.")

        last_message = messages[-1]
        query = (
            last_message["content"]
            if isinstance(last_message, dict)
            else last_message.content
        )

        thread_id = self._get_thread_id(config)
        history = self._history.setdefault(thread_id, [])
        history.append({"role": "user", "content": query})

        # -------------------------------------------------------------
        # Security Guard Layer 1 & 2: Pre-route schema leakage defense
        # -------------------------------------------------------------
        schema_guard_response = pre_route_schema_guard(query, llm=llm)
        if schema_guard_response is not None:
            history.append({"role": "assistant", "content": schema_guard_response})
            return {
                "messages": messages + [AIMessage(content=schema_guard_response)],
                "route": "general",
            }

        # Pass recent history (before this turn's query was appended) so the
        # router can resolve follow-ups like "what are those months" instead
        # of classifying the message in isolation.
        destination = route_query(query, recent_history=history[:-1])

        if destination == "general":
            final_content = handle_general(query)

        elif destination == "operations":
            result = operational_agent.invoke({"messages": history}, config=config)
            final_content = extract_text(result["messages"][-1])

        elif destination == "policy":
            result = policy_agent.invoke({"messages": history}, config=config)
            final_content = extract_text(result["messages"][-1])

        elif destination == "email":
            # email_agent gets the FULL shared history
            result = email_agent.invoke({"messages": history}, config=config)
            final_content = extract_text(result["messages"][-1])

        elif destination == "report":
            # report_agent queries analytics/SQL and creates charts
            result = report_agent.invoke({"messages": history}, config=config)
            final_content = extract_text(result["messages"][-1])

        else:  # both — fact-then-compliance chain
            ops_result = operational_agent.invoke({"messages": history}, config=config)
            ops_facts = extract_text(ops_result["messages"][-1])

            compliance_instruction = (
                "Relevant record facts (freshly retrieved from the database "
                f"for the user's question above):\n{ops_facts}\n\n"
                "VERIFICATION SCOPE & STRICT GROUNDING DIRECTIVES:\n"
                "1. SCOPE:\n"
                "   - If the user explicitly specified specific data points/fields to check (e.g. 'check customer info', 'verify shipment status'), verify ONLY those specified data points/fields.\n"
                "   - If the user did NOT specify specific data points (e.g. 'can you verify this with our document and check whether any violation is there or not', 'check for violations'), you MUST perform a FULL DATA VERIFICATION. Systematically inspect and verify EVERY data point and field present in the record facts above (status, mode, customer info, addresses, dates, weights/packages, financial details, etc.) against company policies using rag_search.\n\n"
                "2. STRICT DOCUMENT-ONLY GROUNDING (NO INVENTED LOGIC/RULES):\n"
                "   - Retrieve relevant policy text via rag_search and evaluate strictly against the document text.\n"
                "   - NEVER create, invent, extrapolate, or assume your own rules, logic, internal states, or standard practices (e.g. do NOT assume 'draft' is a plausible initial state before 'pending').\n\n"
                "3. FORMATTING UNMENTIONED FIELDS (CONCISE FORMAT):\n"
                "   - For fields that HAVE explicit policy rules in the documents: Provide full analysis (Relevant Policy, Comparison of Facts to Policy, Conclusion: VIOLATION or NO VIOLATION).\n"
                "   - For fields that DO NOT have any rule or mention in the document: Do NOT generate multi-bullet blocks ('Policy Reference...', 'Evaluation...', 'Conclusion: NOT MENTIONED...'). Instead, simply display the field name with a brief one-liner (e.g. '• **[Field Name]**: Not mentioned in company policies'), OR omit/don't show unmentioned fields completely.\n\n"
                "4. SCHEMA PRIVACY (NO RAW COLUMN NAMES):\n"
                "   - NEVER print raw database column names or code blocks (e.g. do NOT write `status: active`, `hold: false`, or `is_insured = true`).\n"
                "   - ALWAYS write facts using clean, human-friendly logistics business language (e.g. 'Account Status: Active, On Hold: No' or 'Insurance Status: Not Elected')."
            )

            policy_input_messages = history + [
                {"role": "system", "content": compliance_instruction}
            ]
            policy_result = policy_agent.invoke(
                {"messages": policy_input_messages}, config=config
            )
            final_content = extract_text(policy_result["messages"][-1])

        # -------------------------------------------------------------
        # Security Guard Layer 3: Post-response schema leak backstop
        # -------------------------------------------------------------
        final_content = post_response_schema_guard(final_content)

        history.append({"role": "assistant", "content": final_content})

        return {
            "messages": messages + [AIMessage(content=final_content)],
            "route": destination,
        }


agent = OrchestratorAgent(checkpointer=checkpointer)