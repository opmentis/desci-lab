#!/usr/bin/env python3
import asyncio
import logging
import argparse
from services.miner_service import MinerService
from config import settings
from pathlib import Path
from utils.logging import setup_logging

# Setup logging first
setup_logging()

logger = logging.getLogger(__name__)

async def main(wallet_address: str, api_url: str):
    """Main entry point"""
    try:
        logger.info("Starting OpMentis AlphaFold Miner")
        logger.info("Note: Databases will be streamed as needed")
        logger.info("Using streaming approach to minimize disk usage")
        
        # Create work directory
        Path("/tmp/ramdisk/work").mkdir(parents=True, exist_ok=True)
        logger.info("Work directory ready")
        
        miner = MinerService(
            wallet_address=wallet_address,
            api_url=api_url
        )
        
        logger.info(f"Miner initialized with wallet: {wallet_address}")
        
        try:
            await miner.run()
        except KeyboardInterrupt:
            logger.info("\nShutting down miner gracefully...")
        finally:
            await miner.close()
            
    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpMentis AlphaFold Miner")
    parser.add_argument(
        "--wallet", 
        required=True,
        help="Your wallet address"
    )
    parser.add_argument(
        "--api-url",
        default=settings.API_URL,
        help="API endpoint URL"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(
        wallet_address=args.wallet,
        api_url=args.api_url
    )) 