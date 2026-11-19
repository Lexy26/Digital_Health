from dash import Dash, dcc, html, Input, Output, State, ALL, callback_context, no_update

from loader import load_data
from charts.sankey import make_sankey_figure
from charts.death_age_bars import make_death_age_bars_figure
from charts.survival_km import make_survival_km_figure

from transforms import (
    filter_by_gender,
    filter_by_sample_type,
    filter_by_stage,
    get_filtered_df,
    get_oncotree_counts,
    build_edge_table,
    safe_filter_metastasis_edges,
)


CANCER_COLOR_MAP = {
    "Non-Small Cell Lung Cancer": "#4C78A8",
    "Breast Cancer": "#E45756",
    "Pancreatic Cancer": "#2CBF9B",
    "Colorectal Cancer": "#9D6CFF",
    "Prostate Cancer": "#F28E2B",
    "Other": "#9AA0A6",
}

CHART_SIZE_SCALE = 0.8
SANKEY_ZOOM_SCALE = 0.6


# =========================
# LOAD DATA
# =========================

DF = load_data()

ALL_CANCERS = sorted(
    [
        c
        for c in DF["CANCER_TYPE"].dropna().astype(str).unique().tolist()
        if c.strip() != ""
    ]
)


# =========================
# UI / STATE HELPERS
# =========================

def is_single_cancer(selected_cancers):
    return selected_cancers is not None and len(selected_cancers) == 1


def is_oncotree_mode(selected_cancers, oncotree_mode):
    return (
        is_single_cancer(selected_cancers)
        and oncotree_mode is not None
        and "on" in oncotree_mode
    )


def get_group_col(selected_cancers, oncotree_mode):
    return "ONCOTREE_CODE" if is_oncotree_mode(selected_cancers, oncotree_mode) else "CANCER_TYPE"


def get_group_label(selected_cancers, oncotree_mode):
    return "Histology / OncoTree code" if is_oncotree_mode(selected_cancers, oncotree_mode) else "Cancer type"


def valid_highlight_groups(df, group_col, highlighted_groups):
    if highlighted_groups is None or group_col not in df.columns:
        return None

    if isinstance(highlighted_groups, str):
        candidates = [highlighted_groups]
    else:
        candidates = list(highlighted_groups)

    values = set(df[group_col].dropna().astype(str).unique().tolist())
    valid = [group for group in candidates if group in values]

    return valid or None


def get_highlight_groups(df, group_col, active_selection, meta_threshold):
    if not active_selection:
        return None

    sel_type = active_selection.get("type")
    label = active_selection.get("label")

    if not label:
        return None

    if sel_type == "meta":
        edges = build_edge_table(df, group_col=group_col)
        edges, _, _ = safe_filter_metastasis_edges(edges, meta_threshold)

        if edges.empty:
            return None

        groups = (
            edges.loc[
                edges["METASTATIC_SITE"].astype(str) == str(label),
                "CANCER_TYPE",
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        return groups or None

    return valid_highlight_groups(df, group_col, [label])


def compute_sankey_card_height(
    gender,
    meta_threshold,
    selected_cancers,
    oncotree_mode,
    oncotree_codes,
    oncotree_min_count,
    chart_size_scale,
    sankey_zoom_scale=1.4,
    sample_type="All",
    stage_filter="All",
):
    """
    Calcola l'altezza della card del Sankey in base al numero di nodi visibili.
    Questa funzione resta in app.py perché riguarda il layout dinamico della UI.
    """
    scale = float(chart_size_scale or 1.0)
    base_height = int(680 * scale)

    df = get_filtered_df(
        DF,
        gender,
        selected_cancers,
        oncotree_mode,
        oncotree_codes,
        oncotree_min_count,
        sample_type,
        stage_filter,
    )

    group_col = get_group_col(selected_cancers, oncotree_mode)

    edges = build_edge_table(df, group_col=group_col)
    edges, _, _ = safe_filter_metastasis_edges(edges, meta_threshold)

    if edges.empty:
        return base_height

    left_nodes = int(edges["CANCER_TYPE"].nunique())
    right_nodes = int(edges["METASTATIC_SITE"].nunique())
    max_nodes = max(left_nodes, right_nodes, 1)

    zoom = float(sankey_zoom_scale or 1.4)
    px_per_node = 46 * zoom
    needed_height = int(max_nodes * px_per_node + 280)

    return max(base_height, needed_height)


# =========================
# STYLE HELPERS
# =========================

def cancer_button_style(cancer_name, is_active):
    base_color = CANCER_COLOR_MAP.get(cancer_name, CANCER_COLOR_MAP["Other"])

    return {
        "width": "100%",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "flex-start",
        "gap": "8px",
        "padding": "8px 10px",
        "borderRadius": "12px",
        "border": f"1px solid {base_color}",
        "background": base_color if is_active else "white",
        "color": "white" if is_active else "#333333",
        "cursor": "pointer",
        "fontSize": "13px",
        "fontWeight": "700" if is_active else "500",
        "textAlign": "left",
        "boxShadow": "0 1px 5px rgba(0,0,0,0.14)" if is_active else "none",
    }


PAGE_TITLE_STYLE = {
    "margin": "0 0 18px 0",
    "fontSize": "26px",
    "fontWeight": "800",
    "letterSpacing": "-0.4px",
    "color": "#111827",
}

SECTION_TITLE_STYLE = {
    "fontWeight": "800",
    "fontSize": "17px",
    "marginBottom": "14px",
    "paddingBottom": "8px",
    "borderBottom": "1px solid #eeeeee",
    "color": "#111827",
}

FIELD_LABEL_STYLE = {
    "fontWeight": "700",
    "fontSize": "12px",
    "textTransform": "uppercase",
    "letterSpacing": "0.3px",
    "color": "#323942",
    "marginBottom": "6px",
}

FIELD_LABEL_SPACED_STYLE = {
    **FIELD_LABEL_STYLE,
    "marginTop": "16px",
}

OPTION_TEXT_STYLE = {
    "fontSize": "13px",
    "color": "#111827",
    "lineHeight": "1.6",
}

HELP_TEXT_STYLE = {
    "fontSize": "12px",
    "color": "#6b7280",
    "marginTop": "6px",
    "lineHeight": "1.35",
}


def section_style():
    return {
        "background": "white",
        "border": "1px solid #dddddd",
        "borderRadius": "14px",
        "padding": "13px 14px",
        "boxShadow": "0 1px 4px rgba(0,0,0,0.04)",
    }


def section_title(text):
    return html.Div(text, style=SECTION_TITLE_STYLE)


def chart_card_style(height_px):
    return {
        "height": f"{int(height_px)}px",
        "minHeight": "420px",
        "border": "1px solid #dddddd",
        "borderRadius": "14px",
        "overflowY": "auto",
        "background": "white",
        "display": "flex",
        "flexDirection": "column",
        "boxShadow": "0 1px 5px rgba(0,0,0,0.05)",
    }


def chart_header(title, subtitle=None):
    return html.Div(
        [
            html.Div(
                title,
                style={
                    "fontWeight": "800",
                    "fontSize": "18px",
                    "color": "#222",
                },
            ),
            html.Div(
                subtitle or "",
                style={
                    "fontSize": "12px",
                    "color": "#666",
                    "marginTop": "2px",
                },
            ),
        ],
        style={
            "padding": "10px 14px 8px 14px",
            "borderBottom": "1px solid #eeeeee",
            "background": "#ffffff",
            "flex": "0 0 auto",
        },
    )


def graph_config():
    return {
        "scrollZoom": True,
        "displayModeBar": True,
        "doubleClick": "reset",
        "responsive": True,
    }


# =========================
# APP
# =========================

app = Dash(__name__)

app.layout = html.Div(
    style={
        "height": "100vh",
        "display": "flex",
        "overflow": "hidden",
        "fontFamily": "Arial, sans-serif",
        "background": "#fafafa",
    },
    children=[
        # =========================
        # FIXED LEFT SIDEBAR
        # =========================
        html.Div(
            style={
                "width": "335px",
                "minWidth": "335px",
                "height": "100vh",
                "boxSizing": "border-box",
                "padding": "16px 14px",
                "borderRight": "1px solid #dddddd",
                "background": "#f7f7f7",
                "overflowY": "auto",
                "position": "sticky",
                "top": 0,
                "zIndex": 10,
            },
            children=[
                html.H2("Clinical Dashboard", style=PAGE_TITLE_STYLE),

                html.Div(
                    id="highlighted-cancer-label",
                    style={"display": "none"},
                ),

                html.Div(
                    style={**section_style(), "marginBottom": "12px"},
                    children=[
                        section_title("Common filters"),

                        html.Div("Gender", style=FIELD_LABEL_STYLE),
                        dcc.RadioItems(
                            id="gender-filter",
                            options=[
                                {"label": " All", "value": "All"},
                                {"label": " Female", "value": "Female"},
                                {"label": " Male", "value": "Male"},
                            ],
                            value="All",
                            inline=True,
                            style=OPTION_TEXT_STYLE,
                        ),

                        html.Div("Sample type", style=FIELD_LABEL_SPACED_STYLE),
                        dcc.RadioItems(
                            id="sample-type-filter",
                            options=[
                                {"label": " All", "value": "All"},
                                {"label": " Metastasi", "value": "Metastasis"},
                                {"label": " Primary", "value": "Primary"},
                            ],
                            value="All",
                            inline=True,
                            style=OPTION_TEXT_STYLE,
                        ),

                        html.Div("Stage", style=FIELD_LABEL_SPACED_STYLE),
                        dcc.RadioItems(
                            id="stage-filter",
                            options=[
                                {"label": " All", "value": "All"},
                                {"label": " Stage 1-3", "value": "Stage 1-3"},
                                {"label": " Stage 4", "value": "Stage 4"},
                            ],
                            value="All",
                            inline=True,
                            style=OPTION_TEXT_STYLE,
                        ),
                    ],
                ),

                html.Div(
                    style={**section_style(), "marginBottom": "12px"},
                    children=[
                        section_title("Cancer type selection"),

                        html.Div(
                            style={
                                "display": "flex",
                                "gap": "8px",
                                "marginBottom": "10px",
                            },
                            children=[
                                html.Button(
                                    "Select all",
                                    id="select-all-cancers-btn",
                                    n_clicks=0,
                                    style={
                                        "flex": "1",
                                        "padding": "7px 8px",
                                        "borderRadius": "10px",
                                        "border": "1px solid #bbbbbb",
                                        "background": "#ffffff",
                                        "cursor": "pointer",
                                        "fontWeight": "650",
                                        "fontSize": "12px",
                                    },
                                ),
                                html.Button(
                                    "Deselect all",
                                    id="deselect-all-cancers-btn",
                                    n_clicks=0,
                                    style={
                                        "flex": "1",
                                        "padding": "7px 8px",
                                        "borderRadius": "10px",
                                        "border": "1px solid #bbbbbb",
                                        "background": "#ffffff",
                                        "cursor": "pointer",
                                        "fontWeight": "650",
                                        "fontSize": "12px",
                                    },
                                ),
                            ],
                        ),

                        html.Div(
                            style={
                                "display": "flex",
                                "flexDirection": "column",
                                "gap": "8px",
                            },
                            children=[
                                html.Button(
                                    [
                                        html.Span(
                                            style={
                                                "display": "inline-block",
                                                "width": "10px",
                                                "height": "10px",
                                                "borderRadius": "50%",
                                                "backgroundColor": CANCER_COLOR_MAP.get(
                                                    cancer,
                                                    CANCER_COLOR_MAP["Other"],
                                                ),
                                                "border": "1px solid rgba(0,0,0,0.12)",
                                            }
                                        ),
                                        html.Span(cancer),
                                    ],
                                    id={
                                        "type": "cancer-filter-btn",
                                        "index": cancer,
                                    },
                                    n_clicks=0,
                                    style=cancer_button_style(cancer, True),
                                )
                                for cancer in ALL_CANCERS
                            ],
                        ),

                        html.Div(
                            style={
                                "marginTop": "14px",
                                "paddingTop": "12px",
                                "borderTop": "1px solid #eeeeee",
                            },
                            children=[
                                html.Div(
                                    "Histology / OncoTree code",
                                    style=FIELD_LABEL_SPACED_STYLE,
                                ),
                                dcc.Checklist(
                                    id="oncotree-mode",
                                    options=[
                                        {
                                            "label": " View selected cancer by histology codes",
                                            "value": "on",
                                            "disabled": True,
                                        }
                                    ],
                                    value=[],
                                    inline=False,
                                    style={"fontSize": "13px"},
                                ),
                                html.Div(
                                    id="oncotree-mode-help",
                                    style=HELP_TEXT_STYLE,
                                ),
                                html.Div(
                                    id="oncotree-detail-panel",
                                    style={"display": "none"},
                                    children=[
                                        html.Div(
                                            "Minimum visible histology count",
                                            style={
                                                "fontWeight": "600",
                                                "marginTop": "14px",
                                                "marginBottom": "4px",
                                            },
                                        ),
                                        dcc.Slider(
                                            id="oncotree-min-count",
                                            min=1,
                                            max=200,
                                            step=1,
                                            value=10,
                                            marks={
                                                1: "1",
                                                25: "25",
                                                50: "50",
                                                100: "100",
                                                200: "200",
                                            },
                                            tooltip={
                                                "placement": "bottom",
                                                "always_visible": False,
                                            },
                                        ),
                                        html.Div(
                                            "Visible histologies",
                                            style={
                                                "fontWeight": "600",
                                                "marginTop": "14px",
                                                "marginBottom": "6px",
                                            },
                                        ),
                                        html.Div(
                                            style={
                                                "display": "flex",
                                                "gap": "8px",
                                                "marginBottom": "8px",
                                            },
                                            children=[
                                                html.Button(
                                                    "Select all",
                                                    id="select-all-oncotree-btn",
                                                    n_clicks=0,
                                                    style={
                                                        "flex": "1",
                                                        "padding": "6px 8px",
                                                        "borderRadius": "9px",
                                                        "border": "1px solid #bbbbbb",
                                                        "background": "#ffffff",
                                                        "cursor": "pointer",
                                                        "fontWeight": "650",
                                                        "fontSize": "12px",
                                                    },
                                                ),
                                                html.Button(
                                                    "Deselect all",
                                                    id="deselect-all-oncotree-btn",
                                                    n_clicks=0,
                                                    style={
                                                        "flex": "1",
                                                        "padding": "6px 8px",
                                                        "borderRadius": "9px",
                                                        "border": "1px solid #bbbbbb",
                                                        "background": "#ffffff",
                                                        "cursor": "pointer",
                                                        "fontWeight": "650",
                                                        "fontSize": "12px",
                                                    },
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            style={
                                                "maxHeight": "170px",
                                                "overflowY": "auto",
                                                "paddingRight": "4px",
                                            },
                                            children=[
                                                dcc.Checklist(
                                                    id="oncotree-code-filter",
                                                    options=[],
                                                    value=[],
                                                    inline=False,
                                                    style={
                                                        "fontSize": "12px",
                                                        "lineHeight": "1.45",
                                                    },
                                                    inputStyle={
                                                        "marginRight": "6px"
                                                    },
                                                )
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),

                html.Div(
                    style={**section_style(), "marginBottom": "12px"},
                    children=[
                        section_title("Chart controls"),

                        html.Div("Metastasi min", style=FIELD_LABEL_STYLE),
                        dcc.Slider(
                            id="meta-threshold",
                            min=1,
                            max=350,
                            step=10,
                            value=100,
                            marks={i: str(i) for i in range(50, 351, 100)},
                            tooltip={
                                "placement": "bottom",
                                "always_visible": False,
                            },
                        ),

                        html.Div("Age bins", style=FIELD_LABEL_SPACED_STYLE),
                        dcc.Slider(
                            id="age-bin-slider",
                            min=4,
                            max=10,
                            step=1,
                            value=6,
                            marks={i: str(i) for i in range(4, 11)},
                            tooltip={
                                "placement": "bottom",
                                "always_visible": False,
                            },
                        ),
                    ],
                ),

                html.Button(
                    "Reset all",
                    id="reset-all-btn",
                    n_clicks=0,
                    style={
                        "width": "100%",
                        "height": "42px",
                        "padding": "0 16px",
                        "borderRadius": "12px",
                        "border": "1px solid #bbbbbb",
                        "background": "#ffffff",
                        "cursor": "pointer",
                        "fontWeight": "700",
                        "boxShadow": "0 1px 4px rgba(0,0,0,0.06)",
                    },
                ),
            ],
        ),

        # =========================
        # SCROLLABLE CONTENT
        # =========================
        html.Div(
            style={
                "flex": "1 1 auto",
                "height": "100vh",
                "overflowY": "auto",
                "boxSizing": "border-box",
                "padding": "16px 18px 30px 18px",
            },
            children=[
                html.Div(
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "16px",
                        "maxWidth": "1550px",
                        "margin": "0 auto",
                    },
                    children=[
                        html.Div(
                            id="sankey-card",
                            style=chart_card_style(600),
                            children=[
                                chart_header(
                                    "Weighted bipartite flow diagram: Cancer type/Histology to Metastatic site"
                                ),
                                dcc.Graph(
                                    id="sankey-chart",
                                    style={
                                        "height": "100%",
                                        "width": "100%",
                                        "flex": "1 1 auto",
                                    },
                                    config=graph_config(),
                                ),
                            ],
                        ),
                        html.Div(
                            id="death-age-card",
                            style=chart_card_style(560),
                            children=[
                                chart_header(
                                    "Deaths by Age bin and Cancer type/Histology"
                                ),
                                dcc.Graph(
                                    id="death-age-chart",
                                    style={
                                        "height": "100%",
                                        "width": "100%",
                                        "flex": "1 1 auto",
                                    },
                                    config=graph_config(),
                                ),
                            ],
                        ),
                        html.Div(
                            id="survival-km-card",
                            style=chart_card_style(620),
                            children=[
                                chart_header(
                                    "Kaplan-Meier survival curve by Cancer type/Histology"
                                ),
                                dcc.Graph(
                                    id="survival-km-chart",
                                    style={
                                        "height": "100%",
                                        "width": "100%",
                                        "flex": "1 1 auto",
                                    },
                                    config=graph_config(),
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),

        dcc.Store(id="selected-cancers-store", data=ALL_CANCERS),
        dcc.Store(id="active-selection", data=None),
    ],
)


# =========================
# CALLBACKS: LAYOUT SIZE
# =========================

@app.callback(
    Output("sankey-card", "style"),
    Output("death-age-card", "style"),
    Output("survival-km-card", "style"),
    Input("gender-filter", "value"),
    Input("sample-type-filter", "value"),
    Input("stage-filter", "value"),
    Input("meta-threshold", "value"),
    Input("selected-cancers-store", "data"),
    Input("oncotree-mode", "value"),
    Input("oncotree-code-filter", "value"),
    Input("oncotree-min-count", "value"),
)
def update_chart_card_sizes(
    gender,
    sample_type,
    stage_filter,
    threshold,
    selected_cancers,
    oncotree_mode,
    oncotree_codes,
    oncotree_min_count,
):
    scale = CHART_SIZE_SCALE

    sankey_height = compute_sankey_card_height(
        gender,
        threshold,
        selected_cancers,
        oncotree_mode,
        oncotree_codes,
        oncotree_min_count,
        scale,
        SANKEY_ZOOM_SCALE,
        sample_type=sample_type,
        stage_filter=stage_filter,
    )

    return (
        chart_card_style(sankey_height),
        chart_card_style(560 * scale),
        chart_card_style(620 * scale),
    )


# =========================
# CALLBACKS: FILTERS
# =========================

@app.callback(
    Output("selected-cancers-store", "data"),
    Output({"type": "cancer-filter-btn", "index": ALL}, "style"),
    Input({"type": "cancer-filter-btn", "index": ALL}, "n_clicks"),
    Input("select-all-cancers-btn", "n_clicks"),
    Input("deselect-all-cancers-btn", "n_clicks"),
    Input("reset-all-btn", "n_clicks"),
    State("selected-cancers-store", "data"),
    prevent_initial_call=True,
)
def update_cancer_filters(
    _,
    select_all_clicks,
    deselect_all_clicks,
    reset_all_clicks,
    current_selected,
):
    triggered = callback_context.triggered_id

    selected = ALL_CANCERS.copy() if current_selected is None else list(current_selected)

    if triggered == "reset-all-btn" or triggered == "select-all-cancers-btn":
        selected = ALL_CANCERS.copy()

    elif triggered == "deselect-all-cancers-btn":
        selected = []

    elif isinstance(triggered, dict) and triggered.get("type") == "cancer-filter-btn":
        cancer = triggered.get("index")

        if cancer in selected:
            selected = [item for item in selected if item != cancer]
        else:
            selected = selected + [cancer]

    styles = [
        cancer_button_style(cancer, cancer in selected)
        for cancer in ALL_CANCERS
    ]

    return selected, styles


@app.callback(
    Output("oncotree-mode", "options"),
    Output("oncotree-mode", "value"),
    Output("oncotree-mode-help", "children"),
    Input("selected-cancers-store", "data"),
    State("oncotree-mode", "value"),
)
def update_oncotree_toggle(selected_cancers, current_mode):
    single_cancer_active = is_single_cancer(selected_cancers)
    current_mode = current_mode or []

    option = {
        "label": " View selected cancer by histology codes",
        "value": "on",
        "disabled": not single_cancer_active,
    }

    if not single_cancer_active:
        return (
            [option],
            [],
            "Disabled: select exactly one cancer type to activate histology-code controls.",
        )

    cancer = selected_cancers[0]

    help_text = (
        f"Active for {cancer}: turn this on to split the charts by histology/OncoTree code. "
        f"The code controls appear below when this is enabled."
    )

    return [option], current_mode, help_text


@app.callback(
    Output("oncotree-detail-panel", "style"),
    Output("oncotree-min-count", "max"),
    Output("oncotree-min-count", "marks"),
    Output("oncotree-min-count", "value"),
    Output("oncotree-min-count", "disabled"),
    Output("oncotree-code-filter", "options"),
    Output("oncotree-code-filter", "value"),
    Input("selected-cancers-store", "data"),
    Input("gender-filter", "value"),
    Input("sample-type-filter", "value"),
    Input("stage-filter", "value"),
    Input("oncotree-min-count", "value"),
    Input("oncotree-mode", "value"),
    Input("select-all-oncotree-btn", "n_clicks"),
    Input("deselect-all-oncotree-btn", "n_clicks"),
    State("oncotree-code-filter", "value"),
)
def update_oncotree_code_controls(
    selected_cancers,
    gender,
    sample_type,
    stage_filter,
    min_count,
    oncotree_mode,
    select_all_clicks,
    deselect_all_clicks,
    current_codes,
):
    triggered = callback_context.triggered_id
    current_codes = current_codes if current_codes is not None else None
    mode_active = is_oncotree_mode(selected_cancers, oncotree_mode)

    if not is_single_cancer(selected_cancers):
        return (
            {"display": "none"},
            200,
            {1: "1", 25: "25", 50: "50", 100: "100", 200: "200"},
            int(min_count or 10),
            True,
            [],
            [],
        )

    cancer = selected_cancers[0]

    df = filter_by_gender(DF, gender)
    df = filter_by_sample_type(df, sample_type)
    df = filter_by_stage(df, stage_filter)
    df = df[df["CANCER_TYPE"] == cancer].copy()

    counts = get_oncotree_counts(df)

    max_count = max([count for _, count in counts], default=1)
    slider_max = max(1, int(max_count))
    safe_min = max(1, min(int(min_count or 10), slider_max))

    marks = {
        1: "1",
        slider_max: str(slider_max),
    }

    for candidate in [10, 25, 50, 100, 200, 300]:
        if 1 < candidate < slider_max:
            marks[candidate] = str(candidate)

    visible_counts = [
        (code, count)
        for code, count in counts
        if count >= safe_min
    ]

    options = [
        {
            "label": f" {code} ({count})",
            "value": code,
        }
        for code, count in visible_counts
    ]

    visible_codes = [code for code, _ in visible_counts]
    current_codes_list = current_codes or []

    if triggered == "deselect-all-oncotree-btn":
        selected_visible = []

    elif triggered in {"select-all-oncotree-btn", "oncotree-mode"}:
        selected_visible = visible_codes

    else:
        selected_visible = [
            code
            for code in current_codes_list
            if code in visible_codes
        ]

        if current_codes is None:
            selected_visible = visible_codes

    panel_style = {
        "display": "block" if mode_active else "none",
        "marginTop": "2px",
    }

    return (
        panel_style,
        slider_max,
        marks,
        safe_min,
        not mode_active,
        options,
        selected_visible if mode_active else [],
    )


# =========================
# CALLBACKS: SELECTIONS
# =========================

def _normalize_sankey_customdata(custom):
    """
    Restituisce [kind, label] dal customdata del click sul Sankey.
    """
    if custom is None:
        return None

    if isinstance(custom, (list, tuple)):
        if len(custom) >= 2 and str(custom[0]) in {"cancer", "meta", "link"}:
            return [
                str(custom[0]),
                str(custom[1]) if len(custom) > 1 else "",
            ]

        if len(custom) == 1:
            return _normalize_sankey_customdata(custom[0])

        return None

    custom = str(custom)
    parts = custom.split("|")

    if len(parts) >= 2 and parts[0] in {"cancer", "meta", "link"}:
        return [parts[0], parts[1]]

    return None


def _customdata_from_sankey_click(point, figure):
    """
    Identifica in modo robusto se il click sul Sankey è su nodo o link.
    I link vengono ignorati perché non devono guidare la selezione.
    """
    if not point:
        return None

    if point.get("source") is not None or point.get("target") is not None:
        return ["link", ""]

    custom = _normalize_sankey_customdata(point.get("customdata"))

    if custom:
        return custom

    if not figure:
        return None

    try:
        sankey_trace = figure["data"][0]
        node = sankey_trace.get("node", {})
        labels = [str(value) for value in node.get("label", [])]
        node_customdata = node.get("customdata", [])
    except Exception:
        return None

    clicked_label = point.get("label") or point.get("text")

    if clicked_label is not None:
        clicked_label = str(clicked_label)

        if clicked_label in labels:
            idx = labels.index(clicked_label)

            if idx < len(node_customdata):
                custom = _normalize_sankey_customdata(node_customdata[idx])

                if custom:
                    return custom

            left_count = int(sankey_trace.get("meta", {}).get("left_count", 0) or 0)
            kind = "cancer" if idx < left_count else "meta"

            return [kind, clicked_label]

    point_number = point.get("pointNumber", point.get("pointIndex"))

    if point_number is None:
        return None

    try:
        idx = int(point_number)
    except Exception:
        return None

    if 0 <= idx < len(labels):
        if idx < len(node_customdata):
            custom = _normalize_sankey_customdata(node_customdata[idx])

            if custom:
                return custom

        left_count = int(sankey_trace.get("meta", {}).get("left_count", 0) or 0)
        kind = "cancer" if idx < left_count else "meta"

        return [kind, labels[idx]]

    return None


def _same_selection_target(a, b):
    if not a or not b:
        return False

    return (
        a.get("type") == b.get("type")
        and str(a.get("label")) == str(b.get("label"))
    )


@app.callback(
    Output("active-selection", "data"),
    Output("sankey-chart", "clickData"),
    Input("sankey-chart", "clickData"),
    Input("death-age-chart", "clickData"),
    Input("survival-km-chart", "clickData"),
    Input("reset-all-btn", "n_clicks"),
    State("active-selection", "data"),
    State("sankey-chart", "figure"),
    prevent_initial_call=True,
)
def update_active_selection(
    sankey_click,
    bar_click,
    km_click,
    reset_clicks,
    current_selection,
    sankey_figure,
):
    triggered = callback_context.triggered_id

    if triggered == "reset-all-btn":
        return None, None

    selected = None
    reset_sankey_click = no_update

    if triggered == "sankey-chart":
        if not sankey_click:
            return current_selection, no_update

        point = sankey_click["points"][0]
        custom = _customdata_from_sankey_click(point, sankey_figure)

        if not custom:
            return current_selection, None

        if custom[0] == "link":
            return current_selection, None

        if custom[0] in {"cancer", "meta"} and len(custom) >= 2:
            selected = {
                "source": "sankey",
                "type": custom[0],
                "label": custom[1],
            }

            reset_sankey_click = None

    elif triggered == "death-age-chart":
        if not bar_click:
            return current_selection, no_update

        point = bar_click["points"][0]
        custom = point.get("customdata")

        if not custom:
            return current_selection, no_update

        selected = {
            "source": "bar",
            "type": "cancer",
            "label": custom[1],
            "age_bin": custom[0],
        }

    elif triggered == "survival-km-chart":
        if not km_click:
            return current_selection, no_update

        point = km_click["points"][0]
        custom = point.get("customdata")

        if not custom:
            return current_selection, no_update

        selected = {
            "source": "km",
            "type": "cancer",
            "label": custom[0],
            "time": custom[1],
        }

    if not selected:
        return current_selection, reset_sankey_click

    if _same_selection_target(current_selection, selected):
        return None, reset_sankey_click

    return selected, reset_sankey_click


@app.callback(
    Output("highlighted-cancer-label", "children"),
    Input("active-selection", "data"),
    Input("gender-filter", "value"),
    Input("sample-type-filter", "value"),
    Input("stage-filter", "value"),
    Input("meta-threshold", "value"),
    Input("selected-cancers-store", "data"),
    Input("oncotree-mode", "value"),
    Input("oncotree-code-filter", "value"),
    Input("oncotree-min-count", "value"),
)
def update_highlight_label(
    active_selection,
    gender,
    sample_type,
    stage_filter,
    threshold,
    selected_cancers,
    oncotree_mode,
    oncotree_codes,
    oncotree_min_count,
):
    if not active_selection:
        return "Highlight: none"

    df = get_filtered_df(
        DF,
        gender,
        selected_cancers,
        oncotree_mode,
        oncotree_codes,
        oncotree_min_count,
        sample_type,
        stage_filter,
    )

    group_col = get_group_col(selected_cancers, oncotree_mode)
    groups = get_highlight_groups(df, group_col, active_selection, threshold)

    if active_selection.get("type") == "meta":
        if groups:
            return (
                f"Highlighted metastasis: {active_selection.get('label')} "
                f"→ {len(groups)} connected groups"
            )

        return f"Highlighted metastasis: {active_selection.get('label')}"

    label = active_selection.get("label")

    if active_selection.get("source") == "bar" and active_selection.get("age_bin"):
        return f"Highlighted group: {label} | age bin {active_selection.get('age_bin')}"

    return f"Highlighted group: {label}"


# =========================
# CALLBACKS: FIGURES
# =========================

@app.callback(
    Output("sankey-chart", "figure"),
    Input("gender-filter", "value"),
    Input("sample-type-filter", "value"),
    Input("stage-filter", "value"),
    Input("meta-threshold", "value"),
    Input("active-selection", "data"),
    Input("selected-cancers-store", "data"),
    Input("oncotree-mode", "value"),
    Input("oncotree-code-filter", "value"),
    Input("oncotree-min-count", "value"),
)
def update_sankey(
    gender,
    sample_type,
    stage_filter,
    threshold,
    active_selection,
    selected_cancers,
    oncotree_mode,
    oncotree_codes,
    oncotree_min_count,
):
    df = get_filtered_df(
        DF,
        gender,
        selected_cancers,
        oncotree_mode,
        oncotree_codes,
        oncotree_min_count,
        sample_type,
        stage_filter,
    )

    group_col = get_group_col(selected_cancers, oncotree_mode)
    group_label = get_group_label(selected_cancers, oncotree_mode)

    edges = build_edge_table(df, group_col=group_col)
    edges, effective_threshold, threshold_fallback = safe_filter_metastasis_edges(
        edges,
        threshold,
    )

    scale = CHART_SIZE_SCALE
    title = f"{group_label} to Metastatic Site"

    sankey_height = compute_sankey_card_height(
        gender,
        threshold,
        selected_cancers,
        oncotree_mode,
        oncotree_codes,
        oncotree_min_count,
        scale,
        SANKEY_ZOOM_SCALE,
        sample_type=sample_type,
        stage_filter=stage_filter,
    )

    figure_height = max(420, int(sankey_height - 62))

    return make_sankey_figure(
        edges,
        selected_node=active_selection,
        meta_threshold=effective_threshold,
        left_label=group_label,
        title=title,
        figure_height=figure_height,
        threshold_fallback=threshold_fallback,
        original_meta_threshold=threshold,
    )


@app.callback(
    Output("death-age-chart", "figure"),
    Input("gender-filter", "value"),
    Input("sample-type-filter", "value"),
    Input("stage-filter", "value"),
    Input("age-bin-slider", "value"),
    Input("active-selection", "data"),
    Input("selected-cancers-store", "data"),
    Input("oncotree-mode", "value"),
    Input("oncotree-code-filter", "value"),
    Input("oncotree-min-count", "value"),
    Input("meta-threshold", "value"),
)
def update_bar(
    gender,
    sample_type,
    stage_filter,
    bins,
    active_selection,
    selected_cancers,
    oncotree_mode,
    oncotree_codes,
    oncotree_min_count,
    threshold,
):
    df = get_filtered_df(
        DF,
        gender,
        selected_cancers,
        oncotree_mode,
        oncotree_codes,
        oncotree_min_count,
        sample_type,
        stage_filter,
    )

    group_col = get_group_col(selected_cancers, oncotree_mode)
    group_label = get_group_label(selected_cancers, oncotree_mode)

    highlighted_groups = get_highlight_groups(
        df,
        group_col,
        active_selection,
        threshold,
    )

    selected_bar = (
        active_selection
        if active_selection and active_selection.get("source") == "bar"
        else None
    )

    return make_death_age_bars_figure(
        df=df,
        n_bins=bins,
        selected_bar=selected_bar,
        mode="count",
        highlighted_cancer=highlighted_groups,
        selected_node=active_selection,
        group_col=group_col,
        group_label=group_label,
        title="",
    )


@app.callback(
    Output("survival-km-chart", "figure"),
    Input("gender-filter", "value"),
    Input("sample-type-filter", "value"),
    Input("stage-filter", "value"),
    Input("selected-cancers-store", "data"),
    Input("active-selection", "data"),
    Input("oncotree-mode", "value"),
    Input("oncotree-code-filter", "value"),
    Input("oncotree-min-count", "value"),
    Input("meta-threshold", "value"),
)
def update_survival_km(
    gender,
    sample_type,
    stage_filter,
    selected_cancers,
    active_selection,
    oncotree_mode,
    oncotree_codes,
    oncotree_min_count,
    threshold,
):
    df = get_filtered_df(
        DF,
        gender,
        selected_cancers,
        oncotree_mode,
        oncotree_codes,
        oncotree_min_count,
        sample_type,
        stage_filter,
    )

    group_col = get_group_col(selected_cancers, oncotree_mode)
    group_label = get_group_label(selected_cancers, oncotree_mode)

    highlighted_groups = get_highlight_groups(
        df,
        group_col,
        active_selection,
        threshold,
    )

    return make_survival_km_figure(
        df=df,
        group_col=group_col,
        top_n_groups=None,
        include_other=False,
        selected_group=highlighted_groups,
        title="",
    )


if __name__ == "__main__":
    app.run(debug=True)