import pandas as pd
import plotly.graph_objects as go

from .colors import get_group_color, make_color_map


def normalize_highlight_groups(value):
    if value is None:
        return set()

    if isinstance(value, (list, tuple, set)):
        return {str(v) for v in value if v is not None}

    return {str(value)}


def prepare_death_age_data(
    df,
    age_col="CURRENT_AGE_DEID",
    status_col="OS_STATUS",
    cancer_col="CANCER_TYPE",
    n_bins=6,
    top_n_cancers=999,
    custom_bins=None,
):
    needed_cols = ["PATIENT_ID", age_col, status_col, cancer_col]
    missing = [col for col in needed_cols if col not in df.columns]

    if missing:
        return pd.DataFrame(), f"Colonne mancanti: {missing}"

    data = df[needed_cols].copy()

    data[age_col] = pd.to_numeric(data[age_col], errors="coerce")
    data[status_col] = data[status_col].astype(str).str.strip()
    data[cancer_col] = data[cancer_col].astype(str).str.strip()

    bad = {"", "nan", "NaN", "None", "Unknown"}

    data = data[
        data["PATIENT_ID"].notna()
        & data[age_col].notna()
        & ~data[cancer_col].isin(bad)
        & data[status_col].notna()
    ].copy()

    data = data[
        data[status_col].str.contains("DECEASED", case=False, na=False)
    ].copy()

    if data.empty:
        return (
            pd.DataFrame(),
            "Nessun paziente deceduto disponibile con i filtri selezionati",
        )

    data = data.drop_duplicates(subset=["PATIENT_ID"]).copy()

    top_cancers = (
        data[cancer_col]
        .value_counts()
        .head(top_n_cancers)
        .index
        .tolist()
    )

    data[cancer_col] = data[cancer_col].apply(
        lambda value: value if value in top_cancers else "Other"
    )

    if custom_bins is not None and len(custom_bins) >= 2:
        bins = custom_bins
    else:
        age_min = int(data[age_col].min())
        age_max = int(data[age_col].max())

        if age_min == age_max:
            bins = [age_min - 1, age_min + 1]
        else:
            bins = n_bins

    data["AGE_BIN"] = pd.cut(
        data[age_col],
        bins=bins,
        include_lowest=True,
    )

    data["AGE_BIN_LABEL"] = data["AGE_BIN"].astype(str)

    grouped = (
        data.groupby(["AGE_BIN_LABEL", cancer_col], as_index=False)
        .size()
        .rename(columns={"size": "death_count", cancer_col: "CANCER_TYPE"})
    )

    bin_order = (
        data[["AGE_BIN", "AGE_BIN_LABEL"]]
        .drop_duplicates()
        .sort_values("AGE_BIN")
    )["AGE_BIN_LABEL"].tolist()

    grouped["AGE_BIN_LABEL"] = pd.Categorical(
        grouped["AGE_BIN_LABEL"],
        categories=bin_order,
        ordered=True,
    )

    grouped = grouped.sort_values(
        ["AGE_BIN_LABEL", "death_count"],
        ascending=[True, False],
    )

    return grouped, None


def make_death_age_bars_figure(
    df,
    n_bins=6,
    top_n_cancers=999,
    custom_bins=None,
    selected_bar=None,
    mode="count",
    selected_cancers=None,
    highlighted_cancer=None,
    selected_node=None,
    group_col="CANCER_TYPE",
    group_label="Cancer type",
    title="Deaths by Age Bin and Cancer Type",
):
    grouped, error_message = prepare_death_age_data(
        df=df,
        cancer_col=group_col,
        n_bins=n_bins,
        top_n_cancers=top_n_cancers,
        custom_bins=custom_bins,
    )

    if grouped.empty:
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
                    font=dict(size=16),
                )
            ],
        )

        return fig

    if mode == "percentage":
        total_per_bin = (
            grouped.groupby("AGE_BIN_LABEL", as_index=False)["death_count"]
            .sum()
            .rename(columns={"death_count": "bin_total"})
        )

        grouped = grouped.merge(total_per_bin, on="AGE_BIN_LABEL", how="left")
        grouped["death_count"] = 100 * grouped["death_count"] / grouped["bin_total"]

    fig = go.Figure()

    cancer_order = (
        grouped.groupby("CANCER_TYPE", as_index=False)["death_count"]
        .sum()
        .sort_values("death_count", ascending=False)["CANCER_TYPE"]
        .tolist()
    )

    group_color_map = make_color_map(cancer_order)

    age_order = grouped["AGE_BIN_LABEL"].cat.categories.tolist()

    selected_age_bin = None
    selected_cancer_type = None

    if selected_bar and isinstance(selected_bar, dict):
        selected_age_bin = selected_bar.get("age_bin")
        selected_cancer_type = selected_bar.get("cancer_type") or selected_bar.get("label")

    highlight_groups = normalize_highlight_groups(highlighted_cancer)

    selected_node_type = None

    if selected_node and isinstance(selected_node, dict):
        selected_node_type = selected_node.get("type")

    # Se sto cliccando una metastasi dal bipartite,
    # non voglio che il vecchio selected_bar continui a dominare il chart.
    ignore_selected_bar = selected_node_type == "meta"

    external_highlight_active = (
        bool(highlight_groups)
        and selected_cancer_type not in highlight_groups
    )

    # Altezza minima visiva per rendere hover/click più accessibili
    # anche sulle barre grouped molto basse.
    max_value = grouped["death_count"].max()
    min_visible_height = max_value * 0.015 if max_value > 0 else 0

    for cancer in cancer_order:
        sub = grouped[grouped["CANCER_TYPE"] == cancer].copy()

        sub = (
            pd.DataFrame({"AGE_BIN_LABEL": age_order})
            .merge(sub, on="AGE_BIN_LABEL", how="left")
        )

        sub["CANCER_TYPE"] = sub["CANCER_TYPE"].fillna(cancer)
        sub["death_count"] = sub["death_count"].fillna(0)

        # Valore usato solo per disegnare la barra.
        # Il valore reale resta death_count e viene mostrato nel tooltip.
        sub["display_death_count"] = sub["death_count"]

        sub.loc[
            (sub["death_count"] > 0)
            & (sub["death_count"] < min_visible_height),
            "display_death_count",
        ] = min_visible_height

        customdata = [
            [age_bin, cancer, real_value]
            for age_bin, real_value in zip(
                sub["AGE_BIN_LABEL"],
                sub["death_count"],
            )
        ]

        # =========================
        # LOGICA OPACITA'
        # =========================

        if selected_bar is not None and not ignore_selected_bar and not external_highlight_active:
            trace_opacity = 1.0 if cancer == selected_cancer_type else 0.08

        elif highlight_groups:
            trace_opacity = 1.0 if cancer in highlight_groups else 0.08

        else:
            trace_opacity = 1.0

        # =========================
        # BORDO BARRA CLICCATA
        # =========================

        line_widths = []
        line_colors = []

        for age_bin in sub["AGE_BIN_LABEL"]:
            if (
                not ignore_selected_bar
                and selected_age_bin is not None
                and selected_cancer_type is not None
                and cancer == selected_cancer_type
                and age_bin == selected_age_bin
            ):
                line_widths.append(3.0)
                line_colors.append("#111111")

            elif cancer in highlight_groups:
                line_widths.append(1.4)
                line_colors.append("#222222")

            else:
                line_widths.append(0)
                line_colors.append("rgba(0,0,0,0)")

        if mode == "count":
            hovertemplate = (
                "<b>Age bin:</b> %{customdata[0]}<br>"
                f"<b>{group_label}:</b> %{{customdata[1]}}<br>"
                "<b>Deaths:</b> %{customdata[2]}<extra></extra>"
            )
        else:
            hovertemplate = (
                "<b>Age bin:</b> %{customdata[0]}<br>"
                f"<b>{group_label}:</b> %{{customdata[1]}}<br>"
                "<b>Percentage:</b> %{customdata[2]:.1f}%<extra></extra>"
            )

        fig.add_trace(
            go.Bar(
                x=sub["AGE_BIN_LABEL"],
                y=sub["display_death_count"],
                name=cancer,
                customdata=customdata,
                marker=dict(
                    color=get_group_color(cancer, group_color_map),
                    opacity=trace_opacity,
                    line=dict(width=line_widths, color=line_colors),
                ),
                selected=dict(marker=dict(opacity=1)),
                unselected=dict(marker=dict(opacity=1)),
                hovertemplate=hovertemplate,
            )
        )

    yaxis_title = "Number of deaths" if mode == "count" else "Percentage (%)"

    fig.update_layout(
        template="plotly_white",
        title=title,
        barmode="group",
        xaxis_title="Age bins",
        yaxis_title=yaxis_title,
        showlegend=False,
        margin=dict(l=50, r=30, t=70, b=95),
        height=None,
        clickmode="event",
        dragmode="pan",
        hovermode="closest",
        uirevision="death-age-static",
    )

    fig.update_xaxes(
        tickangle=0,
        categoryorder="array",
        categoryarray=age_order,
        tickmode="array",
        tickvals=age_order,
        ticktext=age_order,
        showticklabels=True,
        fixedrange=False,
    )

    fig.update_yaxes(
        fixedrange=True,
    )

    return fig