import pandas as pd


BAD_VALUES = {"", "nan", "NaN", "None", "Unknown"}


# =========================
# COMMON FILTERS
# =========================

def filter_by_gender(df, gender):
    if gender == "All":
        return df.copy()

    if "GENDER" not in df.columns:
        return df.copy()

    return df[df["GENDER"] == gender].copy()


def filter_by_sample_type(df, sample_type):
    if not sample_type or sample_type == "All":
        return df.copy()

    if "SAMPLE_TYPE" not in df.columns:
        return df.copy()

    return df[df["SAMPLE_TYPE"] == sample_type].copy()


def filter_by_stage(df, stage_filter):
    if not stage_filter or stage_filter == "All":
        return df.copy()

    if "STAGE_HIGHEST_RECORDED" not in df.columns:
        return df.copy()

    return df[df["STAGE_HIGHEST_RECORDED"] == stage_filter].copy()


def get_filtered_df(
    df,
    gender,
    selected_cancers,
    oncotree_mode=None,
    selected_oncotree_codes=None,
    oncotree_min_count=None,
    sample_type="All",
    stage_filter="All",
):
    """
    Applica tutti i filtri principali al dataset.

    Include:
    - filtro per genere
    - filtro per tipo di campione
    - filtro per stadio
    - filtro per tipo di cancro
    - eventuale filtro per codici istologici / OncoTree
    """
    filtered = filter_by_gender(df, gender)
    filtered = filter_by_sample_type(filtered, sample_type)
    filtered = filter_by_stage(filtered, stage_filter)

    if selected_cancers:
        filtered = filtered[filtered["CANCER_TYPE"].isin(selected_cancers)].copy()
    else:
        filtered = filtered.iloc[0:0].copy()

    filtered = apply_oncotree_filters(
        filtered,
        selected_cancers=selected_cancers,
        oncotree_mode=oncotree_mode,
        selected_oncotree_codes=selected_oncotree_codes,
        oncotree_min_count=oncotree_min_count,
    )

    return filtered


# =========================
# ONCOTREE FILTERS
# =========================

def is_oncotree_mode_active(selected_cancers, oncotree_mode):
    """
    La modalità OncoTree è attiva solo quando:
    - è selezionato esattamente un tipo di cancro
    - il toggle OncoTree contiene il valore "on"
    """
    return (selected_cancers is not None and len(selected_cancers) == 1 and oncotree_mode is not None and "on" in oncotree_mode)


def get_oncotree_counts(df):
    """
    Conta quanti pazienti unici appartengono a ciascun codice OncoTree.
    """
    if "ONCOTREE_CODE" not in df.columns:
        return []

    work = df.copy()
    work["ONCOTREE_CODE"] = work["ONCOTREE_CODE"].astype(str).str.strip()
    work = work[~work["ONCOTREE_CODE"].isin(BAD_VALUES)].copy()

    if work.empty:
        return []

    counts = (
        work.groupby("ONCOTREE_CODE")["PATIENT_ID"]
        .nunique()
        .sort_values(ascending=False)
    )

    return [(str(code), int(count)) for code, count in counts.items()]


def apply_oncotree_filters(
    df,
    selected_cancers,
    oncotree_mode,
    selected_oncotree_codes,
    oncotree_min_count,
):
    """
    Applica il filtro per codici istologici / OncoTree.

    Se la modalità OncoTree non è attiva, restituisce il dataframe invariato.
    """
    if not is_oncotree_mode_active(selected_cancers, oncotree_mode):
        return df.copy()

    if "ONCOTREE_CODE" not in df.columns:
        return df.copy()

    counts = get_oncotree_counts(df)
    min_count = int(oncotree_min_count or 1)

    visible_codes = [
        code
        for code, count in counts
        if count >= min_count
    ]

    if selected_oncotree_codes is not None:
        selected_set = set(str(code) for code in selected_oncotree_codes)
        visible_codes = [
            code
            for code in visible_codes
            if code in selected_set
        ]

    if not visible_codes:
        return df.iloc[0:0].copy()

    return df[df["ONCOTREE_CODE"].astype(str).isin(visible_codes)].copy()


# =========================
# BIPARTITE GRAPH / EDGES
# =========================

def build_edge_table(df, group_col="CANCER_TYPE", target_col="METASTATIC_SITE"):
    """
    Costruisce la tabella edge per il grafo bipartito.

    Nota:
    la colonna sorgente viene rinominata internamente in CANCER_TYPE
    anche quando group_col è ONCOTREE_CODE.

    In quel caso CANCER_TYPE rappresenta il gruppo visualizzato a sinistra,
    non necessariamente il tipo di cancro.
    """
    output_columns = [
        "CANCER_TYPE",
        "METASTATIC_SITE",
        "count",
        "cancer_total",
        "meta_total",
        "pct_meta_within_cancer",
        "pct_cancer_within_meta",
    ]

    if group_col not in df.columns or target_col not in df.columns:
        return pd.DataFrame(columns=output_columns)

    work = df[[group_col, target_col]].copy()
    work[group_col] = work[group_col].astype(str).str.strip()
    work[target_col] = work[target_col].astype(str).str.strip()

    work = work[
        ~work[group_col].isin(BAD_VALUES)
        & ~work[target_col].isin(BAD_VALUES)
    ].copy()

    edges = (
        work.groupby([group_col, target_col], as_index=False)
        .size()
        .rename(
            columns={
                group_col: "CANCER_TYPE",
                target_col: "METASTATIC_SITE",
                "size": "count",
            }
        )
    )

    if edges.empty:
        return pd.DataFrame(columns=output_columns)

    cancer_tot = (
        edges.groupby("CANCER_TYPE", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "cancer_total"})
    )

    meta_tot = (
        edges.groupby("METASTATIC_SITE", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "meta_total"})
    )

    edges = edges.merge(cancer_tot, on="CANCER_TYPE", how="left")
    edges = edges.merge(meta_tot, on="METASTATIC_SITE", how="left")

    edges["pct_meta_within_cancer"] = (
        100 * edges["count"] / edges["cancer_total"]
    )
    edges["pct_cancer_within_meta"] = (
        100 * edges["count"] / edges["meta_total"]
    )

    return edges


def filter_metastasis_by_total_frequency(edges, min_freq=100):
    """
    Mantiene solo i siti metastatici che compaiono almeno min_freq volte.
    """
    if edges is None or edges.empty:
        return edges

    if "METASTATIC_SITE" not in edges.columns or "count" not in edges.columns:
        return edges.copy()

    meta_tot = (
        edges.groupby("METASTATIC_SITE", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "meta_global_total"})
    )

    filtered_edges = edges.merge(meta_tot, on="METASTATIC_SITE", how="left")

    return filtered_edges[
        filtered_edges["meta_global_total"] >= min_freq
    ].copy()


def safe_filter_metastasis_edges(edges, min_freq):
    """
    Applica il filtro sulle metastasi senza rischiare di nascondere tutto.

    Se il filtro elimina tutti gli edge, restituisce la tabella originale.
    Questo evita che il Sankey diventi vuoto quando l'utente seleziona
    un sottoinsieme piccolo di tumori o istologie.
    """
    if edges is None or edges.empty:
        return edges, min_freq, False

    filtered = filter_metastasis_by_total_frequency(edges, min_freq)

    if filtered.empty:
        return edges.copy(), None, True

    return filtered, min_freq, False