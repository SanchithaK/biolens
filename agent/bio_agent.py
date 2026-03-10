""" BioLens analysis agent.
Uses LangChain + Claude to autonomously run multi-step genomics analyses by calling BioLens API endpoints as tools"""
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent
import requests, os
from dotenv import load_dotenv

load_dotenv()

llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)
API_BASE = "http://localhost:8000"

@tool
def get_gene_expression(gene_symbol: str) -> str:
    """Query expression levels for a gene across TCGA-BRCA samples by stage."""
    r = requests.get(f"{API_BASE}/expression/{gene_symbol}")
    if r.status_code != 200:
        return f"Gene {gene_symbol} not found"
    import pandas as pd
    df = pd.DataFrame(r.json()['data'])
    if df.empty:
        return f"No expression data for {gene_symbol}"
    summary = df.groupby('stage')['log2_tpm'].agg(['mean','median','count']).round(3)
    return f"Expression of {gene_symbol} by stage:\n{summary.to_string()}"

@tool
def run_differential_expression(group_a: str, group_b: str) -> str:
    """Run differential expression between two sample groups e.g. 'Stage I' and 'Stage IV'."""
    payload = {"group_a": group_a, "group_b": group_b, "padj_cutoff": 0.05, "log2fc_cutoff": 1.0}
    r = requests.post(f"{API_BASE}/analysis/differential", json=payload)
    data = r.json()
    if 'error' in data:
        return data['error']
    top = data['results'][:15]
    lines = [f"  {g['gene_symbol']}: log2FC={g['log2fc']:.2f}, padj={g['padj']:.2e}"
             for g in top]
    return f"Top DEGs ({group_a} vs {group_b}), {data['significant']} significant:\n" + "\n".join(lines)

@tool
def get_pathway_enrichment(gene_list: str) -> str:
    """Run GO/KEGG pathway enrichment for a comma-separated list of gene symbols."""
    from gprofiler import GProfiler
    genes = [g.strip() for g in gene_list.split(",")]
    gp = GProfiler(return_dataframe=True)
    results = gp.profile(organism='hsapiens', query=genes, sources=['GO:BP','KEGG','REAC'])
    if results.empty:
        return "No enriched pathways found."
    return results[['name','p_value','source']].head(10).to_string(index=False)

@tool
def interpret_biology(question: str) -> str:
    """Ask Claude to interpret biological findings in plain language."""
    r = requests.post(f"{API_BASE}/chat/ask", json={"question": question})
    return r.json()['answer']

tools = [get_gene_expression, run_differential_expression,
         get_pathway_enrichment, interpret_biology]

agent = create_react_agent(llm, tools)

def run_analysis(question: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["messages"][-1].content

if __name__ == "__main__":
    answer = run_analysis(
        "What genes are most upregulated in Stage IV vs Stage I BRCA? "
        "What pathways do they implicate?"
    )
    print("\n=== AGENT ANSWER ===")
    print(answer)
