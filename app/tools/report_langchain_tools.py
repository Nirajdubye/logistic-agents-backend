from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from app.tools.db_readonly_tool import get_database_schema, run_readonly_query
from app.tools.chart_tool import create_chart_impl


# =====================================================================
# get_database_schema - no input needed
# =====================================================================
def _get_schema():
    return get_database_schema()


get_schema_tool = StructuredTool.from_function(
    func=_get_schema,
    name="get_database_schema",
    description=(
        "Returns the real table and column names (and types) available in "
        "the database. ALWAYS call this first if you are not already certain "
        "of the exact table/column names needed - never guess a column name."
    ),
)


# =====================================================================
# run_readonly_query
# =====================================================================
class RunQueryInput(BaseModel):
    sql: str = Field(
        description=(
            "A single, complete, read-only SQL SELECT (or WITH ... SELECT) "
            "statement. Never include INSERT/UPDATE/DELETE/DROP/ALTER or any "
            "other write/DDL statement - these will be rejected. Never "
            "include more than one statement."
        )
    )
    max_rows: int = Field(default=200, description="Maximum rows to return. Defaults to 200.")


def _run_query(sql: str, max_rows: int = 200):
    return run_readonly_query(sql=sql, max_rows=max_rows)


run_query_tool = StructuredTool.from_function(
    func=_run_query,
    name="run_readonly_query",
    description=(
        "Executes a read-only SQL SELECT query against the logistics database "
        "and returns the resulting rows. Use this for any analytics request: "
        "averages, sums, counts, comparisons between time periods (e.g. use "
        "date_trunc('month', some_date_column) to group by month), 'last N "
        "records' (ORDER BY ... DESC LIMIT N), or any other statistic. Any "
        "query containing INSERT, UPDATE, DELETE, DROP, ALTER, or similar "
        "write/DDL keywords will be rejected automatically - this tool can "
        "only ever read data, never modify it."
    ),
    args_schema=RunQueryInput,
)


# =====================================================================
# create_chart
# =====================================================================
class CreateChartInput(BaseModel):
    title: str = Field(description="Title of the chart.")
    chart_type: Literal["bar", "line", "pie", "scatter", "area", "donut", "barh", "auto"] = Field(
        default="bar", description="Type of chart ('bar', 'line', 'pie', 'scatter', 'area', 'donut', 'barh', or 'auto')."
    )
    data: List[dict] | None = Field(
        default=None,
        description=(
            "List of dictionary objects from run_readonly_query output. "
            "For multi-series / grouped charts or general datasets, provide rows containing "
            "category columns, optional grouping columns, and numeric metric values."
        ),
    )
    x_axis: str | None = Field(
        default=None,
        description="Key/column name in data objects to use for primary X-axis categories.",
    )
    y_axis: str | None = Field(
        default=None,
        description="Key/column name in data objects containing numeric Y-axis values.",
    )
    group_by: str | None = Field(
        default=None,
        description=(
            "Optional key/column name in data objects for secondary grouping / comparison series "
            "(renders side-by-side grouped bars or multi-line trends)."
        ),
    )
    value_columns: List[str] | None = Field(
        default=None,
        description=(
            "Optional list of numeric column names when data is wide-format "
            "(e.g. ['last_month', 'this_month']). Each column becomes a distinct colored series."
        ),
    )
    labels: List[str] | None = Field(
        default=None, description="1D category/x-axis labels fallback array."
    )
    values: List[float] | None = Field(
        default=None, description="1D numeric values fallback array."
    )


def _create_chart(
    title: str,
    chart_type: str = "bar",
    data: List[dict] | None = None,
    x_axis: str | None = None,
    y_axis: str | None = None,
    group_by: str | None = None,
    value_columns: List[str] | None = None,
    labels: List[str] | None = None,
    values: List[float] | None = None,
):
    return create_chart_impl(
        title=title,
        chart_type=chart_type,
        data=data,
        x_axis=x_axis,
        y_axis=y_axis,
        group_by=group_by,
        value_columns=value_columns,
        labels=labels,
        values=values,
    )


create_chart_tool = StructuredTool.from_function(
    func=_create_chart,
    name="create_chart",
    description=(
        "Creates a generic single-series or multi-series (grouped) bar, line, or pie chart "
        "from SQL query output (run_readonly_query) and returns a chart_id (not the raw image). "
        "Pass 'data' (SQL output rows), 'x_axis', 'y_axis', and optional 'group_by' (for comparison "
        "or multi-group series). Mention the chart_id in your text answer."
    ),
    args_schema=CreateChartInput,
)


def get_report_tools():
    return [get_schema_tool, run_query_tool, create_chart_tool]