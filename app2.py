import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="BioLens",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("🔬 BioLens")
st.sidebar.caption("AI-powered gene expression analysis")
page = st.sidebar.radio(
    "Navigate",
    ["Gene Search", "Differential Expression", "Top Variable Genes", "AI Interpretation"],
)

def api_get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend. Make sure the FastAPI server is running on port 8000."
    except requests.exceptions.HTTPError as e:
        return None, f"API error: {e.response.status_code} — {e.response.text}"
    except Exception as e:
        return None, str(e)

def api_post(path, payload):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=60)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend. Make sure the FastAPI server is running on port 8000."
    except requests.exceptions.HTTPError as e:
        return None, f"API error: {e.response.status_code} — {e.response.text}"
    except Exception as e:
        return None, str(e)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Gene Search
# ══════════════════════════════════════════════════════════════════════════════
if page == "Gene Search":
    st.title("Gene Expression Explorer")
    st.markdown("Search for a gene to visualise its expression across samples.")

    col1, col2 = st.columns([3, 1])
    with col1:
        gene = st.text_input("Gene symbol", placeholder="e.g. TP53, BRCA1, MKI67").strip().upper()
    with col2:
        stage_filter = st.text_input("Stage filter (optional)", placeholder="e.g. Stage_I")

    # Semantic search helper
    with st.expander("Not sure of the gene name? Try semantic search"):
        sem_query = st.text_input("Describe the biology", placeholder="e.g. cell cycle checkpoint kinase")
        if st.button("Search", key="sem_btn") and sem_query:
            data, err = api_get("/expression/search/semantic", {"query": sem_query, "n": 10})
            if err:
                st.error(err)
            elif data:
                st.write("Top matches:")
                st.dataframe(pd.DataFrame(data), use_container_width=True)

    if gene:
        params = {"stage": stage_filter} if stage_filter else {}
        with st.spinner(f"Fetching expression data for {gene}…"):
            data, err = api_get(f"/expression/{gene}", params)

        if err:
            st.error(err)
        else:
            df = pd.DataFrame(data["data"])
            st.success(f"**{gene}** — {data['n_samples']} samples")

            tab_box, tab_violin, tab_raw = st.tabs(["Box plot", "Violin plot", "Raw data"])

            with tab_box:
                fig = px.box(
                    df, x="stage", y="log2_tpm", color="stage",
                    points="outliers",
                    title=f"{gene} expression by stage (log₂ TPM)",
                    labels={"log2_tpm": "log₂ TPM", "stage": "Stage"},
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with tab_violin:
                fig2 = px.violin(
                    df, x="stage", y="log2_tpm", color="stage", box=True,
                    title=f"{gene} expression distribution by stage",
                    labels={"log2_tpm": "log₂ TPM", "stage": "Stage"},
                )
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

                if "subtype" in df.columns and df["subtype"].nunique() > 1:
                    st.subheader("By subtype")
                    fig3 = px.box(
                        df, x="subtype", y="log2_tpm", color="subtype",
                        title=f"{gene} expression by subtype",
                        labels={"log2_tpm": "log₂ TPM"},
                    )
                    fig3.update_layout(showlegend=False)
                    st.plotly_chart(fig3, use_container_width=True)

            with tab_raw:
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, f"{gene}_expression.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Differential Expression
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Differential Expression":
    st.title("Differential Expression Analysis")
    st.markdown("Compare gene expression between two sample groups using Wilcoxon rank-sum + BH correction.")

    # Fetch available stages for dropdowns
    samples_data, err = api_get("/expression/samples", {"limit": 1000})
    if samples_data:
        stages = sorted({s["stage"] for s in samples_data if s.get("stage")})
    else:
        stages = ["Stage_I", "Stage_II", "Stage_III", "Stage_IV"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        group_a = st.selectbox("Group A", stages, index=0)
    with col2:
        group_b = st.selectbox("Group B", stages, index=min(1, len(stages) - 1))
    with col3:
        padj = st.number_input("adj. p-value cutoff", value=0.05, min_value=0.001, max_value=0.5, step=0.01, format="%.3f")
    with col4:
        log2fc = st.number_input("|log₂FC| cutoff", value=1.0, min_value=0.1, max_value=5.0, step=0.1)

    if st.button("Run DE Analysis", type="primary"):
        if group_a == group_b:
            st.warning("Please select two different groups.")
        else:
            with st.spinner("Running differential expression…"):
                result, err = api_post("/analysis/differential", {
                    "group_a": group_a,
                    "group_b": group_b,
                    "padj_cutoff": padj,
                    "log2fc_cutoff": log2fc,
                })

            if err:
                st.error(err)
            else:
                st.session_state["de_result"] = result
                st.session_state["de_groups"] = (group_a, group_b)

    if "de_result" in st.session_state:
        result = st.session_state["de_result"]
        group_a, group_b = st.session_state["de_groups"]

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Genes tested", result["total_tested"])
        col_b.metric("Significant genes", result["significant"])
        col_c.metric("Groups", f"{group_a} vs {group_b}")

        df = pd.DataFrame(result["results"])

        if df.empty:
            st.info("No significant genes found with current cutoffs.")
        else:
            # ── Volcano plot ──────────────────────────────────────────────────
            st.subheader("Volcano plot")

            # Build full result for all tested genes if available; otherwise use sig only
            df_plot = df.copy()
            df_plot["-log10_padj"] = -np.log10(df_plot["padj"].clip(lower=1e-300))
            df_plot["label"] = df_plot.apply(
                lambda r: "Up" if r["log2fc"] > 0 else "Down", axis=1
            )
            color_map = {"Up": "#e74c3c", "Down": "#3498db"}

            fig = go.Figure()
            for label, color in color_map.items():
                sub = df_plot[df_plot["label"] == label]
                fig.add_trace(go.Scatter(
                    x=sub["log2fc"], y=sub["-log10_padj"],
                    mode="markers",
                    marker=dict(color=color, size=6, opacity=0.7),
                    text=sub["gene_symbol"],
                    hovertemplate="<b>%{text}</b><br>log₂FC: %{x:.2f}<br>-log₁₀(padj): %{y:.2f}<extra></extra>",
                    name=label,
                ))

            fig.add_vline(x=log2fc, line_dash="dash", line_color="grey", opacity=0.5)
            fig.add_vline(x=-log2fc, line_dash="dash", line_color="grey", opacity=0.5)
            fig.add_hline(y=-np.log10(padj), line_dash="dash", line_color="grey", opacity=0.5)
            fig.update_layout(
                title=f"Volcano: {group_a} vs {group_b}",
                xaxis_title="log₂ Fold Change",
                yaxis_title="-log₁₀(adj. p-value)",
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

            # ── Top genes bar chart ───────────────────────────────────────────
            st.subheader(f"Top 20 significant genes")
            top20 = df.head(20).copy()
            top20["color"] = top20["direction"].map({"up": "#e74c3c", "down": "#3498db"})
            fig2 = px.bar(
                top20, x="log2fc", y="gene_symbol", orientation="h",
                color="direction",
                color_discrete_map={"up": "#e74c3c", "down": "#3498db"},
                title="Top significant genes by log₂FC",
                labels={"log2fc": "log₂FC", "gene_symbol": "Gene"},
            )
            fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
            st.plotly_chart(fig2, use_container_width=True)

            # ── Table ─────────────────────────────────────────────────────────
            st.subheader("Results table")
            st.dataframe(
                df.style.background_gradient(subset=["log2fc"], cmap="RdBu_r"),
                use_container_width=True,
            )
            csv = df.to_csv(index=False)
            st.download_button("Download results CSV", csv, "de_results.csv", "text/csv")

            # ── AI interpretation shortcut ────────────────────────────────────
            st.divider()
            st.subheader("AI biological interpretation")
            question = st.text_input(
                "Ask Claude about these results",
                value=f"What biological processes explain the differences between {group_a} and {group_b}?",
                key="de_question",
            )
            if st.button("Interpret with Claude", key="de_interp_btn"):
                with st.spinner("Asking Claude…"):
                    interp, err2 = api_post("/chat/interpret", {
                        "question": question,
                        "deg_results": result["results"],
                    })
                if err2:
                    st.error(err2)
                else:
                    st.info(interp["answer"])
                    st.caption(f"Tokens used: {interp['tokens_used']}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Top Variable Genes
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Top Variable Genes":
    st.title("Most Variable Genes")
    st.markdown("Genes with the highest expression variance across all samples — potential biomarkers.")

    n = st.slider("Number of genes", min_value=10, max_value=200, value=50, step=10)

    with st.spinner("Loading variable genes…"):
        data, err = api_get("/expression/summary/top_variable", {"n": n})

    if err:
        st.error(err)
    else:
        df = pd.DataFrame(data)

        col_chart, col_table = st.columns([2, 1])

        with col_chart:
            fig = px.bar(
                df.head(30), x="variance", y="gene_symbol", orientation="h",
                color="variance",
                color_continuous_scale="Viridis",
                title=f"Top 30 most variable genes (of {n})",
                labels={"variance": "Variance (log₂ TPM)", "gene_symbol": "Gene"},
            )
            fig.update_layout(
                yaxis={"categoryorder": "total ascending"},
                coloraxis_showscale=False,
                height=600,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.dataframe(df, use_container_width=True, height=600)
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, "top_variable_genes.csv", "text/csv")

        # Scatter: rank vs variance (elbow plot)
        st.subheader("Variance elbow plot")
        df["rank"] = range(1, len(df) + 1)
        fig2 = px.line(
            df, x="rank", y="variance",
            title="Gene rank vs variance",
            labels={"rank": "Gene rank", "variance": "Variance"},
        )
        fig2.update_traces(line_color="#8e44ad")
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — AI Interpretation
# ══════════════════════════════════════════════════════════════════════════════
elif page == "AI Interpretation":
    st.title("AI Interpretation")
    st.markdown("Ask Claude questions about cancer genomics, pathways, or interpret a list of genes.")

    mode = st.radio("Mode", ["Free-form question", "Interpret gene list"], horizontal=True)

    if mode == "Free-form question":
        question = st.text_area(
            "Your question",
            placeholder="e.g. What is the role of MYC amplification in triple-negative breast cancer?",
            height=120,
        )
        if st.button("Ask Claude", type="primary") and question:
            with st.spinner("Thinking…"):
                result, err = api_post("/chat/ask", {"question": question})
            if err:
                st.error(err)
            else:
                st.markdown("### Response")
                st.markdown(result["answer"])

    else:
        gene_input = st.text_area(
            "Paste gene list (comma or newline separated)",
            placeholder="TP53, BRCA1, EGFR, MYC …",
            height=120,
        )
        question = st.text_input(
            "Interpretation question",
            value="What pathways and biological processes are represented by these genes?",
        )
        if st.button("Interpret with Claude", type="primary") and gene_input:
            genes = [g.strip().upper() for g in gene_input.replace("\n", ",").split(",") if g.strip()]
            with st.spinner("Interpreting gene list…"):
                result, err = api_post("/chat/interpret", {
                    "question": question,
                    "gene_list": genes,
                })
            if err:
                st.error(err)
            else:
                st.markdown("### Biological interpretation")
                st.markdown(result["answer"])
                st.caption(f"Tokens used: {result['tokens_used']} | Genes submitted: {len(genes)}")
