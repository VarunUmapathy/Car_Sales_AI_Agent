dealership-crm/
│
├── docker-compose.yml                  # Spins up DB, Kafka, Nginx, APIs, and Microservices
├── init.sql                            # PostgreSQL initialization script
├── .env.example                        # Shared environment variables template
│
├── api_gateway/                        # Nginx Reverse Proxy
│   ├── nginx.conf                      # Your hardened Nginx configuration
│   └── ssl/                            # SSL certificates (Let's Encrypt / local dev)
│
├── proto/                              # Shared gRPC Contracts
│   ├── dealership_services.proto       # The single source of truth for all microservice APIs
│   └── generate_stubs.sh               # Bash script to compile .proto to Python/Node code
│
├── ai_agent/                           # LangGraph AI Service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                         # FastAPI wrapper to accept webhooks & trigger agent
│   ├── graph.py                        # LangGraph orchestration (Nodes, Edges, Compilation)
│   ├── agent_state.py                  # TypedDict and Pydantic schemas (CustomerProfile)
│   ├── mcp_client.py                   # Connects to external Postgres/Qdrant MCP servers
│   └── tools/
│       ├── __init__.py
│       └── handoff_tool.py             # Kafka publisher for human handoffs
│
├── mcp_servers/                        # Model Context Protocol Servers
│   ├── postgres_mcp/
│   │   ├── Dockerfile
│   │   └── index.js                    # Standard MCP server connecting to PgBouncer
│   └── qdrant_mcp/
│       ├── Dockerfile
│       └── main.py                     # Standard MCP server connecting to Vector DB
│
├── crm_api/                            # CRM FastAPI (Backend-for-Frontend & Webhook Router)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                         # App startup & background task initialization
│   ├── routers/
│   │   ├── webhooks.py                 # WhatsApp API POST endpoints
│   │   ├── dashboard.py                # REST API for React (leads, stats)
│   │   └── websockets.py               # Live connection for agent notifications
│   ├── services/
│   │   ├── kafka_consumer.py           # Listens for AI handoff events
│   │   └── mesh_rpc_client.py          # gRPC stubs calling internal microservices
│   └── schemas/
│       └── payloads.py                 # Pydantic validation (WhatsAppWebhookPayload)
│
├── microservices/                      # Internal gRPC Business Logic Services
│   ├── auth_service/
│   │   ├── Dockerfile
│   │   ├── server.py                   # gRPC Servicer implementation
│   │   └── db_repository.py            # PgBouncer queries
│   │
│   ├── chat_service/
│   │   ├── Dockerfile
│   │   ├── server.py
│   │   └── kafka_producer.py           # Broadcasts human agent replies
│   │
│   └── inventory_service/
│       ├── Dockerfile
│       └── server.py
│
└── frontend/                           # CRM React Dashboard
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        ├── components/                 # ChatBox, LeadQueue, InventoryList
        ├── hooks/
        │   └── useWebSocket.js         # Custom hook managing the live CRM connection
        ├── services/
        │   └── api.js                  # Axios calls to crm_api (REST)
        └── context/
            └── AuthContext.jsx         # Auth0 integration state