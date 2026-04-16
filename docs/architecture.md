```mermaid

graph TD
    %% Define Node Styles
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef gateway fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef cache fill:#cce5ff,stroke:#007bff,stroke-width:2px;
    classDef broker fill:#fff3cd,stroke:#ffc107,stroke-width:2px;
    classDef worker fill:#f8d7da,stroke:#dc3545,stroke-width:2px;
    classDef db fill:#e2e3e5,stroke:#6c757d,stroke-width:2px;
    classDef secret fill:#e83e8c,stroke:#e83e8c,stroke-width:2px,color:#fff;
    classDef proactive fill:#e1bee7,stroke:#8e24aa,stroke-width:2px;

    %% --- 1. PROACTIVE / PRE-LOADED FLOW ---
    Z[Scheduler: Inventory Restock & Events]:::proactive -->|Trigger Batch Scrape| F
    Y[(Maintenance & Service Status)]:::proactive -.->|Status Check| B

    %% --- 2. USER REQUEST FLOW (ON-DEMAND) ---
    A[User / Client]:::client -->|Search Request| B(API Gateway):::gateway
    B -->|Check Cache & TTL| C[(Redis Cache)]:::cache
    
    %% Cache Hit Flow
    C -- Cache Hit --> B
    B -->|Return Pre-loaded Data| A
    
    %% Cache Miss / Volatile Path
    C -- Cache Miss / Live Price Req --> D{Deduplication Check}
    D -- Job Already in Queue --> E[Subscribe to Active Job]
    D -- New Scrape Job --> F[Message Broker / SQS]:::broker
    
    %% --- 3. EXECUTION & ORCHESTRATION ---
    F -->|Route by Retailer| G[Worker Pool - Retailer A]:::worker
    F -->|Route by Retailer| H[Worker Pool - Retailer B]:::worker
    F -->|Route by Retailer| I[Worker Pool - Retailer C]:::worker
    
    %% Secret Management
    J[Secret Manager]:::secret -.->|Inject Proxy/API Keys| G
    J -.->|Inject Proxy/API Keys| H
    J -.->|Inject Proxy/API Keys| I
    
    %% Scraping Execution
    G & H & I -->|Live Stock/Price Scrape| K((External Retailers))
    
    %% --- 4. PERSISTENCE & MONITORING ---
    G & H & I -->|Normalize & Write| L[(Primary PostgreSQL DB)]:::db
    L -.->|Update| C
    
    M[Monitoring & Logging]:::db -.->|Trace ID Tracking| B
    M -.->|Metric Collection| F
    M -.->|Failure Alerting| G

```

Pre-loaded vs On Demand Data: The parts which pre-loaded as a batch include inventory and scheduled events. Given that new stock comes in on a schedule and not randomly,
it would be appropriate for this information to be stored in batch memory. Along with this, scheduled events such as downtime and maintenance for the service would also be 
pre-loaded data too. On-demand data is different, and information such as live stock (ie. how many the retailer has in possession at the moment) as well as the price of goods 
are amongst the items that should be provided on demand. These two data strategies are depicted in the diagram above by isolating the Proactive Flow from the Reactive Flow. 
The former represents pre-loaded information, whereas the latter represents On-Demand Data.

Queueing / orchestration approach: In the diagram above, queueing is represented by the Message Broker node. The Message broker connects the API which the user interacts with
to backend pools; this is particularly important in ensuring that longer and more arduous scraping requests do not "block" the user from conducting more searches. By using a 
Message Broker in particular, we can ensure that systems can run independently, so that if a component fails or is overwhelmed, data is not lost. The deduplication node is where
it is so that if an identical search for the same retailer is already in the queue, the new user's request "subscribes" to that existing job. Also in the diagram is the routing logic, 
which basically retries strategies should they fail (ie. if it fails with one retailer, it tries it with another).

Secret and credential management strategy: In the diagram above, the secret and credential management strategy is represented by 
