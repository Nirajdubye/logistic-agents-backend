"""
Generates a chart from data the agent already retrieved via run_readonly_query,
and returns a short chart_id instead of the raw image.

WHY A chart_id INSTEAD OF EMBEDDING THE IMAGE DIRECTLY IN THE ANSWER:
A base64-encoded PNG is often 5,000-50,000+ characters of text. If that
gets embedded directly in the agent's chat answer, it also gets stored in
`history` and resent in full on every subsequent turn (per how the
orchestrator works) - conversation context would balloon after just one
or two charts. Instead, the actual image lives in an in-memory cache here,
and only a short id (e.g. "chart_1") plus a plain-text description travels
through the conversation. When the user later says "email me that chart",
the email tool looks up the real image by that id.

LIMITATION: the cache is in-memory and per-process. Charts are lost on
restart, and aren't shared across multiple worker processes if you ever
scale this beyond a single process. Fine for now; if that becomes a
problem later, swap _CHART_CACHE for a small database table or Redis.
"""

import io
import base64
from typing import List, Optional, Union

import matplotlib
matplotlib.use("Agg")  # no display server needed - we only ever save to bytes
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

_CHART_CACHE: dict[str, dict] = {}  # chart_id -> {"html": "<img ...>", "title": ..., "data": {...}}
_chart_counter = 0

SUPPORTED_CHART_TYPES = ("bar", "line", "pie", "scatter", "area", "donut", "barh", "auto")

# ---------------------------------------------------------------------
# Visual style — centralized so every chart looks consistent
# ---------------------------------------------------------------------
_BG_COLOR = "#FFFFFF"
_TEXT_COLOR = "#1F2937"        # slate-800
_GRID_COLOR = "#E5E7EB"        # gray-200
_ACCENT = "#2563EB"            # blue-600
_PALETTE = [
    "#2563EB",  # blue
    "#F97316",  # orange
    "#10B981",  # emerald
    "#EF4444",  # red
    "#8B5CF6",  # violet
    "#F59E0B",  # amber
    "#06B6D4",  # cyan
    "#EC4899",  # pink
]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": _GRID_COLOR,
    "axes.labelcolor": _TEXT_COLOR,
    "text.color": _TEXT_COLOR,
    "xtick.color": _TEXT_COLOR,
    "ytick.color": _TEXT_COLOR,
    "figure.facecolor": _BG_COLOR,
    "axes.facecolor": _BG_COLOR,
    "savefig.facecolor": _BG_COLOR,
})


def _style_axes(ax):
    """Removes clutter (top/right spines) and adds a light horizontal grid."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_GRID_COLOR)
    ax.spines["bottom"].set_color(_GRID_COLOR)
    ax.grid(axis="y", color=_GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _format_value(v: float) -> str:
    """Compact number formatting for on-chart labels (1234 -> 1.2K)."""
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:.1f}K"
    if float(v).is_integer():
        return f"{int(v)}"
    return f"{v:.2f}"


def _resolve_key(target: Optional[str], sample_keys: List[str]) -> Optional[str]:
    """Smart key resolution matching exact, case-insensitive, normalized, or substring keys."""
    if not target or not sample_keys:
        return None

    if target in sample_keys:
        return target

    target_norm = target.lower().strip().replace("_", "").replace(" ", "")

    for k in sample_keys:
        k_norm = k.lower().strip().replace("_", "").replace(" ", "")
        if k_norm == target_norm:
            return k

    for k in sample_keys:
        k_norm = k.lower().strip().replace("_", "").replace(" ", "")
        if target_norm in k_norm or k_norm in target_norm:
            return k

    return None


def create_chart_impl(
    title: str,
    chart_type: str = "bar",
    data: Optional[List[dict]] = None,
    x_axis: Optional[str] = None,
    y_axis: Optional[str] = None,
    group_by: Optional[str] = None,
    value_columns: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    values: Optional[List[float]] = None,
) -> dict:
    global _chart_counter

    if not chart_type or chart_type == "auto":
        chart_type = "bar"
    else:
        chart_type = chart_type.lower().strip()

    if chart_type not in SUPPORTED_CHART_TYPES:
        return {
            "status": "error",
            "message": f"Unsupported chart_type '{chart_type}'. Use one of: {SUPPORTED_CHART_TYPES}.",
        }

    categories = []
    series_dict = {}  # group_name -> list of values corresponding to categories
    single_values = []
    is_grouped = False

    if data and isinstance(data, list) and len(data) > 0:
        sample = data[0]
        sample_keys = list(sample.keys())

        # Resolve user/agent specified column keys with smart matching
        resolved_x = _resolve_key(x_axis, sample_keys)
        resolved_y = _resolve_key(y_axis, sample_keys)
        resolved_g = _resolve_key(group_by, sample_keys)
        y_axis_explicit = resolved_y is not None

        # 1. Resolve X axis
        if resolved_x:
            x_axis = resolved_x
        else:
            # Auto-detect X axis: prefer identifier/code/number/string keys
            x_axis = None
            for k in sample_keys:
                k_lower = k.lower()
                if any(w in k_lower for w in ["code", "number", "id", "name", "date", "status", "type"]):
                    x_axis = k
                    break
            if not x_axis:
                for k in sample_keys:
                    val = sample.get(k)
                    if not isinstance(val, (int, float)):
                        x_axis = k
                        break
            if not x_axis:
                x_axis = sample_keys[0]

        # 2. Resolve Group By
        if resolved_g and resolved_g != x_axis:
            group_by = resolved_g
        else:
            group_by = None

        # 3. Resolve Y axis
        if resolved_y and resolved_y != x_axis:
            y_axis = resolved_y
        else:
            y_axis = None
            for k in sample_keys:
                if k != x_axis and k != group_by:
                    val = sample.get(k)
                    if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).isdigit()):
                        y_axis = k
                        break
            if not y_axis:
                remaining = [k for k in sample_keys if k != x_axis and k != group_by]
                y_axis = remaining[0] if remaining else sample_keys[-1]

        # Identify numeric columns
        numeric_keys = []
        for k in sample_keys:
            if k != x_axis and k != group_by:
                val = sample.get(k)
                if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).isdigit()):
                    numeric_keys.append(k)

        # Wide-Format Multi-Series Column Selection (Only if y_axis was not explicitly specified or value_columns passed)
        if value_columns:
            target_value_cols = [k for k in [_resolve_key(vc, sample_keys) for vc in value_columns] if k]
        elif not y_axis_explicit and len(numeric_keys) > 1 and not group_by:
            target_value_cols = numeric_keys
        else:
            target_value_cols = None

        if target_value_cols and len(target_value_cols) > 1:
            # WIDE-FORMAT MULTI-SERIES DATA
            is_grouped = True
            categories = [str(row.get(x_axis, "") if row.get(x_axis) is not None else "N/A") for row in data]

            for col in target_value_cols:
                series_label = col.replace("_", " ").title()
                col_vals = []
                for row in data:
                    raw_v = row.get(col, 0.0)
                    try:
                        v_val = float(raw_v) if raw_v is not None else 0.0
                    except (ValueError, TypeError):
                        v_val = 0.0
                    col_vals.append(v_val)
                series_dict[series_label] = col_vals

        elif group_by and group_by in sample_keys and group_by != x_axis:
            # LONG-FORMAT GROUPED DATA
            is_grouped = True
            cat_set = []
            grp_set = []
            pivot = {}

            for row in data:
                c_val = str(row.get(x_axis, "") if row.get(x_axis) is not None else "N/A")
                g_val = str(row.get(group_by, "") if row.get(group_by) is not None else "N/A")
                raw_v = row.get(y_axis, 0.0)
                try:
                    v_val = float(raw_v) if raw_v is not None else 0.0
                except (ValueError, TypeError):
                    v_val = 0.0

                if c_val not in cat_set:
                    cat_set.append(c_val)
                if g_val not in grp_set:
                    grp_set.append(g_val)
                pivot[(c_val, g_val)] = v_val

            categories = cat_set
            for g in grp_set:
                series_dict[g] = [pivot.get((c, g), 0.0) for c in categories]

        else:
            # 1D SINGLE METRIC DATA
            cat_list = []
            val_list = []
            for row in data:
                c_val = str(row.get(x_axis, "") if row.get(x_axis) is not None else "N/A")
                raw_v = row.get(y_axis, 0.0)
                try:
                    v_val = float(raw_v) if raw_v is not None else 0.0
                except (ValueError, TypeError):
                    v_val = 0.0
                cat_list.append(c_val)
                val_list.append(v_val)
            categories = cat_list
            single_values = val_list

    elif labels and values and len(labels) == len(values):
        categories = [str(l) for l in labels]
        single_values = [float(v) for v in values]
    else:
        return {
            "status": "error",
            "message": "Invalid input: provide either 'data' with x_axis/y_axis or 'labels' and 'values' arrays.",
        }

    if not categories:
        return {"status": "error", "message": "No valid chart categories were found."}

    fig, ax = plt.subplots(figsize=(8.0, 4.5), dpi=150)

    if is_grouped and len(series_dict) > 1:
        group_names = list(series_dict.keys())
        num_groups = len(group_names)
        num_cats = len(categories)
        x_indices = np.arange(num_cats)

        if chart_type == "bar":
            total_width = 0.75
            bar_width = total_width / num_groups

            for g_idx, g_name in enumerate(group_names):
                g_vals = series_dict[g_name]
                offset = (g_idx - (num_groups - 1) / 2) * bar_width
                color = _PALETTE[g_idx % len(_PALETTE)]
                bars = ax.bar(
                    x_indices + offset,
                    g_vals,
                    width=bar_width,
                    label=g_name,
                    color=color,
                    zorder=3,
                    edgecolor="none",
                )

                y_max = max(g_vals) if g_vals else 0
                pad = (y_max * 0.02) if y_max > 0 else 0.02
                for rect, v in zip(bars, g_vals):
                    height = rect.get_height()
                    ax.text(
                        rect.get_x() + rect.get_width() / 2,
                        height + pad,
                        _format_value(v),
                        ha="center",
                        va="bottom",
                        fontsize=8.5,
                        color=_TEXT_COLOR,
                    )

            _style_axes(ax)
            ax.set_xticks(x_indices)
            ax.set_xticklabels(categories, rotation=30, ha="right", fontsize=9.5)
            ax.set_ylabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)
            ax.legend(frameon=False, fontsize=9.5, loc="upper right")
            ax.margins(y=0.18)

        elif chart_type == "barh":
            y_indices = np.arange(num_cats)
            total_height = 0.75
            bar_height = total_height / num_groups

            for g_idx, g_name in enumerate(group_names):
                g_vals = series_dict[g_name]
                offset = (g_idx - (num_groups - 1) / 2) * bar_height
                color = _PALETTE[g_idx % len(_PALETTE)]
                bars = ax.barh(
                    y_indices + offset,
                    g_vals,
                    height=bar_height,
                    label=g_name,
                    color=color,
                    zorder=3,
                    edgecolor="none",
                )

                x_max = max(g_vals) if g_vals else 0
                pad = (x_max * 0.02) if x_max > 0 else 0.02
                for rect, v in zip(bars, g_vals):
                    ax.text(
                        rect.get_width() + pad,
                        rect.get_y() + rect.get_height() / 2,
                        _format_value(v),
                        ha="left",
                        va="center",
                        fontsize=8.5,
                        color=_TEXT_COLOR,
                    )

            _style_axes(ax)
            ax.set_yticks(y_indices)
            ax.set_yticklabels(categories, fontsize=9.5)
            ax.set_xlabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)
            ax.invert_yaxis()
            ax.legend(frameon=False, fontsize=9.5, loc="upper right")
            ax.margins(x=0.18)

        elif chart_type in ("line", "area"):
            for g_idx, g_name in enumerate(group_names):
                g_vals = series_dict[g_name]
                color = _PALETTE[g_idx % len(_PALETTE)]
                ax.plot(
                    categories,
                    g_vals,
                    marker="o",
                    markersize=5.5,
                    linewidth=2.2,
                    label=g_name,
                    color=color,
                    zorder=3,
                )
                if chart_type == "area":
                    ax.fill_between(range(len(categories)), g_vals, color=color, alpha=0.15, zorder=2)
                for i, v in enumerate(g_vals):
                    ax.annotate(
                        _format_value(v),
                        (i, v),
                        textcoords="offset points",
                        xytext=(0, 9),
                        ha="center",
                        fontsize=8.5,
                        color=_TEXT_COLOR,
                    )
            _style_axes(ax)
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=9.5)
            ax.set_ylabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)
            ax.legend(frameon=False, fontsize=9.5, loc="upper right")

        elif chart_type == "scatter":
            x_indices = np.arange(len(categories))
            try:
                x_numeric = [float(c) for c in categories]
                use_numeric_x = True
            except (ValueError, TypeError):
                use_numeric_x = False
                x_numeric = x_indices

            # Check for high disparity in Y values (e.g. 3.1M vs 58) to prevent squishing
            all_y = [v for g in series_dict.values() for v in g if v > 0]
            if all_y and (max(all_y) / (min(all_y) or 1)) > 200:
                ax.set_yscale("symlog", linthresh=100.0)

            for g_idx, g_name in enumerate(group_names):
                g_vals = series_dict[g_name]
                color = _PALETTE[g_idx % len(_PALETTE)]
                ax.scatter(
                    x_numeric,
                    g_vals,
                    s=80,
                    label=g_name,
                    color=color,
                    alpha=0.85,
                    zorder=3,
                )
                num_pts = len(x_numeric)
                lbl_fontsize = 7.5 if num_pts > 10 else 8.5
                for pt_idx, (x_pos, y_val) in enumerate(zip(x_numeric, g_vals)):
                    # Alternate vertical offsets to prevent label collision on dense plots
                    y_offset = 11 if pt_idx % 2 == 0 else -14
                    ax.annotate(
                        _format_value(y_val),
                        (x_pos, y_val),
                        textcoords="offset points",
                        xytext=(0, y_offset),
                        ha="center",
                        fontsize=lbl_fontsize,
                        color=_TEXT_COLOR,
                    )
            _style_axes(ax)
            if not use_numeric_x:
                ax.set_xticks(x_indices)
                rot_deg = 40 if any(len(str(c)) > 10 for c in categories) else 30
                ax.set_xticklabels(categories, rotation=rot_deg, ha="right", fontsize=8.5 if len(categories) > 10 else 9.5)
            else:
                ax.set_xlabel(x_axis.replace("_", " ").title() if x_axis else "X", fontsize=10, labelpad=8)

            ax.set_ylabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)
            ax.legend(frameon=False, fontsize=9.5, loc="upper right")
            ax.margins(x=0.08, y=0.18)

        elif chart_type in ("pie", "donut"):
            g_totals = [sum(series_dict[g]) for g in group_names]
            colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(group_names))]
            wedge_width = 0.45 if chart_type == "donut" else 1.0
            wedges, texts, autotexts = ax.pie(
                g_totals,
                labels=None,
                autopct="%1.1f%%",
                startangle=90,
                colors=colors,
                pctdistance=0.75,
                wedgeprops={"width": wedge_width, "linewidth": 2, "edgecolor": _BG_COLOR},
            )
            for at in autotexts:
                at.set_color("white")
                at.set_fontsize(9.5)
                at.set_fontweight("bold")
            ax.legend(
                wedges,
                group_names,
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                frameon=False,
                fontsize=9.5,
            )
            ax.axis("equal")
    else:
        values = single_values
        if chart_type == "bar":
            import re
            from matplotlib.patches import Patch

            # Auto-detect period/group tags in categories (e.g. '2072 (Aug)' vs '2050 (Jul)')
            group_tags = []
            for c in categories:
                match = re.search(r'\(([^)]+)\)', str(c))
                tag = match.group(1).strip() if match else None
                group_tags.append(tag)

            unique_tags = []
            for t in group_tags:
                if t and t not in unique_tags:
                    unique_tags.append(t)

            if len(unique_tags) > 1:
                # Color code bars by group/period tag (e.g. Aug = Blue, Jul = Orange)
                tag_colors = {t: _PALETTE[idx % len(_PALETTE)] for idx, t in enumerate(unique_tags)}
                bar_colors = [tag_colors.get(t, _ACCENT) for t in group_tags]
                bars = ax.bar(categories, values, color=bar_colors, width=0.6, zorder=3, edgecolor="none")

                legend_elements = [Patch(facecolor=tag_colors[t], label=t) for t in unique_tags]
                ax.legend(handles=legend_elements, frameon=False, fontsize=9.5, loc="upper right")
            else:
                bars = ax.bar(categories, values, color=_ACCENT, width=0.6, zorder=3, edgecolor="none")

            _style_axes(ax)
            ax.set_ylabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)

            y_max = max(values) if values else 0
            pad = (y_max * 0.02) if y_max else 0.02
            num_cats = len(categories)

            # Prevent text label overlap: use smaller font and rotation when category count is high
            lbl_fontsize = 7.5 if num_cats > 12 else (8.5 if num_cats > 8 else 9.5)
            lbl_rotation = 45 if num_cats > 10 else 0

            for rect, v in zip(bars, values):
                height = rect.get_height()
                if v == 0 and num_cats > 15:
                    continue
                ax.text(
                    rect.get_x() + rect.get_width() / 2,
                    height + pad,
                    _format_value(v),
                    ha="center" if lbl_rotation == 0 else "left",
                    va="bottom",
                    fontsize=lbl_fontsize,
                    rotation=lbl_rotation,
                    color=_TEXT_COLOR,
                )
            ax.margins(y=0.22)

        elif chart_type == "barh":
            y_indices = np.arange(len(categories))
            bars = ax.barh(
                y_indices,
                values,
                color=_ACCENT,
                height=0.6,
                zorder=3,
                edgecolor="none",
            )
            _style_axes(ax)
            ax.set_yticks(y_indices)
            ax.set_yticklabels(categories, fontsize=9.5)
            ax.set_xlabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)
            ax.invert_yaxis()
            x_max = max(values) if values else 0
            pad = (x_max * 0.02) if x_max else 0.02
            for rect, v in zip(bars, values):
                ax.text(
                    rect.get_width() + pad,
                    rect.get_y() + rect.get_height() / 2,
                    _format_value(v),
                    ha="left",
                    va="center",
                    fontsize=9,
                    color=_TEXT_COLOR,
                )
            ax.margins(x=0.18)

        elif chart_type in ("line", "area"):
            x_indices = np.arange(len(categories))
            ax.plot(
                x_indices,
                values,
                marker="o",
                markersize=5.5,
                linewidth=2.2,
                color=_ACCENT,
                markerfacecolor="white",
                markeredgecolor=_ACCENT,
                markeredgewidth=1.8,
                zorder=3,
            )
            if chart_type == "area":
                ax.fill_between(x_indices, values, color=_ACCENT, alpha=0.15, zorder=2)
            _style_axes(ax)
            ax.set_xticks(x_indices)
            ax.set_xticklabels(categories, rotation=30, ha="right", fontsize=9.5)
            ax.set_ylabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)

            for i, v in enumerate(values):
                ax.annotate(
                    _format_value(v),
                    (i, v),
                    textcoords="offset points",
                    xytext=(0, 9),
                    ha="center",
                    fontsize=9,
                    color=_TEXT_COLOR,
                )
            ax.margins(x=0.05, y=0.15)

        elif chart_type == "scatter":
            x_indices = np.arange(len(categories))
            try:
                x_numeric = [float(c) for c in categories]
                use_numeric_x = True
            except (ValueError, TypeError):
                use_numeric_x = False
                x_numeric = x_indices

            # Check for high disparity in Y values to prevent squishing along bottom axis
            pos_vals = [v for v in values if v > 0]
            if pos_vals and (max(pos_vals) / (min(pos_vals) or 1)) > 200:
                ax.set_yscale("symlog", linthresh=100.0)

            ax.scatter(
                x_numeric,
                values,
                s=80,
                color=_ACCENT,
                edgecolors="none",
                alpha=0.85,
                zorder=3,
            )
            _style_axes(ax)
            if not use_numeric_x:
                ax.set_xticks(x_indices)
                rot_deg = 40 if any(len(str(c)) > 10 for c in categories) else 30
                ax.set_xticklabels(categories, rotation=rot_deg, ha="right", fontsize=8.5 if len(categories) > 10 else 9.5)
            else:
                ax.set_xlabel(x_axis.replace("_", " ").title() if x_axis else "X", fontsize=10, labelpad=8)

            ax.set_ylabel(y_axis.replace("_", " ").title() if y_axis else "Value", fontsize=10, labelpad=8)

            num_pts = len(x_numeric)
            lbl_fontsize = 7.5 if num_pts > 10 else 8.5
            for pt_idx, (x_pos, y_val) in enumerate(zip(x_numeric, values)):
                y_offset = 11 if pt_idx % 2 == 0 else -14
                ax.annotate(
                    _format_value(y_val),
                    (x_pos, y_val),
                    textcoords="offset points",
                    xytext=(0, y_offset),
                    ha="center",
                    fontsize=lbl_fontsize,
                    color=_TEXT_COLOR,
                )
            ax.margins(x=0.08, y=0.18)

        elif chart_type in ("pie", "donut"):
            colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(categories))]
            wedge_width = 0.45 if chart_type == "donut" else 1.0
            wedges, texts, autotexts = ax.pie(
                values,
                labels=None,
                autopct="%1.1f%%",
                startangle=90,
                colors=colors,
                pctdistance=0.75,
                wedgeprops={"width": wedge_width, "linewidth": 2, "edgecolor": _BG_COLOR},
            )
            for at in autotexts:
                at.set_color("white")
                at.set_fontsize(9.5)
                at.set_fontweight("bold")
            ax.legend(
                wedges,
                categories,
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                frameon=False,
                fontsize=9.5,
            )
            ax.axis("equal")

    if chart_type in ("bar", "line", "area"):
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=9.5)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=6))

    ax.set_title(title, fontsize=13.5, fontweight="bold", color=_TEXT_COLOR, pad=14)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    png_bytes = buf.getvalue()
    b64 = base64.b64encode(png_bytes).decode("utf-8")

    img_html = f'<img src="data:image/png;base64,{b64}" alt="{title}" style="max-width:100%;">'

    _chart_counter += 1
    chart_id = f"chart_{_chart_counter}"
    data_summary = series_dict if is_grouped else dict(zip(categories, single_values))

    _CHART_CACHE[chart_id] = {
        "html": img_html,
        "title": title,
        "data": data_summary,
        "bytes": png_bytes,
        "b64": b64,
    }

    return {
        "status": "success",
        "chart_id": chart_id,
        "title": title,
        "data_summary": data_summary,
        "note": (
            f"Chart created and stored as '{chart_id}'. Describe what it shows in your "
            "answer using data_summary above. DO NOT under any circumstances copy, paste, "
            "or reference the raw image data anywhere in your text response. To email it, "
            f"call send_email with chart_id='{chart_id}'."
        ),
    }


def get_chart_html(chart_id: str) -> str | None:
    entry = _CHART_CACHE.get(chart_id)
    return entry["html"] if entry else None


def get_chart_bytes(chart_id: str) -> bytes | None:
    entry = _CHART_CACHE.get(chart_id)
    return entry.get("bytes") if entry else None


def get_chart_title(chart_id: str) -> str | None:
    entry = _CHART_CACHE.get(chart_id)
    return entry["title"] if entry else None