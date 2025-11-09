"""
Data Transformation Module - Silver Layer
Reads raw data, performs transformations, and loads to staging table
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import create_engine, text
import json


class DataTransformer:
    """
    Handles data transformation and loading to staging table.
    
    Transformations:
    - Data type standardization
    - Null handling with appropriate defaults
    - Field normalization (names, formats)
    - Derived columns (rankings, categories, calculations)
    - Data quality validations
    """
    
    def __init__(self):
        self.raw_data_dir = Path("/opt/dagster/app/data/raw")
        self.processed_data_dir = Path("/opt/dagster/app/data/processed")
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Database connection
        db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'crypto_data'),
            'user': os.getenv('DB_USER', 'pipeline_user'),
            'password': os.getenv('DB_PASSWORD', 'pipeline_pass')
        }
        
        self.engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
    
    def get_latest_raw_file(self) -> Path:
        """Find the most recent raw data file (Parquet preferred)"""
        # Get all parquet files sorted by modification time
        parquet_files = list(self.raw_data_dir.rglob("*.parquet"))
        
        if not parquet_files:
            # Fall back to JSON if no parquet files found
            json_files = list(self.raw_data_dir.rglob("*.json"))
            if not json_files:
                raise FileNotFoundError("No raw data files found")
            return max(json_files, key=lambda p: p.stat().st_mtime)
        
        return max(parquet_files, key=lambda p: p.stat().st_mtime)
    
    def read_raw_data(self, file_path: Path) -> pd.DataFrame:
        """Read raw data from file"""
        print(f"Reading raw data from: {file_path}")
        
        if file_path.suffix == '.parquet':
            df = pd.read_parquet(file_path)
        elif file_path.suffix == '.json':
            df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        print(f"Loaded {len(df)} records with {len(df.columns)} columns")
        return df
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformations to raw data.
        
        Transformations:
        1. Standardize column names (snake_case)
        2. Handle null values appropriately
        3. Standardize data types
        4. Create derived columns
        5. Add metadata columns
        """
        print("\nApplying transformations...")
        
        # Make a copy to avoid modifying original
        df_transformed = df.copy()
        
        # 1. Add processing metadata
        df_transformed['processed_at'] = datetime.now()
        df_transformed['record_hash'] = df_transformed.apply(
            lambda row: hash(str(row.get('id', '')) + str(row.get('symbol', ''))), 
            axis=1
        )
        
        # 2. Standardize data types
        numeric_columns = [
            'current_price', 'market_cap', 'market_cap_rank', 
            'total_volume', 'high_24h', 'low_24h', 'price_change_24h',
            'price_change_percentage_24h', 'market_cap_change_24h',
            'market_cap_change_percentage_24h', 'circulating_supply',
            'total_supply', 'max_supply', 'ath', 'atl'
        ]
        
        for col in numeric_columns:
            if col in df_transformed.columns:
                df_transformed[col] = pd.to_numeric(df_transformed[col], errors='coerce')
        
        # 3. Handle null values with domain-appropriate defaults
        df_transformed['total_supply'] = df_transformed['total_supply'].fillna(0)
        df_transformed['max_supply'] = df_transformed['max_supply'].fillna(0)
        df_transformed['market_cap_rank'] = df_transformed['market_cap_rank'].fillna(999)
        
        # 4. Create derived columns - Market Cap Categories
        def categorize_market_cap_rank(rank):
            if pd.isna(rank) or rank >= 999:
                return 'unranked'
            elif rank <= 10:
                return 'large_cap'
            elif rank <= 50:
                return 'mid_cap'
            else:
                return 'small_cap'
        
        df_transformed['market_cap_category'] = df_transformed['market_cap_rank'].apply(
            categorize_market_cap_rank
        )
        
        # 5. Calculate additional metrics
        # Price volatility (24h range as % of current price)
        df_transformed['price_volatility_24h'] = np.where(
            df_transformed['current_price'] > 0,
            ((df_transformed['high_24h'] - df_transformed['low_24h']) / 
             df_transformed['current_price'] * 100),
            0
        )
        
        # Distance from ATH (All-Time High)
        df_transformed['distance_from_ath_pct'] = np.where(
            df_transformed['ath'] > 0,
            ((df_transformed['current_price'] - df_transformed['ath']) / 
             df_transformed['ath'] * 100),
            0
        )
        
        # Volume to market cap ratio (liquidity indicator)
        df_transformed['volume_to_mcap_ratio'] = np.where(
            df_transformed['market_cap'] > 0,
            df_transformed['total_volume'] / df_transformed['market_cap'],
            0
        )
        
        # 6. Normalize text fields
        df_transformed['symbol'] = df_transformed['symbol'].str.upper()
        df_transformed['name'] = df_transformed['name'].str.strip()
        
        print(f"✓ Transformations completed")
        print(f"  - Added {len([c for c in df_transformed.columns if c not in df.columns])} derived columns")
        print(f"  - Total columns: {len(df_transformed.columns)}")
        
        return df_transformed
    
    def create_staging_table(self):
        """Create staging table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS staging_crypto_market (
            id VARCHAR(100) PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            name VARCHAR(255) NOT NULL,
            image TEXT,
            current_price NUMERIC(20, 8),
            market_cap NUMERIC(30, 2),
            market_cap_rank INTEGER,
            total_volume NUMERIC(30, 2),
            high_24h NUMERIC(20, 8),
            low_24h NUMERIC(20, 8),
            price_change_24h NUMERIC(20, 8),
            price_change_percentage_24h NUMERIC(10, 4),
            market_cap_change_24h NUMERIC(30, 2),
            market_cap_change_percentage_24h NUMERIC(10, 4),
            circulating_supply NUMERIC(30, 2),
            total_supply NUMERIC(30, 2),
            max_supply NUMERIC(30, 2),
            ath NUMERIC(20, 8),
            ath_change_percentage NUMERIC(10, 4),
            ath_date TIMESTAMP,
            atl NUMERIC(20, 8),
            atl_change_percentage NUMERIC(10, 4),
            atl_date TIMESTAMP,
            last_updated TIMESTAMP,
            
            -- Derived columns
            market_cap_category VARCHAR(20),
            price_volatility_24h NUMERIC(10, 4),
            distance_from_ath_pct NUMERIC(10, 4),
            volume_to_mcap_ratio NUMERIC(10, 6),
            
            -- Metadata
            processed_at TIMESTAMP NOT NULL,
            record_hash BIGINT,
            
            -- Indexes for common queries
            CONSTRAINT valid_market_cap_rank CHECK (market_cap_rank > 0 OR market_cap_rank = 999)
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_market_cap_rank ON staging_crypto_market(market_cap_rank);
        CREATE INDEX IF NOT EXISTS idx_market_cap_category ON staging_crypto_market(market_cap_category);
        CREATE INDEX IF NOT EXISTS idx_processed_at ON staging_crypto_market(processed_at);
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        
        print("✓ Staging table created/verified")
    
    def load_to_staging(self, df: pd.DataFrame) -> int:
        """Load transformed data to staging table"""
        print(f"\nLoading {len(df)} records to staging table...")
        
        # Select columns that exist in the table
        table_columns = [
            'id', 'symbol', 'name', 'image', 'current_price', 'market_cap',
            'market_cap_rank', 'total_volume', 'high_24h', 'low_24h',
            'price_change_24h', 'price_change_percentage_24h',
            'market_cap_change_24h', 'market_cap_change_percentage_24h',
            'circulating_supply', 'total_supply', 'max_supply',
            'ath', 'ath_change_percentage', 'ath_date',
            'atl', 'atl_change_percentage', 'atl_date', 'last_updated',
            'market_cap_category', 'price_volatility_24h',
            'distance_from_ath_pct', 'volume_to_mcap_ratio',
            'processed_at', 'record_hash'
        ]
        
        # Filter to only existing columns
        df_to_load = df[[col for col in table_columns if col in df.columns]].copy()
        
        # Load data (replace existing records)
        df_to_load.to_sql(
            'staging_crypto_market',
            self.engine,
            if_exists='replace',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        print(f"✓ Loaded {len(df_to_load)} records to staging_crypto_market")
        
        return len(df_to_load)
    
    def save_processed_data(self, df: pd.DataFrame) -> str:
        """Save processed data locally for audit trail"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.processed_data_dir / f"crypto_processed_{timestamp}.parquet"
        
        df.to_parquet(output_path, index=False, compression='snappy')
        print(f"✓ Saved processed data: {output_path}")
        
        return str(output_path)
    
    def transform_and_load(self) -> Dict[str, Any]:
        """
        Main method: Read raw data, transform, and load to staging.
        
        Returns:
            Dictionary with transformation metadata
        """
        start_time = datetime.now()
        
        # 1. Read latest raw data
        raw_file = self.get_latest_raw_file()
        df_raw = self.read_raw_data(raw_file)
        
        # 2. Transform data
        df_transformed = self.transform_data(df_raw)
        
        # 3. Create/verify staging table
        self.create_staging_table()
        
        # 4. Load to staging
        records_loaded = self.load_to_staging(df_transformed)
        
        # 5. Save processed data locally
        processed_file = self.save_processed_data(df_transformed)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            "records_transformed": records_loaded,
            "staging_table": "staging_crypto_market",
            "raw_file": str(raw_file),
            "processed_file": processed_file,
            "load_timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "transformations": [
                "Data type standardization",
                "Null value handling",
                "Market cap categorization",
                "Volatility calculation",
                "Distance from ATH calculation",
                "Volume/MarketCap ratio"
            ]
        }
        
        print(f"\n✓ Transformation & Loading completed in {duration:.2f}s")
        
        return result


def main():
    """Standalone execution for testing"""
    transformer = DataTransformer()
    result = transformer.transform_and_load()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
