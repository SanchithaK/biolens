""" Load processed TCGA data into Biolens PostgreSQL database"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

def load_genes(expr_df):
	print("Loading genes")
	genes_df = pd.DataFrame({'gene_symbol': expr_df.columns})
	genes_df.to_sql('genes', engine, if_exists = 'append', index = False, method = 'multi', chunksize = 1000)
	# Return gene_symbol -> gene_id mapping
	with engine.connect() as conn:
		result = conn.execute(text("SELECT gene_id, gene_symbol FROM genes"))
		return {row.gene_symbol: row.gene_id for row in result}

def load_samples(clinical_df):
	print("Loading samples")
	samples_df = clinical_df[['sample_type', 'pathologic_stage']].copy()
	samples_df.index.name = 'sample_id'
	samples_df = samples_df.rename(columns={'sample_type': 'cancer_type', 'pathologic_stage': 'stage'}).reset_index()
	samples_df.to_sql('samples', engine, if_exists='append', index=False)

def load_expression(expr_df, gene_map):
	print("Loading expression data")
	# Melt wide matrix into long format for DB
	records = []
	for sample_id, row in expr_df.iterrows():
		for gene_symbol, value in row.items():
			if gene_symbol in gene_map and not pd.isna(value):
				records.append({
					'sample_id': sample_id,
					'gene_id': gene_map[gene_symbol],
					'log2_tpm': float(value)
				})
		if len(records) > 50000:
			pd.DataFrame(records).to_sql('expression', engine, if_exists='append', index = False, method='multi')
			records = []
	if records:
		pd.DataFrame(records).to_sql('expression', engine, if_exists ='append', index=False, method='multi')
	print(f"Done")
if __name__ == "__main__":
	print("Loading expression matrix")
	expr = pd.read_csv("data/processed/expression_matrix.csv", index_col = 0)
	print("Loading clinical metadata")
	clinical = pd.read_csv("data/processed/sample_metadata.csv", index_col=0)

	load_samples(clinical)
	gene_map = load_genes(expr)
	load_expression(expr, gene_map)
	print("Database loaded successfully")
