# !/usr/bin/env python3
""" Preprocess TCGA expression + clinical data for Biolens database loading """
import argparse, pandas as pd, numpy as np, os

def preprocess(expression_path, clinical_path, output_dir):
	os.makedirs(output_dir, exist_ok = True)
	
	print("Loading expression matrix")
	expr = pd.read_csv(expression_path, sep='\t', index_col=0)
	#Xena format: rows = genes, cols = samples
	# Transpose so: rows = samples, cols = genes
	expr = expr.T
	print(f"Shape: {expr.shape[0]} samples x {expr.shape[1]} genes")

	print("Loading clinical metadata:")
	clinical = pd.read_csv(clinical_path, sep='\t', index_col = 0)

	#Filter to shared samples
	shared = expr.index.intersection(clinical.index)
	expr = expr.loc[shared]
	clinical = clinical.loc[shared]
	print(f"Shared samples: {len(shared)}")

	# Keep high variance genes - top 5000 to keep DB small
	gene_var = expr.var()
	top_genes = gene_var.nlargest(15000).index
	expr = expr[top_genes]

	# Save
	expr.to_csv(f"{output_dir}/expression_matrix.csv")
	clinical.to_csv(f"{output_dir}/sample_metadata.csv")
	pd.DataFrame({'gene_symbol': top_genes}).to_csv(f"{output_dir}/gene_list.csv", index=False)
	print(f"Saved to {output_dir}/")

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--expression"), parser.add_argument("--clinical"), parser.add_argument("--output")
	args = parser.parse_args()
	preprocess(args.expression, args.clinical, args.output)
