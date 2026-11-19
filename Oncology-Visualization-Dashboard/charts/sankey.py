import math

import plotly.graph_objects as go

from .colors import get_group_color, hex_to_rgba, make_color_map


BAD_VALUES = {"", "nan", "NaN", "None", "Unknown"} # Not Applicable


def _spread_positions(n, top=0.06, bottom=0.94):
    """Return stable, non-overlapping y positions in paper/data coordinates."""
    if n <= 1:
        return [0.50]
    step = (bottom - top) / (n - 1)
    return [top + i * step for i in range(n)]


def _prepare_sankey_data(edges):
    work = edges.copy()
    work["CANCER_TYPE"] = work["CANCER_TYPE"].astype(str).str.strip()
    work["METASTATIC_SITE"] = work["METASTATIC_SITE"].astype(str).str.strip()
    work = work[
        ~work["CANCER_TYPE"].isin(BAD_VALUES)
        & ~work["METASTATIC_SITE"].isin(BAD_VALUES)
    ].copy()

    left_groups = (
        work.groupby("CANCER_TYPE")["count"]
        .sum()
        .sort_values(ascending=False)
        .index
        .astype(str)
        .tolist()
    )
    metas = (
        work.groupby("METASTATIC_SITE")["count"]
        .sum()
        .sort_values(ascending=False)
        .index
        .astype(str)
        .tolist()
    )
    return work, left_groups, metas


def _selection_sets(edges, selected_node, highlighted_cancer=None):
    selected_type = None
    selected_label = None
    if selected_node and isinstance(selected_node, dict):
        selected_type = selected_node.get("type")
        selected_label = selected_node.get("label")

    connected_groups = set()
    connected_metas = set()

    available_groups = set(edges["CANCER_TYPE"].dropna().astype(str).unique())
    available_metas = set(edges["METASTATIC_SITE"].dropna().astype(str).unique())

    if selected_type == "cancer" and selected_label:
        selected_label = str(selected_label)
        if selected_label in available_groups:
            connected_groups = {selected_label}
            connected_metas = set(
                edges.loc[edges["CANCER_TYPE"].astype(str) == selected_label, "METASTATIC_SITE"]
                .astype(str)
                .unique()
            )
    elif selected_type == "meta" and selected_label:
        selected_label = str(selected_label)
        if selected_label in available_metas:
            connected_metas = {selected_label}
            connected_groups = set(
                edges.loc[edges["METASTATIC_SITE"].astype(str) == selected_label, "CANCER_TYPE"]
                .astype(str)
                .unique()
            )
    elif highlighted_cancer is not None:
        if isinstance(highlighted_cancer, (list, tuple, set)):
            candidate_groups = {str(v) for v in highlighted_cancer if v is not None}
        else:
            candidate_groups = {str(highlighted_cancer)}
        connected_groups = candidate_groups & available_groups
        if connected_groups:
            connected_metas = set(
                edges.loc[edges["CANCER_TYPE"].astype(str).isin(connected_groups), "METASTATIC_SITE"]
                .astype(str)
                .unique()
            )

    return selected_type, selected_label, connected_groups, connected_metas


def _node_hover(label, kind, total, total_all_edges, edges, meta_threshold=None):
    pct_total = 100 * int(total) / max(1, int(total_all_edges))
    if kind == "cancer":
        return (
            f"<b>{label}</b><br>"
            f"Totale flusso visibile: {int(total)}<br>"
            f"% sul totale filtrato: {pct_total:.1f}%<br>"
            f"Clicca per evidenziare i rami collegati"
        )

    meta_distribution_df = (
        edges[edges["METASTATIC_SITE"].astype(str) == str(label)]
        .sort_values("count", ascending=False)
        [["CANCER_TYPE", "count", "pct_cancer_within_meta"]]
    )

    distribution_lines = []
    for _, dist_row in meta_distribution_df.iterrows():
        distribution_lines.append(
            f"- {dist_row['CANCER_TYPE']}: {int(dist_row['count'])} "
            f"({dist_row['pct_cancer_within_meta']:.1f}%)"
        )
    distribution_html = "<br>".join(distribution_lines)

    threshold_html = ""
    if meta_threshold is not None:
        threshold_html = f"Soglia metastasi attiva: >= {meta_threshold}<br>"

    return (
        f"<b>{label}</b><br>"
        f"Totale flusso visibile: {int(total)}<br>"
        f"% sul totale filtrato: {pct_total:.1f}%<br>"
        f"{threshold_html}"
        f"<br><b>Distribuzione sui gruppi visibili:</b><br>"
        f"{distribution_html}<br><br>"
        f"Clicca per evidenziare i rami collegati"
    )


def _link_width(count, count_min, count_max):
    if count_max <= count_min:
        return 11.0
    # Sqrt scaling keeps large flows visible without swallowing smaller ones.
    t = (math.sqrt(float(count)) - math.sqrt(float(count_min))) / (
        math.sqrt(float(count_max)) - math.sqrt(float(count_min))
    )
    return 2.8 + 24.0 * t


def _minimum_step(positions):
    if len(positions) <= 1:
        return 0.84
    return min(abs(positions[i + 1] - positions[i]) for i in range(len(positions) - 1))


def _scaled_node_height(total, side_max_total, max_height, *, min_height=0.010, gamma=1.30):
    """
    Scale node height relative to the largest visible node on that side.
    gamma > 1 increases contrast between small and large nodes.
    """
    max_height = max(0.012, float(max_height))
    min_height = max(0.008, min(float(min_height), max_height * 0.45))

    if side_max_total <= 0:
        return max_height * 0.60

    t = max(0.0, min(1.0, float(total) / float(side_max_total)))

    # gamma > 1 => more visual separation
    t = t ** gamma

    return min_height + (max_height - min_height) * t

def _scaled_marker_size(node_height, figure_height):
    """Convert data-coordinate node height to a pixel click target."""
    plot_height = max(320, int(figure_height or 620) - 90)
    return max(30, min(98, int(node_height * plot_height * 0.95)))


def make_sankey_figure(
    edges,
    selected_node=None,
    meta_threshold=None,
    highlighted_cancer=None,
    left_label="Cancer Type",
    title="Sankey-like: Cancer Type to Metastatic Site",
    figure_height=620,
    threshold_fallback=False,
    original_meta_threshold=None,
):
    """Build a stable Sankey-like diagram.

    Plotly's native Sankey is visually useful, but node/link clickData can become
    unreliable when nodes are close together: a link may intercept the click, or
    a nearby node can be returned. Here links are drawn as non-interactive layout
    shapes, while cancer/metastasis nodes are normal Scatter markers with stable
    customdata. This keeps highlighting predictable and makes zoom/pan native.
    """
    fig = go.Figure()
    figure_height = int(figure_height or 620)

    if edges is None or edges.empty:
        fig.update_layout(
            template="plotly_white",
            height=figure_height,
            xaxis=dict(visible=False, range=[0, 1], fixedrange=False),
            yaxis=dict(visible=False, range=[0, 1], fixedrange=False),
            annotations=[
                dict(
                    text="Nessun dato disponibile con i filtri selezionati",
                    showarrow=False,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    font=dict(size=16),
                )
            ],
            margin=dict(l=18, r=18, t=18, b=18),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        return fig

    edges, left_groups, metas = _prepare_sankey_data(edges)
    if edges.empty or not left_groups or not metas:
        fig.update_layout(
            template="plotly_white",
            height=figure_height,
            xaxis=dict(visible=False, range=[0, 1], fixedrange=False),
            yaxis=dict(visible=False, range=[0, 1], fixedrange=False),
            annotations=[
                dict(
                    text="Nessun collegamento disponibile con i filtri selezionati",
                    showarrow=False,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    font=dict(size=16),
                )
            ],
            margin=dict(l=18, r=18, t=18, b=18),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        return fig

    group_color_map = make_color_map(left_groups)

    group_totals = edges.groupby("CANCER_TYPE")["count"].sum().to_dict()
    meta_totals = edges.groupby("METASTATIC_SITE")["count"].sum().to_dict()
    total_all_edges = max(1, int(edges["count"].sum()))

    selected_type, selected_label, connected_groups, connected_metas = _selection_sets(
        edges=edges,
        selected_node=selected_node,
        highlighted_cancer=highlighted_cancer,
    )
    has_selection = bool(connected_groups or connected_metas)

    # Fixed semantic columns. These are data coordinates, so Plotly's native
    # zoom/pan works consistently.
    x_left = 0.16
    x_right = 0.82
    label_dx = 0.024
    y_left_positions = _spread_positions(len(left_groups), top=0.08, bottom=0.92)
    y_right_positions = _spread_positions(len(metas), top=0.08, bottom=0.92)
    group_pos = {g: (x_left, y_left_positions[i]) for i, g in enumerate(left_groups)}
    meta_pos = {m: (x_right, y_right_positions[i]) for i, m in enumerate(metas)}

    count_min = float(edges["count"].min())
    count_max = float(edges["count"].max())

    # Node size now carries quantity information. Heights are proportional to
    # visible totals, but capped by the available vertical spacing so nodes stay
    # stable and clickable.
    left_totals = [int(group_totals.get(g, 0)) for g in left_groups]
    right_totals = [int(meta_totals.get(m, 0)) for m in metas]

    left_step = _minimum_step(y_left_positions)
    right_step = _minimum_step(y_right_positions)

    # use more of the available vertical space
    max_left_node_h = min(0.26, max(0.020, left_step * 0.82))
    max_right_node_h = min(0.20, max(0.014, right_step * 0.78))

    left_max_total = max(left_totals) if left_totals else 0
    right_max_total = max(right_totals) if right_totals else 0

    group_heights = {
        g: _scaled_node_height(
            int(group_totals.get(g, 0)),
            left_max_total,
            max_left_node_h,
            min_height=0.015,
            gamma=1.35,
        )
        for g in left_groups
    }

    meta_heights = {
        m: _scaled_node_height(
            int(meta_totals.get(m, 0)),
            right_max_total,
            max_right_node_h,
            min_height=0.010,
            gamma=1.22,
        )
        for m in metas
    }

    shapes = []

    # Non-interactive links. Because these are layout shapes, they cannot steal
    # clickData from the nodes and they have no hover tooltip.
    node_rect_width = 0.032
    for _, row in edges.sort_values("count", ascending=True).iterrows():
        c = str(row["CANCER_TYPE"])
        m = str(row["METASTATIC_SITE"])
        count = int(row["count"])
        if c not in group_pos or m not in meta_pos:
            continue

        x0, y0 = group_pos[c]
        x1, y1 = meta_pos[m]
        base_color = get_group_color(c, group_color_map)

        if not has_selection:
            active = True
        elif selected_type == "meta":
            active = m in connected_metas
        elif selected_type == "cancer":
            active = c in connected_groups
        else:
            active = c in connected_groups

        if count_max == count_min:
            base_alpha = 0.34
        else:
            base_alpha = 0.18 + 0.34 * ((float(count) - count_min) / (count_max - count_min))

        alpha = 0.86 if (has_selection and active) else (0.025 if has_selection else base_alpha)
        width = _link_width(count, count_min, count_max)
        if has_selection and active:
            width += 2.5

        start_x = x0 + node_rect_width / 2
        end_x = x1 - node_rect_width / 2
        c1x = start_x + 0.28
        c2x = end_x - 0.28
        path = f"M {start_x},{y0} C {c1x},{y0} {c2x},{y1} {end_x},{y1}"
        shapes.append(
            dict(
                type="path",
                path=path,
                xref="x",
                yref="y",
                layer="below",
                line=dict(color=hex_to_rgba(base_color, alpha), width=width),
            )
        )

    # Node rectangles as background shapes, also non-interactive. Scatter markers
    # below provide the real click target.
    node_x = []
    node_y = []
    node_text = []
    node_customdata = []
    node_hover = []
    node_marker_colors = []
    node_marker_line_colors = []
    node_marker_sizes = []
    node_text_positions = []
    annotations = []

    for label in left_groups:
        x, y = group_pos[label]
        base_color = get_group_color(label, group_color_map)
        total = int(group_totals.get(label, 0))
        is_active = (not has_selection) or (label in connected_groups)
        fill_alpha = 0.90 if is_active else 0.10
        line_alpha = 1.00 if is_active else 0.18
        fill = hex_to_rgba(base_color, fill_alpha)
        line = hex_to_rgba(base_color, line_alpha)

        node_height = group_heights.get(label, 0.030)
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                layer="below",
                x0=x - node_rect_width / 2,
                x1=x + node_rect_width / 2,
                y0=y - node_height / 2,
                y1=y + node_height / 2,
                fillcolor=fill,
                line=dict(color=line, width=1.8 if is_active else 0.8),
            )
        )

        node_x.append(x)
        node_y.append(y)
        node_text.append("")
        annotations.append(
            dict(
                text=f"<b>{label}</b> ({total})" if is_active else f"{label} ({total})",
                x=x - node_rect_width / 2 - label_dx,
                y=y,
                xref="x",
                yref="y",
                showarrow=False,
                xanchor="right",
                yanchor="middle",
                font=dict(
                    size=12,
                    color="#111827" if is_active else "#9CA3AF",
                ),
            )
        )
        node_customdata.append(["cancer", label, _node_hover(label, "cancer", total, total_all_edges, edges, meta_threshold)])
        node_hover.append(_node_hover(label, "cancer", total, total_all_edges, edges, meta_threshold))
        node_marker_colors.append(hex_to_rgba(base_color, 0.01))
        node_marker_line_colors.append(hex_to_rgba(base_color, 0.01))
        node_marker_sizes.append(_scaled_marker_size(node_height, figure_height))
        node_text_positions.append("middle right")

    for label in metas:
        x, y = meta_pos[label]
        total = int(meta_totals.get(label, 0))
        is_active = (not has_selection) or (label in connected_metas)
        fill = hex_to_rgba("#111111", 0.92 if is_active else 0.12)
        line = hex_to_rgba("#111111", 1.00 if is_active else 0.16)

        node_height = meta_heights.get(label, 0.030)
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                layer="below",
                x0=x - node_rect_width / 2,
                x1=x + node_rect_width / 2,
                y0=y - node_height / 2,
                y1=y + node_height / 2,
                fillcolor=fill,
                line=dict(color=line, width=1.8 if is_active else 0.8),
            )
        )

        node_x.append(x)
        node_y.append(y)
        node_text.append("")
        annotations.append(
            dict(
                text=f"<b>{label}</b> ({total})" if is_active else f"{label} ({total})",
                x=x + node_rect_width / 2 + label_dx,
                y=y,
                xref="x",
                yref="y",
                showarrow=False,
                xanchor="left",
                yanchor="middle",
                font=dict(
                    size=12,
                    color="#111827" if is_active else "#9CA3AF",
                ),
            )
        )
        node_customdata.append(["meta", label, _node_hover(label, "meta", total, total_all_edges, edges, meta_threshold)])
        node_hover.append(_node_hover(label, "meta", total, total_all_edges, edges, meta_threshold))
        node_marker_colors.append("rgba(0,0,0,0.01)")
        node_marker_line_colors.append("rgba(0,0,0,0.01)")
        node_marker_sizes.append(_scaled_marker_size(node_height, figure_height))
        node_text_positions.append("middle left")

    # One single scatter trace drives all clicks. Links are shapes, so the click
    # can only come from these nodes.
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers",
            text=node_text,
            customdata=node_customdata,
            hovertemplate="%{customdata[2]}<extra></extra>",
            marker=dict(
                symbol="square",
                size=node_marker_sizes,
                color=node_marker_colors,
                line=dict(color=node_marker_line_colors, width=1),
            ),
            textposition=node_text_positions,
            textfont=dict(size=11, color="#1F2A44"),
            cliponaxis=False,
            showlegend=False,
        )
    )

    if threshold_fallback:
        annotations.append(
            dict(
                text=f"La soglia metastasi {original_meta_threshold} era troppo alta per questi filtri: mostro tutti i siti disponibili.",
                showarrow=False,
                x=0.5,
                y=1.035,
                xref="paper",
                yref="paper",
                font=dict(size=11, color="#6B7280"),
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=figure_height,
        autosize=True,
        margin=dict(l=190, r=180, t=34 if threshold_fallback else 16, b=28),
        clickmode="event+select",
        hovermode="closest",
        dragmode="pan",
        shapes=shapes,
        annotations=annotations,
        plot_bgcolor="white",
        paper_bgcolor="white",
        uirevision="stable-sankey-like",
    )

    fig.update_xaxes(
        visible=False,
        range=[0.0, 1.12],
        fixedrange=False,
        constrain="domain",
    )
    fig.update_yaxes(
        visible=False,
        range=[0.0, 1.0],
        fixedrange=False,
        scaleanchor=None,
    )

    return fig
