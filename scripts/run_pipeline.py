"""
Standalone Pipeline Runner
Executes the complete pipeline: Ingest → Transform → Model
Can be run independently without Dagster for testing
"""

import sys
import time
from datetime import datetime

# Import pipeline modules
from ingest import CryptoDataIngestion
from transform import DataTransformer
from models import DataModeler


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70 + "\n")


def print_success(message: str):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"✗ {message}")


def run_pipeline():
    """Execute the complete data pipeline"""
    
    print_header("CRYPTO DATA PIPELINE - FULL EXECUTION")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        # ====================================================================
        # STAGE 1: INGESTION (Bronze Layer)
        # ====================================================================
        print_header("STAGE 1: DATA INGESTION (Bronze Layer)")
        
        ingestion = CryptoDataIngestion()
        ingest_result = ingestion.fetch_and_store(format="both")
        
        print_success(f"Ingested {ingest_result['records_count']} records")
        print_success(f"Stored at: {ingest_result['file_path']}")
        
        # ====================================================================
        # STAGE 2: TRANSFORMATION & LOADING (Silver Layer)
        # ====================================================================
        print_header("STAGE 2: TRANSFORMATION & LOADING (Silver Layer)")
        
        transformer = DataTransformer()
        transform_result = transformer.transform_and_load()
        
        print_success(f"Transformed {transform_result['records_transformed']} records")
        print_success(f"Loaded to: {transform_result['staging_table']}")
        print_success(f"Duration: {transform_result['duration_seconds']}s")
        
        # ====================================================================
        # STAGE 3: DATA MODELING (Gold Layer)
        # ====================================================================
        print_header("STAGE 3: DATA MODELING (Gold Layer)")
        
        modeler = DataModeler()
        model_results = modeler.build_all_models()
        
        print_success(f"Analytics mart: {model_results['analytics_mart']['records_in_mart']} records")
        print_success(f"Segment analysis: {model_results['segment_analysis']['segments_count']} segments")
        
        # ====================================================================
        # PIPELINE COMPLETE
        # ====================================================================
        duration = time.time() - start_time
        
        print_header("PIPELINE EXECUTION COMPLETE")
        print(f"Total duration: {duration:.2f} seconds")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "="*70)
        print(" SUMMARY")
        print("="*70)
        print(f"✓ Bronze Layer: {ingest_result['records_count']} records ingested")
        print(f"✓ Silver Layer: {transform_result['records_transformed']} records transformed")
        print(f"✓ Gold Layer: {model_results['analytics_mart']['records_in_mart']} records in analytics mart")
        print(f"✓ Total time: {duration:.2f}s")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print_error(f"Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
