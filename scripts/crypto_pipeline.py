"""
Crypto Data Pipeline - Dagster Assets & Jobs
Demonstrates: Ingestion → Transformation → Analytics Modeling
"""

import os
import json
from datetime import datetime
from pathlib import Path

from dagster import (
    asset,
    AssetExecutionContext,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    AssetSelection,
)

# Import pipeline modules 
from scripts.ingest import CryptoDataIngestion
from scripts.transform import DataTransformer
from scripts.models import DataModeler


# ============================================================================
# BRONZE LAYER - Raw Data Ingestion
# ============================================================================

@asset(
    group_name="bronze_layer",
    description="Ingest raw cryptocurrency data from CoinGecko API",
    compute_kind="python"
)
def raw_crypto_data(context: AssetExecutionContext) -> dict:
    """
    Asset: Pull raw data from CoinGecko API and store locally.
    
    Returns metadata about the ingested data.
    """
    context.log.info("Starting data ingestion from CoinGecko API...")
    
    ingestion = CryptoDataIngestion()
    result = ingestion.fetch_and_store()
    
    context.log.info(f"Ingested {result['records_count']} records")
    context.log.info(f"Stored at: {result['file_path']}")
    
    # Add metadata for Dagster UI
    context.add_output_metadata({
        "records_count": result['records_count'],
        "file_path": result['file_path'],
        "file_size_kb": result.get('file_size_kb', 0),
        "timestamp": result['timestamp']
    })
    
    return result


# ============================================================================
# SILVER LAYER - Cleaned & Standardized Data
# ============================================================================

@asset(
    group_name="silver_layer",
    description="Transform and load cleaned data into staging table",
    compute_kind="python",
    deps=[raw_crypto_data]
)
def staging_crypto_data(context: AssetExecutionContext) -> dict:
    """
    Asset: Read raw data, perform transformations, load to staging table.
    
    Transformations include:
    - Data type standardization
    - Null handling
    - Field normalization
    - Derived columns (price change %, market cap rank categories)
    """
    context.log.info("Starting data transformation...")
    
    transformer = DataTransformer()
    result = transformer.transform_and_load()
    
    context.log.info(f"Transformed {result['records_transformed']} records")
    context.log.info(f"Loaded to staging table: {result['staging_table']}")
    
    context.add_output_metadata({
        "records_transformed": result['records_transformed'],
        "staging_table": result['staging_table'],
        "transformations_applied": len(result.get('transformations', [])),
        "load_timestamp": result['load_timestamp']
    })
    
    return result


# ============================================================================
# GOLD LAYER - Analytics-Ready Models
# ============================================================================

@asset(
    group_name="gold_layer",
    description="Build analytics mart for top cryptocurrencies",
    compute_kind="sql",
    deps=[staging_crypto_data]
)
def crypto_analytics_mart(context: AssetExecutionContext) -> dict:
    """
    Asset: Create analytics-ready mart with aggregations and metrics.
    
    Includes:
    - Top performers by market cap
    - Price change analytics
    - Market dominance calculations
    - Optimized with indexes
    """
    context.log.info("Building analytics mart...")
    
    modeler = DataModeler()
    result = modeler.build_analytics_mart()
    
    context.log.info(f"Created mart with {result['records_in_mart']} records")
    context.log.info(f"Applied {len(result.get('indexes', []))} indexes")
    
    context.add_output_metadata({
        "records_in_mart": result['records_in_mart'],
        "mart_table": result['mart_table'],
        "indexes_created": len(result.get('indexes', [])),
        "build_timestamp": result['build_timestamp']
    })
    
    return result


@asset(
    group_name="gold_layer",
    description="Build market segment analysis table",
    compute_kind="sql",
    deps=[staging_crypto_data]
)
def market_segment_analysis(context: AssetExecutionContext) -> dict:
    """
    Asset: Create market segment analysis for different cap categories.
    
    Segments:
    - Large cap (rank 1-10)
    - Mid cap (rank 11-50)  
    - Small cap (rank 51-100)
    """
    context.log.info("Building market segment analysis...")
    
    modeler = DataModeler()
    result = modeler.build_market_segments()
    
    context.log.info(f"Created {result['segments_count']} market segments")
    
    context.add_output_metadata({
        "segments_count": result['segments_count'],
        "segment_table": result['segment_table'],
        "total_records": result['total_records'],
        "build_timestamp": result['build_timestamp']
    })
    
    return result


# ============================================================================
# JOBS & SCHEDULES
# ============================================================================

# Define the complete pipeline job
crypto_pipeline_job = define_asset_job(
    name="crypto_pipeline_job",
    description="End-to-end crypto data pipeline: Bronze → Silver → Gold",
    selection=AssetSelection.all()
)

# Schedule to run daily at 9 AM UTC
daily_crypto_schedule = ScheduleDefinition(
    name="daily_crypto_pipeline",
    job=crypto_pipeline_job,
    cron_schedule="0 9 * * *",  # 9 AM UTC daily
    execution_timezone="UTC"
)

# Schedule for more frequent updates (every 6 hours)
frequent_crypto_schedule = ScheduleDefinition(
    name="frequent_crypto_pipeline",
    job=crypto_pipeline_job,
    cron_schedule="0 */6 * * *",  # Every 6 hours
    execution_timezone="UTC"
)


# ============================================================================
# DEFINITIONS
# ============================================================================

defs = Definitions(
    assets=[
        raw_crypto_data,
        staging_crypto_data,
        crypto_analytics_mart,
        market_segment_analysis
    ],
    jobs=[crypto_pipeline_job],
    schedules=[daily_crypto_schedule, frequent_crypto_schedule]
)
