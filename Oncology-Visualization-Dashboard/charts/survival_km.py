import pandas as pd
import plotly.graph_objects as go

from .colors import get_group_color, make_color_map, hex_to_rgba

def normalize_highlight_groups(value):
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(v) for v in value if v is not None}
    return {str(value)}


def _safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def _normalize_os_status(value):
    """
    Converte OS_STATUS in evento binario:
    - 1 = decesso
    - 0 = censored / living
    """
    if pd.isna(value):
        return None

    v = str(value).strip().upper()

    if "DECEASED" in v or v == "1":
        return 1

    if "LIVING" in v or "ALIVE" in v or v == "0":
        return 0

    return None


def prepare_survival_data(
        df,
        patient_ids=None,
        group_col="CANCER_TYPE",
        top_n_groups=6,
        include_other=True
):
    needed_cols = ["PATIENT_ID", "OS_MONTHS", "OS_STATUS", group_col]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        return pd.DataFrame(), f"Colonne mancanti: {missing}"

    data = df[needed_cols].copy()

    if patient_ids is not None:
        data = data[data["PATIENT_ID"].isin(patient_ids)].copy()

    data["OS_MONTHS"] = _safe_numeric(data["OS_MONTHS"])
    data["event"] = data["OS_STATUS"].apply(_normalize_os_status)
    data[group_col] = data[group_col].astype(str).str.strip()

    bad = {"", "nan", "NaN", "None", "Unknown"} # , "Not Applicable"

    data = data[
        data["PATIENT_ID"].notna() &
        data["OS_MONTHS"].notna() &
        (data["OS_MONTHS"] >= 0) &
        data["event"].notna() &
        ~data[group_col].isin(bad)
        ].copy()

    if data.empty:
        return pd.DataFrame(), "Nessun dato survival disponibile con i filtri selezionati"

    data = data.drop_duplicates(subset=["PATIENT_ID"]).copy()

    top_groups = (
        data[group_col]
        .value_counts()
        .head(top_n_groups)
        .index
        .tolist()
    )

    if include_other:
        data["group"] = data[group_col].apply(
            lambda x: x if x in top_groups else "Other"
        )
    else:
        data = data[data[group_col].isin(top_groups)].copy()
        data["group"] = data[group_col]

    data = data.rename(columns={"OS_MONTHS": "time"})

    return data[["PATIENT_ID", "time", "event", "group"]].copy(), None


def compute_km_curve(group_df):
    """
    Calcola manualmente la curva di Kaplan-Meier per un gruppo.

    Restituisce dataframe con:
    - time
    - survival
    - n_risk
    - n_events
    """
    if group_df.empty:
        return pd.DataFrame(columns=["time", "survival", "n_risk", "n_events"])

    d = group_df[["time", "event"]].copy()
    d["time"] = _safe_numeric(d["time"])
    d["event"] = _safe_numeric(d["event"])

    d = d.dropna(subset=["time", "event"]).sort_values("time")

    if d.empty:
        return pd.DataFrame(columns=["time", "survival", "n_risk", "n_events"])

    event_times = sorted(d.loc[d["event"] == 1, "time"].unique().tolist())

    km_rows = [{
        "time": 0.0,
        "survival": 1.0,
        "n_risk": len(d),
        "n_events": 0
    }]

    survival = 1.0

    for t in event_times:
        n_risk = int((d["time"] >= t).sum())
        n_events = int(((d["time"] == t) & (d["event"] == 1)).sum())

        if n_risk > 0:
            survival *= (1 - n_events / n_risk)

        km_rows.append({
            "time": float(t),
            "survival": float(survival),
            "n_risk": n_risk,
            "n_events": n_events
        })

    return pd.DataFrame(km_rows)


def make_survival_km_figure(
        df,
        patient_ids=None,
        group_col="CANCER_TYPE",
        top_n_groups=6,
        include_other=True,
        selected_group=None,
        selected_point=None,
        title="Kaplan-Meier Survival Curve"
):
    survival_df, error_message = prepare_survival_data(
        df=df,
        patient_ids=patient_ids,
        group_col=group_col,
        top_n_groups=top_n_groups,
        include_other=include_other
    )

    if survival_df.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            title=title,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text=error_message or "Nessun dato disponibile",
                    showarrow=False,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    font=dict(size=16)
                )
            ]
        )
        return fig

    fig = go.Figure()

    group_order = (
        survival_df["group"]
        .value_counts()
        .index
        .tolist()
    )
    group_color_map = make_color_map(group_order)

    selected_groups = normalize_highlight_groups(selected_group)

    for group_name in group_order:
        sub = survival_df[survival_df["group"] == group_name].copy()
        km = compute_km_curve(sub)

        if km.empty:
            continue

        customdata = [
            [group_name, float(t), int(n_risk), int(n_events)]
            for t, n_risk, n_events in zip(km["time"], km["n_risk"], km["n_events"])
        ]

        base_color = get_group_color(group_name, group_color_map)
        faded_color = hex_to_rgba(base_color, 0.10)

        is_group_selected = bool(selected_groups) and group_name in selected_groups

        if not selected_groups:
            line_width = 3
            line_color = base_color
            default_marker_color = base_color
            default_marker_size = 7
        else:
            if is_group_selected:
                line_width = 4.8
                line_color = base_color
                default_marker_color = base_color
                default_marker_size = 8
            else:
                line_width = 2
                line_color = faded_color
                default_marker_color = faded_color
                default_marker_size = 5

        marker_sizes = [default_marker_size] * len(km)
        marker_colors = [default_marker_color] * len(km)
        marker_line_widths = [0] * len(km)
        marker_line_colors = ["rgba(0,0,0,0)"] * len(km)
        fig.add_trace(
            go.Scatter(
                x=km["time"],
                y=km["survival"],
                mode="lines",
                showlegend=False,
                hoverinfo="skip",
                line=dict(
                    shape="hv",
                    width=line_width + 3.2,
                    color="black"
                ),
                opacity=1.0 if is_group_selected else 0.0
            )
        )
        fig.add_trace(
            go.Scatter(
                x=km["time"],
                y=km["survival"],
                mode="lines+markers",
                name=group_name,
                customdata=customdata,
                line=dict(
                    shape="hv",
                    width=line_width,
                    color=line_color
                ),
                marker=dict(
                    size=marker_sizes,
                    color=marker_colors,
                    line=dict(
                        width=marker_line_widths,
                        color=marker_line_colors,
                    )
                ),
                hovertemplate=(
                    "<b>Group:</b> %{customdata[0]}<br>"
                    "<b>Time (months):</b> %{customdata[1]:.1f}<br>"
                    "<b>Survival:</b> %{y:.3f}<br>"
                    "<b>At risk:</b> %{customdata[2]}<br>"
                    "<b>Events at time:</b> %{customdata[3]}<extra></extra>"
                )
            )
        )

    fig.update_layout(
        template="plotly_white",
        title=title,
        xaxis_title="Overall survival (months)",
        yaxis_title="Survival probability",
        showlegend=False,
        margin=dict(l=60, r=30, t=70, b=70),
        clickmode="event",
        dragmode="pan",
        uirevision="survival-km-static"
    )

    fig.update_yaxes(
        range=[0, 1.02],
        fixedrange=True
    )

    fig.update_xaxes(
        fixedrange=False
    )

    return fig