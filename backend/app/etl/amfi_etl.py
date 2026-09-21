import httpx
import pandas as pd
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import MutualFundScheme, SchemeNAVData
import logging
import re

logger = logging.getLogger(__name__)

def parse_nav_data_line(line: str) -> dict:
    """Parse a single line from AMFI NAV data file"""
    # Pattern to extract different fields based on known AMFI format
    # AMFI format example: "AMF0001,14-Jan-2023,12345.6789,1000.0000"
    
    # Extract AMFI code
    amfi_code_match = re.match(r'^(\d+)', line)
    if not amfi_code_match:
        return None
    
    # Split by comma
    parts = line.strip().split(',')
    if len(parts) < 4:
        return None
    
    try:
        amfi_code = int(parts[0])
        date_str = parts[1]
        nav = float(parts[2]) if parts[2] else 0.0
        net_assets = float(parts[3]) if len(parts) > 3 and parts[3] else 0.0
        
        # Parse date (handling different formats)
        try:
            nav_date = datetime.strptime(date_str, '%d-%b-%Y').date()
        except ValueError:
            # Try alternative format
            try:
                nav_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                nav_date = None
        
        return {
            'amfi_code': amfi_code,
            'date': nav_date,
            'nav': nav,
            'net_assets': net_assets
        }
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing line '{line}': {e}")
        return None

async def ingest_amfi_nav_data():
    """ETL function to ingest AMFI NAV data from the official source"""
    logger.info("Starting AMFI NAV data ingestion")
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Fetch data from AMFI website
        url = "https://www.amfiindia.com/spages/NAVAll.txt"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            
            # Parse the content
            lines = response.text.strip().split('\n')
            parsed_records = []
            
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    parsed = parse_nav_data_line(line)
                    if parsed:
                        parsed_records.append(parsed)
            
            if not parsed_records:
                logger.warning("No data parsed from AMFI source")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(parsed_records)
            logger.info(f"Parsed {len(df)} records from AMFI source")
            
            # Filter for valid dates
            df = df.dropna(subset=['date'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # Insert into database
            inserted_count = 0
            for _, row in df.iterrows():
                # Check if scheme exists
                scheme = db.query(MutualFundScheme).filter(
                    MutualFundScheme.amfi_code == row['amfi_code']
                ).first()
                
                if not scheme:
                    logger.warning(f"Scheme with AMFI code {row['amfi_code']} not found in database")
                    continue
                
                # Check if record already exists
                existing = db.query(SchemeNAVData).filter(
                    SchemeNAVData.time == row['date'],
                    SchemeNAVData.scheme_id == scheme.scheme_id
                ).first()
                
                if not existing:
                    nav_record = SchemeNAVData(
                        time=row['date'],
                        scheme_id=scheme.scheme_id,
                        nav=row['nav'],
                        net_assets_cr=row['net_assets']
                    )
                    db.add(nav_record)
                    inserted_count += 1
            
            db.commit()
            next(db_gen)
            logger.info(f"Inserted {inserted_count} new NAV records into database")
            
    except Exception as e:
        logger.error(f"Error during AMFI NAV data ingestion: {e}")
        try:
            db.rollback()
            next(db_gen)
        except:
            pass
        raise
    finally:
        try:
            db.close()
        except:
            pass

    logger.info("AMFI NAV data ingestion completed")

async def ingest_portfolio_holdings():
    """ETL function to ingest portfolio holdings data (placeholder for source data)"""
    logger.info("Starting portfolio holdings ingestion (placeholder)")
    
    # TODO: Implement actual portfolio holdings ingestion from source
    # This would typically fetch data from:
    # - AMFI scheme holdings files
    # - Fund house APIs
    # - BSE/NSE disclosures
    
    logger.info("Portfolio holdings ingestion is a placeholder - implement actual data source")
