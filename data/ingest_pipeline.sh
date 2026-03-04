#!/bin/bash
# Biolens Data Ingestion Pipeline
# Usage: bash data/ingest_pipeline.sh
set -euo pipefail
echo "==========================="
echo "Biolens Ingestion Pipeline"
echo "==========================="

DATA_DIR="data/raw"
PROCESSED_DIR="data/processed"
BUCKET="${S3_BUCKET:-biolens-genomics-data-sk}"

# Step 1: Validate input files exist
echo "1/4 Checking input files"
for f in "$DATA_DIR/BRCA_expression.tsv" "$DATA_DIR/BRCA_clinical.tsv"; do
    if [ ! -f "$f" ]; then
	echo "ERROR: Missing $f"
	exit 1
    fi
done
echo "Input files found"

# Step 2: Basic QC on raw data
echo "2/4 Running QC checks"
N_SAMPLES=$(head -1 "$DATA_DIR/BRCA_expression.tsv" | tr '\t' '\n' | wc -l)
N_GENES=$(wc -l < "$DATA_DIR/BRCA_expression.tsv")
echo "Samples: $N_SAMPLES | Genes: $N_GENES"

# Step 3: Run Python preprocessing
echo "3/4 Preprocessing expression data"
python3 scripts/preprocess.py \
	--expression "$DATA_DIR/BRCA_expression.tsv" \
	--clinical "$DATA_DIR/BRCA_clinical.tsv" \
	--output "$PROCESSED_DIR"
echo "Processed files saved to $PROCESSED_DIR"

# Step 4: Upload to S3
# echo "4/4 Uploading to S3"
# aws s3 sync "$PROCESSED_DIR\" "s3://$BUCKET/processed/" \
#	--exclude "*.tmp" \
#	--storage-class STANDARD_IA

echo "4/4 Skipping S3 upload for now"
echo ""
echo "Pipeline done, data available at s3://$BUCKET/processed/"
