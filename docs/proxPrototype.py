import asyncio
import random
import logging
import json
from datetime import datetime

#logging and configuration for better visibility of the simulation
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

#mock method to simulate scraping a retailer
async def scrape_external_retailer(trace_id, retailer, product):
    """
    Simulates a network call to an External Retailer.
    Returns realistic JSON data or raises specific HTTP-style errors.
    """
    #replicate network latency with a random delay between 100ms and 500ms
    await asyncio.sleep(random.uniform(0.1, 0.5)) 
    
    #simulate scraper Pushback
    roll = random.random()
    
    #if roll is less than 0.15, simulate a proxy block 
    #else if roll is between 0.15 and 0.30, simulate a rate limit 
    if roll < 0.15:
        raise ConnectionError(f"HTTP 403 Forbidden - Proxy blocked by {retailer}")
    elif roll < 0.30:
        raise TimeoutError(f"HTTP 429 Too Many Requests - {retailer} is overwhelmed")
    
    #simulate a successful scrape returning realistic grocery data
    mock_payload = {
        "trace_id": trace_id,
        "retailer": retailer,
        "product_name": product,
        "price": round(random.uniform(2.50, 4.99), 2),
        "in_stock": random.choice([True, True, True, False]), 
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return json.dumps(mock_payload)


async def worker(worker_name, queue, semaphore):
    """
    Simulates a worker pulling jobs from the queue, applying concurrency limits,
    and handling failures with exponential backoff
    """
    while True:
        #pull next job from queue
        job = await queue.get()
        trace_id, retailer, product = job

        #apply concurrency limit for Retailer A using the semaphore
        async with semaphore:
            logging.info(f"[{worker_name}] 🚀 Started {trace_id} for {retailer} ({product})")

            #retry logic with exponential backoff for handling scraper failures
            retries = 0
            max_retries = 3
            success = False
            #loop until success or max retries exceeded
            while retries <= max_retries and not success:
                try:
                    #Attempt the scrape 
                    result_json = await scrape_external_retailer(trace_id, retailer, product)
                    data = json.loads(result_json)
                    
                    #Process and "Normalize" the data 
                    stock_status = "IN STOCK" if data['in_stock'] else "OUT OF STOCK"
                    logging.info(f"[{worker_name}] ✅ SUCCESS {trace_id}: {data['product_name']} is {stock_status} at ${data['price']:.2f}")
                    
                    #Persist to DB and Update Cache 
                    logging.info(f"[{worker_name}] 💾 Wrote to DB & Updated Redis Cache for {data['product_name']}")
                    success = True
                
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        #Move to Dead Letter Queue after max retries
                        logging.error(f"[{worker_name}] ❌ FAILED {trace_id} after {max_retries} retries. Moving to DLQ.")
                        break

                    
                    backoff_time = 1 * (2 ** retries)
                    logging.warning(f"[{worker_name}] ⚠️ {e}. Retrying in {backoff_time}s...")
                    
                    #Pause this specific worker without blocking the rest of the system
                    await asyncio.sleep(backoff_time)

        #Acknowledge the message was processed so it leaves the queue
        queue.task_done()


#async main function to set up the simulation environment, create workers, and simulate a traffic spike
async def main():
    print("   Starting Prox Execution Framework Prototype \n")
    
    #set up the message queue for incoming search requests
    queue = asyncio.Queue()
    
    #make it so only 2 requests can hit a retailer at a time
    retailer_a_semaphore = asyncio.Semaphore(2)

    #make 5 worker tasks to process the queue concurrently
    workers = []
    for i in range(1, 6):
        task = asyncio.create_task(worker(f"Worker-{i}", queue, retailer_a_semaphore))
        workers.append(task)

    #Deduplication Check tracker
    active_jobs = set()

    #sim a traffic spike: 10 users searching for a mix of items
    requests = ["Eggs", "Milk", "Bread", "Eggs", "Milk", "Cereal", "Bread", "Apples", "Apples", "Coffee"]
    
    print(">>> API Gateway receiving sudden traffic spike...\n")
    for i, product in enumerate(requests, 1):
        trace_id = f"req_{i:03}"
        job_key = f"Retailer_A_{product}"
        
        #Deduplication Check
        if job_key in active_jobs:
            logging.info(f"[Deduplication] {trace_id} SUBSCRIBED to active job for {product}")
            continue #Skips adding duplicate to the Message Broker
            
        #Cache Miss/New Scrape Job
        active_jobs.add(job_key)
        queue.put_nowait((trace_id, "Retailer_A", product))
        logging.info(f"[Message Broker] Added {trace_id} to Queue for {product}")

    #keep the main program running until the queue is completely empty
    await queue.join()

    #shut down the background workers 
    for w in workers:
        w.cancel()
    
    print("\nAll Search Requests Processed. Shutting down.")

if __name__ == "__main__":
    #run the asynchronous event loop
    asyncio.run(main())
