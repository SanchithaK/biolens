import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px

API = "http://localhost:8000"

st.set_page_config(
    page_title="BioLens",
    page_icon="🔬",
    layout="wide"
)

# Header
st.title("🔬 BioLens — Gene Expression Analysis Platform")
st.caption("AI-powered analysis of TCGA Breast Cancer (BRCA) expression data · 1,218 samples · 15,000 genes")
st.divider()

# Navigation
page = st.sidebar.selectbox("Navigate", [
    "Gene Expression Explorer",
    "Differential Expression",
    "AI Interpretation",
    "Semantic Gene Search",
    "Cancer Subtype Classifier"
])

# ─── PAGE 1: Gene Expression Explorer ───
if page == "Gene Expression Explorer":
    st.header("Gene Expression Explorer")
    st.write("Query expression levels for any gene across all TCGA-BRCA samples, grouped by cancer stage.")

    gene = st.text_input("Enter gene symbol", value="SCGB2A2", placeholder="e.g. SCGB2A2, TFF1, ERBB2")

    if st.button("Search", type="primary") and gene:
        with st.spinner(f"Querying expression data for {gene}..."):
            r = requests.get(f"{API}/expression/{gene.upper()}")

        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data['data'])

            if df.empty:
                st.warning(f"No expression data found for {gene}")
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("Samples", data['n_samples'])
                col2.metric("Mean Expression", f"{df['log2_tpm'].mean():.2f}")
                col3.metric("Std Dev", f"{df['log2_tpm'].std():.2f}")

                # Box plot by stage
                fig = px.box(
                    df.dropna(subset=['stage']),
                    x='stage', y='log2_tpm', color='stage',
                    title=f"{gene.upper()} expression by BRCA stage",
                    labels={'log2_tpm': 'log2(TPM+1)', 'stage': 'Cancer Stage'},
                    category_orders={"stage": ["Stage I","Stage IIA","Stage IIB",
                                               "Stage IIIA","Stage IIIB","Stage IIIC","Stage IV"]}
                )
                fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig, use_container_width=True)

                # Subtype breakdown if available
                if 'subtype' in df.columns and df['subtype'].notna().any():
                    fig2 = px.violin(df.dropna(subset=['subtype']),
                                     x='subtype', y='log2_tpm', color='subtype',
                                     title=f"{gene.upper()} expression by PAM50 subtype",
                                     labels={'log2_tpm': 'log2(TPM+1)'})
                    fig2.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)',
                                       plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.error(f"Gene '{gene}' not found in database")

# ─── PAGE 2: Differential Expression ───
elif page == "Differential Expression":
    st.header("Differential Expression Analysis")
    st.write("Run Wilcoxon rank-sum DE analysis between two sample groups with BH multiple testing correction.")

    stages = ["Stage I", "Stage IIA", "Stage IIB", "Stage IIIA", "Stage IIIB", "Stage IIIC", "Stage IV"]
    col1, col2, col3 = st.columns(3)
    with col1: group_a = st.selectbox("Group A (baseline)", stages, index=0)
    with col2: group_b = st.selectbox("Group B (comparison)", stages, index=6)
    with col3:
        padj = st.number_input("FDR threshold", value=0.05, min_value=0.001, max_value=0.1)
        log2fc = st.number_input("log2FC threshold", value=1.0, min_value=0.5, max_value=3.0)

    if st.button("Run DE Analysis", type="primary"):
        with st.spinner(f"Running Wilcoxon test: {group_a} vs {group_b}..."):
            r = requests.post(f"{API}/analysis/differential", json={
                "group_a": group_a, "group_b": group_b,
                "padj_cutoff": padj, "log2fc_cutoff": log2fc
            })
            data = r.json()

        if 'error' in data:
            st.error(data['error'])
        elif data['significant'] == 0:
            st.warning("No significant DEGs found with these thresholds. Try relaxing the cutoffs.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Genes tested", data['total_tested'])
            col2.metric("Significant DEGs", data['significant'])
            df = pd.DataFrame(data['results'])
            col3.metric("Top gene", df.iloc[0]['gene_symbol'])

            # Volcano plot
            df['neg_log10_padj'] = -df['padj'].apply(lambda x: np.log10(x + 1e-300))
            fig = px.scatter(
                df, x='log2fc', y='neg_log10_padj',
                color='direction', hover_data=['gene_symbol'],
                color_discrete_map={'up': '#ef4444', 'down': '#3b82f6'},
                title=f"Volcano Plot: {group_a} vs {group_b}",
                labels={'log2fc': 'log2 Fold Change', 'neg_log10_padj': '-log10(padj)'}
            )
            fig.add_vline(x=log2fc, line_dash="dash", line_color="gray", opacity=0.5)
            fig.add_vline(x=-log2fc, line_dash="dash", line_color="gray", opacity=0.5)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"Top 20 DEGs")
            st.dataframe(df.head(20)[['gene_symbol','log2fc','pvalue','padj','direction']].round(4),
                         use_container_width=True)

# ─── PAGE 3: AI Interpretation ───
elif page == "AI Interpretation":
    st.header("AI Biological Interpretation")
    st.write("Ask Claude any question about gene expression, pathways, or cancer biology.")

    question = st.text_area(
        "Your question",
        height=120,
        placeholder="e.g. What does it mean if ERBB2 is highly expressed in Stage IV breast cancer?"
    )

    if st.button("Ask Claude", type="primary") and question:
        with st.spinner("Claude is thinking..."):
            r = requests.post(f"{API}/chat/ask", json={"question": question})

        if r.status_code == 200:
            answer = r.json()['answer']
            st.markdown("### Answer")
            st.markdown(answer)
        else:
            st.error("Error reaching the AI endpoint")

# ─── PAGE 4: Semantic Search ───
elif page == "Semantic Gene Search":
    st.header("Semantic Gene Search")
    st.write("Search for genes by biological function using vector similarity — no need to know exact gene names.")

    query = st.text_input(
        "Search by biological concept",
        placeholder="e.g. immune checkpoint regulation, DNA damage response, cell cycle arrest"
    )
    n = st.slider("Number of results", 5, 20, 10)

    if st.button("Search", type="primary") and query:
        with st.spinner("Searching gene embeddings..."):
            r = requests.get(f"{API}/expression/search/semantic?query={query}&n={n}")

        if r.status_code == 200:
            results = r.json()
            df = pd.DataFrame(results)
            if df.empty:
                st.warning("No results found")
            else:
                fig = px.bar(df, x='gene_symbol', y='similarity',
                             title=f"Genes most similar to: '{query}'",
                             labels={'similarity': 'Cosine Similarity', 'gene_symbol': 'Gene'},
                             color='similarity', color_continuous_scale='Blues')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True)

# ─── PAGE 5: Subtype Classifier ───
elif page == "Cancer Subtype Classifier":
    st.header("Cancer Subtype Classifier")
    st.write("Predict PAM50 breast cancer subtype from a sample's gene expression profile using a trained ML model.")

    sample_id = st.text_input(
        "Enter a TCGA sample ID",
        placeholder="e.g. TCGA-BH-A0BQ-01"
    )

    if st.button("Classify", type="primary") and sample_id:
        with st.spinner("Running classifier..."):
            r = requests.get(f"{API}/analysis/classify/{sample_id}")

        if r.status_code == 200:
            result = r.json()
            st.success(f"Predicted subtype: **{result['predicted_subtype']}** (confidence: {result['confidence']:.1%})")

            probs = result['all_probabilities']
            fig = px.bar(
                x=list(probs.keys()),
                y=list(probs.values()),
                title="Subtype Probabilities",
                labels={'x': 'PAM50 Subtype', 'y': 'Probability'},
                color=list(probs.values()),
                color_continuous_scale='Viridis'
            )
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)
        elif r.status_code == 404:
            st.error(f"Sample '{sample_id}' not found in database")
        else:
            st.error("Error running classifier — make sure the model is trained first")

    st.info("Get sample IDs from the Gene Expression Explorer page or the /expression/samples API endpoint")
    if st.button("Show sample IDs"):
        r = requests.get(f"{API}/expression/samples?limit=50")
        if r.status_code == 200:
            df_samples = pd.DataFrame(r.json())
            st.dataframe(
                df_samples[['sample_id', 'stage', 'subtype']],
                use_container_width=True
            )
