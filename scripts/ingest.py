"""
Data Ingestion Module - Bronze Layer
Fetches cryptocurrency data from CoinGecko API and stores as raw data
"""

import os
import json
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class CryptoDataIngestion:
    """
    Handles data ingestion from CoinGecko public API.
    
    Data Source: CoinGecko API (https://www.coingecko.com/en/api)
    Endpoint: /coins/markets
    Rate Limit: 10-50 requests/minute (free tier)
    """
    
    def __init__(self):
        self.api_base_url = "https://api.coingecko.com/api/v3"
        self.raw_data_dir = Path("/opt/dagster/app/data/raw")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        
    def fetch_market_data(self, vs_currency: str = "usd", per_page: int = 100) -> list:
        """
        Fetch cryptocurrency market data from CoinGecko API.
        
        Args:
            vs_currency: Target currency (default: usd)
            per_page: Number of results per page (max: 250)
            
        Returns:
            List of cryptocurrency market data dictionaries
        """
        endpoint = f"{self.api_base_url}/coins/markets"
        
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h,7d,30d"
        }
        
        try:
            print(f"Fetching data from CoinGecko API...")
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            print(f"Successfully fetched {len(data)} cryptocurrency records")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from API: {e}")
            raise
    
    def store_raw_data(self, data: list, format: str = "json") -> Dict[str, Any]:
        """
        Store raw data locally in organized folder structure.
        
        Folder structure:
        data/raw/
        ├── YYYY-MM-DD/
        │   ├── crypto_raw_TIMESTAMP.json
        │   └── crypto_raw_TIMESTAMP.parquet
        
        Args:
            data: List of dictionaries containing market data
            format: Storage format ('json', 'parquet', or 'both')
            
        Returns:
            Dictionary with file metadata
        """
        timestamp = datetime.now()
        date_folder = self.raw_data_dir / timestamp.strftime("%Y-%m-%d")
        date_folder.mkdir(exist_ok=True)
        
        file_prefix = f"crypto_raw_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        result = {
            "timestamp": timestamp.isoformat(),
            "records_count": len(data),
            "files": []
        }
        
        # Store as JSON
        if format in ["json", "both"]:
            json_path = date_folder / f"{file_prefix}.json"
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            file_size = json_path.stat().st_size / 1024  # KB
            result["files"].append({
                "format": "json",
                "path": str(json_path),
                "size_kb": round(file_size, 2)
            })
            print(f"Stored JSON: {json_path} ({file_size:.2f} KB)")
        
        # Store as Parquet (columnar format - better for analytics)
        if format in ["parquet", "both"]:
            parquet_path = date_folder / f"{file_prefix}.parquet"
            df = pd.DataFrame(data)
            df.to_parquet(parquet_path, index=False, compression='snappy')
            
            file_size = parquet_path.stat().st_size / 1024  # KB
            result["files"].append({
                "format": "parquet",
                "path": str(parquet_path),
                "size_kb": round(file_size, 2)
            })
            print(f"Stored Parquet: {parquet_path} ({file_size:.2f} KB)")
        
        # Set primary file path (parquet preferred for downstream processing)
        if format == "both" and len(result["files"]) > 1:
            result["file_path"] = result["files"][1]["path"]  # parquet
            result["file_size_kb"] = result["files"][1]["size_kb"]
        else:
            result["file_path"] = result["files"][0]["path"]
            result["file_size_kb"] = result["files"][0]["size_kb"]
        
        return result
    
    def fetch_and_store(self, format: str = "both") -> Dict[str, Any]:
        """
        Main method: Fetch data from API and store locally.
        
        Args:
            format: Storage format ('json', 'parquet', or 'both')
            
        Returns:
            Dictionary with ingestion metadata
        """
        # Fetch data
        market_data = self.fetch_market_data(per_page=100)
        
        # Store data
        storage_result = self.store_raw_data(market_data, format=format)
        
        print(f"\n✓ Ingestion completed successfully")
        print(f"  - Records: {storage_result['records_count']}")
        print(f"  - Files: {len(storage_result['files'])}")
        print(f"  - Primary file: {storage_result['file_path']}")
        
        return storage_result


def main():
    """Standalone execution for testing"""
    ingestion = CryptoDataIngestion()
    result = ingestion.fetch_and_store()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
