from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from scipy import stats
from statsmodels.stats.multitest import multipletests
import pandas as pd, numpy as np

router =APIRouter()

class DERequest(BaseModel):
	group_a: str # ex: Stage_I
	group_b: str # ex: Stage_IV
	padj_cutoff : float=0.05
	log2fc_cutoff: float=1.0

@router.post("/differential")
def differential_expression(req: DERequest, db: Session = Depends(get_db)):
	""" Run Wilcoxan rank-sum differential expression between 2 sample groups. Results stored in database and returned"""
	# Pull expression for both groups
	query = """
		SELECT g.gene_symbol, s.stage, e.log2_tpm
		FROM expression e
		JOIN genes g ON e.gene_id = g.gene_id
		JOIN samples s ON e.sample_id = s.sample_id
		WHERE s.stage IN (:a, :b)
	"""
	rows = db.execute(text(query), {"a":req.group_a, "b": req.group_b}).fetchall()
	df = pd.DataFrame([dict(r._mapping) for r in rows])

	if df.empty:
		return {"error": "No data found for these groups"}

	# Pivot to wide format
	pivot = df.pivot_table(index='gene_symbol', columns='stage', values='log2_tpm', aggfunc=list)

	results = []
	genes = pivot.index.tolist()
	p_values = []
	log2fcs = []

	for gene in genes:
		try:
			a_vals = pivot.loc[gene, req.group_a]
			b_vals = pivot.loc[gene, req.group_b]
			if len(a_vals) < 5 or len(b_vals) < 5:
				continue
			stat, pval = stats.mannwhitneyu(a_vals, b_vals, alternative='two-sided')
			log2fc = np.mean(b_vals) - np.mean(a_vals)
			p_values.append(pval)
			log2fcs.append(log2fc)	
			results.append(gene)
		except:
			continue

	# Multiple testing correction (Benjamin-Hochberg)
	_, padj_vals, _, _ = multipletests(p_values, method='fdr_bh')

	result_df = pd.DataFrame({ 'gene_symbol': results, 'log2fc': log2fcs, 'pvalue': p_values, 'padj': padj_vals})
	result_df['direction'] = result_df['log2fc'].apply(lambda x: 'up' if x>0 else 'down')

	# Filter to significant
	sig = result_df[(result_df['padj'] < req.padj_cutoff) & (result_df['log2fc'].abs() > req.log2fc_cutoff)].sort_values('padj')

	return { "group_a": req.group_a, "group_b": req.group_b, "total_tested": len(result_df), "significant": len(sig), "results": sig.to_dict(orient='records')}

class AgentQuery(BaseModel):
	question:str

@router.post("/agent")
def run_agent(query: AgentQuery):
    """Run the autonomous BioLens analysis agent."""
    from agent.bio_agent import run_analysis
    return {"question": query.question, "answer": run_analysis(query.question)}

@router.get("/classify/{sample_id}")
def classify_sample(sample_id: str, db: Session = Depends(get_db)):
	"""Predict cancer subtype for a sample from its expression profile."""
	# Get expression values for this sample
	query = """ 
	SELECT g.gene_symbol, e.log2_tpm
	FROM expression e
	JOIN genes g ON e.gene_id = g.gene_id
	WHERE e.sample_id = :sample_id
	"""
	rows = db.execute(text(query), {"sample_id": sample_id}).fetchall()
	if not rows:
		raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
	
	expression_dict = {r.gene_symbol: r.log2_tpm for r in rows}

	from ml.classifier import predict
	result = predict(expression_dict)
	result["sample_id"] = sample_id
	return result
