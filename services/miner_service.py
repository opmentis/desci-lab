import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any
import os
from config import settings
from .sequence_processor import SequenceProcessor
from tabulate import tabulate
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime
import sys

logger = logging.getLogger(__name__)

def log_dict_as_table(data_dict, logger=logger):
    headers = ['Attribute', 'Value']
    table_data = [[k, v] for k, v in data_dict.items()]
    table = tabulate(
        table_data,
        headers=headers,
        tablefmt='grid',  
        numalign='left',
        stralign='left'
    )
    
    separator = '-' * 80
    logger.info(f"\n{separator}\n{table}\n{separator}")

class MinerService:
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_UPLOADING = "uploading"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    def __init__(self, wallet_address: str, api_url: str):
        logger.info("Initializing miner service...")
        self.wallet_address = wallet_address
        self.api_url = api_url
        self.session = None
        logger.info("Creating sequence processor...")
        self.processor = SequenceProcessor()
        logger.info("Miner service initialized")
        
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def get_miner_info(self):
        wallet_address = self.wallet_address
        try:              
            async with self.session.get(f"{self.api_url}/incentives/customer/{wallet_address}") as response:
                if response.status != 200:
                    return
                response_data = await response.json()
                log_dict_as_table(data_dict=response_data)
                
        except Exception as e:
            raise
    
    async def submit_task(self, task: Dict[str, Any]):
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()   

            task_data = {
                'wallet_address': task['wallet_address'],
                'task_id': task['task_id']
            }
            async with self.session.post(
                f"{self.api_url}/tasks/complete", 
                json=task_data 
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to submit task: {error_text}")
                    return None

                return await response.json()
        
        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            raise

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next available task from server"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            params = {'wallet_address': self.wallet_address}
            async with self.session.get(
                f"{self.api_url}/tasks/next",
                params=params
            ) as response:
                if response.status == 200:
                    task = await response.json()

                    if task == 0:
                        logger.warning("Sorry, your wallet is not registered. Kindly register to access Decentralizing Scientific Discovery Lab.")
                        logger.info("Shutting down miner gracefully...")
                        sys.exit(0)

                    if task:
                        logger.debug(f"Received task: {task}")
                        
                        if isinstance(task.get('sequence'), (list, tuple)):
                            task['sequence'] = ''.join(map(str, task['sequence']))

                        return task
                    
                    logger.info("No tasks available")
                    return None
                else:
                    logger.error(f"Error getting task: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting next task: {e}")
            return None

    async def update_task_progress(self, task_id: str, progress: float, status: str) -> bool:
        """Update task progress"""
        try:
         
            progress = max(0.0, min(1.0, progress))
            
            data = {
                "status": status,
                "progress": progress,
                "message": f"Processing by {self.wallet_address}",
                "timestamp": datetime.utcnow().isoformat(),
                "wallet_address": self.wallet_address
            }
            
            async with self.session.post(
                f"{self.api_url}/tasks/{task_id}/progress", 
                json=data
            ) as response:
                if response.status == 422:
                    error_detail = await response.json()
                    logger.error(f"Validation error: {error_detail}")
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error updating task progress: {e}")
            return False

    def get_wallet_prefix(self) -> str:
        return f"wallets/{self.wallet_address}"
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def upload_result(self, task_id: str, file_path: str, file_type: str) -> bool:
        try:      
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            form_data = aiohttp.FormData()
            form_data.add_field('file',
                            file_data,
                            filename=os.path.basename(file_path))
                
            async with self.session.post(
                f"{self.api_url}/storage/{task_id}/upload",
                params={
                    "task_id": task_id,
                    "file_type": file_type,
                    "wallet": self.wallet_address
                },
                data=form_data
            ) as response:         
                if response.status != 200:
                    error_detail = await response.json()
                    logger.error(f"Upload failed: {error_detail}")
                    return False
                return True
                
        except Exception as e:
            logger.error(f"Error uploading result: {e}")
            raise
            
    async def process_task(self, task: Dict[str, Any]) -> bool:
        """Process a single task"""
        task_id = task['task_id']
        
        try:
            # Add wallet address to task data
            task["wallet_address"] = self.wallet_address
            
            # Start processing
            await self.update_task_progress(task_id, 0.0, self.STATUS_PENDING)
            
            # Process sequence (50% of progress)
            result_paths = await self.processor.process_sequence(task_id=task_id, 
                                                                 sequence=task['sequence'], 
                                                                 wallet_address=task["wallet_address"])
            
            await self.update_task_progress(task_id, 0.4, self.STATUS_PROCESSING)
            
    
            await self.update_task_progress(task_id, 0.5, self.STATUS_UPLOADING)
            
            total_files = len(result_paths)
            for i, (file_type, file_path) in enumerate(result_paths.items()):
                await self.upload_result(task_id, str(file_path), file_type)
                progress = 0.6 + (0.3 * (i / total_files))  
                await self.update_task_progress(task_id, progress, self.STATUS_UPLOADING)
            
            await self.submit_task(task)

            await self.update_task_progress(task_id, 1.0, self.STATUS_COMPLETED)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            await self.update_task_progress(task_id, 0.0, self.STATUS_FAILED)
            return False

    async def run(self):
        """Run the miner service"""
        try:
            logger.info("Starting miner service...")
            
            while True:
                try:
                    logger.info("Requesting next task...")
                    task = await self.get_next_task()

                    if task:
                        logger.info(f"Got task {task['task_id']}, processing sequence...")
                        
                        await self.process_task(task=task)

                        await self.get_miner_info()

                        logger.info("Hibernating miner service...")

                        await asyncio.sleep(settings.TASK_POLL_INTERVAL)

                    else:
                        logger.info("No task available, waiting...")
                        await asyncio.sleep(settings.TASK_POLL_INTERVAL)
                        
                except Exception as e:
                    logger.error(f"Error in miner loop: {e}")
                    await asyncio.sleep(5)
                    
        finally:
            if self.session:
                await self.session.close()
                self.session = None