# Colorectal Cancer Transcriptomics and Network Analysis

A Bioinformatics and Systems Biology course project focused on colorectal adenocarcinoma (COAD). The first part revisits analyses from a published study; the second explores disease and drug relationships using protein interaction networks.

### Analyses

- **Gene expression:** Differential expression analysis of four GEO datasets (GSE113513, GSE134834, GSE110223, and GSE22598) using GEO2R, followed by a comparison with the reference paper.
- **Functional enrichment:** GO and KEGG enrichment using g:Profiler (ORA).
- **Network medicine:** STRING protein–protein interaction (PPI) networks and network separation between COAD and rheumatoid arthritis (RA), with diabetes mellitus (DM) as a control.
- **Drug–disease analysis:** Network proximity between methotrexate targets and the three disease modules.

For the network analyses, I compared two COAD modules: the **five hub genes reported in the paper** (CDH3, CXCL1, MMP1, MMP3, and TGFBI) and a **larger set of upregulated and downregulated genes** from the differential expression analysis.

### Files

- `assignment-stefanelli.ipynb` — analysis and discussion.
- `PPI_STRING/string_sep.tsv` and `string_sep_more_coad.tsv` — PPI data for network separation.
- `PPI_STRING/string_mtx.tsv` and `string_mtx_more_coad.tsv` — PPI data for methotrexate–disease network analysis.

The `_more_coad` files use the larger DEG-based COAD module.
The notebook also uses GEO2R, g:Profiler, and DisGeNET exports, along with some local figures. Those input files are needed to rerun all cells.

### Reference paper
Saleh et al. (2025), *Transcriptomic profiling and bioinformatics-driven statistical prioritization of CRC biomarkers: A step toward precision oncology*. [DOI: 10.1016/j.gene.2025.149594](https://doi.org/10.1016/j.gene.2025.149594).
