"""
Data Modeling Module - Gold Layer
Builds analytics-ready tables and marts with optimizations
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import create_engine, text
import json


class DataModeler:
    """
    Handles creation of analytics-ready data models.
    
    Models:
    - crypto_analytics_mart: Optimized view of top cryptocurrencies
    - market_segment_analysis: Aggregated metrics by market cap category
    
    Optimizations:
    - Strategic indexes on frequently queried columns
    - Appropriate data types for storage efficiency
    - Aggregations for faster analytical queries
    """
    
    def __init__(self):
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
    
    def build_analytics_mart(self) -> Dict[str, Any]:
        """
        Build the main analytics mart for top cryptocurrencies.
        
        Features:
        - Top 50 cryptocurrencies by market cap
        - Key performance metrics
        - Market dominance calculations
        - Optimized indexes
        """
        print("\n" + "="*60)
        print("Building Crypto Analytics Mart")
        print("="*60)
        
        # Drop and recreate for idempotency
        drop_sql = "DROP TABLE IF EXISTS crypto_analytics_mart CASCADE;"
        
        create_mart_sql = """
        CREATE TABLE crypto_analytics_mart AS
        WITH total_market_cap AS (
            SELECT SUM(market_cap) as total_mcap
            FROM staging_crypto_market
            WHERE market_cap IS NOT NULL
        ),
        ranked_crypto AS (
            SELECT 
                s.*,
                (s.market_cap / t.total_mcap * 100) as market_dominance_pct,
                CASE 
                    WHEN s.price_change_percentage_24h > 10 THEN 'strong_gain'
                    WHEN s.price_change_percentage_24h > 0 THEN 'moderate_gain'
                    WHEN s.price_change_percentage_24h > -10 THEN 'moderate_loss'
                    ELSE 'strong_loss'
                END as price_trend_category,
                CASE
                    WHEN s.volume_to_mcap_ratio > 0.5 THEN 'high_liquidity'
                    WHEN s.volume_to_mcap_ratio > 0.1 THEN 'medium_liquidity'
                    ELSE 'low_liquidity'
                END as liquidity_category
            FROM staging_crypto_market s
            CROSS JOIN total_market_cap t
            WHERE s.market_cap_rank <= 50
              AND s.market_cap IS NOT NULL
        )
        SELECT 
            id,
            symbol,
            name,
            current_price,
            market_cap,
            market_cap_rank,
            market_dominance_pct,
            total_volume,
            price_change_percentage_24h,
            price_trend_category,
            market_cap_category,
            price_volatility_24h,
            distance_from_ath_pct,
            volume_to_mcap_ratio,
            liquidity_category,
            circulating_supply,
            max_supply,
            ath,
            ath_date,
            last_updated,
            processed_at
        FROM ranked_crypto
        ORDER BY market_cap_rank;
        
        -- Add primary key
        ALTER TABLE crypto_analytics_mart ADD PRIMARY KEY (id);
        
        -- Create indexes for common query patterns
        CREATE INDEX idx_mart_rank ON crypto_analytics_mart(market_cap_rank);
        CREATE INDEX idx_mart_price_trend ON crypto_analytics_mart(price_trend_category);
        CREATE INDEX idx_mart_liquidity ON crypto_analytics_mart(liquidity_category);
        CREATE INDEX idx_mart_dominance ON crypto_analytics_mart(market_dominance_pct DESC);
        
        -- Add comments for documentation
        COMMENT ON TABLE crypto_analytics_mart IS 'Analytics-ready mart for top 50 cryptocurrencies with performance metrics';
        COMMENT ON COLUMN crypto_analytics_mart.market_dominance_pct IS 'Percentage of total market cap held by this cryptocurrency';
        COMMENT ON COLUMN crypto_analytics_mart.price_trend_category IS 'Categorized 24h price movement: strong_gain, moderate_gain, moderate_loss, strong_loss';
        COMMENT ON COLUMN crypto_analytics_mart.liquidity_category IS 'Trading liquidity based on volume/market cap ratio';
        """
        
        with self.engine.connect() as conn:
            print("Dropping existing mart...")
            conn.execute(text(drop_sql))
            
            print("Creating analytics mart with aggregations...")
            conn.execute(text(create_mart_sql))
            
            # Get record count
            result = conn.execute(text("SELECT COUNT(*) as cnt FROM crypto_analytics_mart"))
            record_count = result.fetchone()[0]
            
            conn.commit()
        
        print(f"✓ Analytics mart created with {record_count} records")
        print("  Indexes: market_cap_rank, price_trend, liquidity, market_dominance")
        
        return {
            "mart_table": "crypto_analytics_mart",
            "records_in_mart": record_count,
            "build_timestamp": datetime.now().isoformat(),
            "indexes": [
                "idx_mart_rank",
                "idx_mart_price_trend",
                "idx_mart_liquidity",
                "idx_mart_dominance"
            ],
            "optimizations": [
                "Materialized aggregations",
                "Strategic indexes on query patterns",
                "Denormalized design for read performance",
                "Efficient data types"
            ]
        }
    
    def build_market_segments(self) -> Dict[str, Any]:
        """
        Build market segment analysis table.
        
        Segments cryptocurrencies by market cap and provides
        aggregated metrics for each segment.
        """
        print("\n" + "="*60)
        print("Building Market Segment Analysis")
        print("="*60)
        
        drop_sql = "DROP TABLE IF EXISTS market_segment_analysis CASCADE;"
        
        create_segment_sql = """
        CREATE TABLE market_segment_analysis AS
        WITH segment_stats AS (
            SELECT 
                market_cap_category as segment,
                COUNT(*) as crypto_count,
                SUM(market_cap) as total_market_cap,
                AVG(current_price) as avg_price,
                AVG(price_change_percentage_24h) as avg_price_change_24h,
                AVG(price_volatility_24h) as avg_volatility,
                AVG(volume_to_mcap_ratio) as avg_liquidity_ratio,
                SUM(total_volume) as total_volume,
                MIN(market_cap_rank) as best_rank,
                MAX(market_cap_rank) as worst_rank
            FROM staging_crypto_market
            WHERE market_cap_category != 'unranked'
            GROUP BY market_cap_category
        )
        SELECT 
            segment,
            crypto_count,
            total_market_cap,
            ROUND(avg_price::numeric, 8) as avg_price,
            ROUND(avg_price_change_24h::numeric, 2) as avg_price_change_24h,
            ROUND(avg_volatility::numeric, 2) as avg_volatility,
            ROUND(avg_liquidity_ratio::numeric, 4) as avg_liquidity_ratio,
            total_volume,
            best_rank,
            worst_rank,
            CASE 
                WHEN avg_price_change_24h > 0 THEN 'bullish'
                WHEN avg_price_change_24h < 0 THEN 'bearish'
                ELSE 'neutral'
            END as segment_sentiment,
            NOW() as analyzed_at
        FROM segment_stats
        ORDER BY 
            CASE segment
                WHEN 'large_cap' THEN 1
                WHEN 'mid_cap' THEN 2
                WHEN 'small_cap' THEN 3
            END;
        
        -- Add primary key
        ALTER TABLE market_segment_analysis ADD PRIMARY KEY (segment);
        
        -- Create index on sentiment
        CREATE INDEX idx_segment_sentiment ON market_segment_analysis(segment_sentiment);
        
        -- Add comments
        COMMENT ON TABLE market_segment_analysis IS 'Aggregated metrics by market cap segment (large/mid/small cap)';
        COMMENT ON COLUMN market_segment_analysis.segment_sentiment IS 'Overall price trend sentiment for the segment';
        """
        
        with self.engine.connect() as conn:
            print("Dropping existing segment analysis...")
            conn.execute(text(drop_sql))
            
            print("Creating market segment analysis...")
            conn.execute(text(create_segment_sql))
            
            # Get results
            result = conn.execute(text("""
                SELECT segment, crypto_count, segment_sentiment 
                FROM market_segment_analysis
                ORDER BY segment
            """))
            segments = result.fetchall()
            
            conn.commit()
        
        print(f"✓ Market segment analysis created")
        for seg in segments:
            print(f"  - {seg[0]}: {seg[1]} cryptos, sentiment: {seg[2]}")
        
        return {
            "segment_table": "market_segment_analysis",
            "segments_count": len(segments),
            "total_records": sum(seg[1] for seg in segments),
            "build_timestamp": datetime.now().isoformat(),
            "segments": [
                {
                    "name": seg[0],
                    "count": seg[1],
                    "sentiment": seg[2]
                }
                for seg in segments
            ]
        }
    
    def create_summary_view(self):
        """Create a helpful summary view for quick insights"""
        summary_view_sql = """
        CREATE OR REPLACE VIEW crypto_market_summary AS
        SELECT 
            COUNT(*) as total_cryptocurrencies,
            SUM(market_cap) as total_market_cap,
            AVG(price_change_percentage_24h) as avg_price_change_24h,
            COUNT(CASE WHEN price_change_percentage_24h > 0 THEN 1 END) as gainers,
            COUNT(CASE WHEN price_change_percentage_24h < 0 THEN 1 END) as losers,
            MAX(processed_at) as last_updated
        FROM staging_crypto_market;
        
        COMMENT ON VIEW crypto_market_summary IS 'Quick market overview statistics';
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(summary_view_sql))
            conn.commit()
        
        print("✓ Summary view created: crypto_market_summary")
    
    def build_all_models(self) -> Dict[str, Any]:
        """Build all analytics models"""
        print("\n" + "="*70)
        print(" BUILDING GOLD LAYER - ANALYTICS MODELS")
        print("="*70)
        
        results = {}
        
        # Build analytics mart
        results['analytics_mart'] = self.build_analytics_mart()
        
        # Build segment analysis
        results['segment_analysis'] = self.build_market_segments()
        
        # Create summary view
        self.create_summary_view()
        
        print("\n" + "="*70)
        print("✓ All models built successfully!")
        print("="*70)
        
        return results


def main():
    """Standalone execution for testing"""
    modeler = DataModeler()
    results = modeler.build_all_models()
    print("\n" + json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
