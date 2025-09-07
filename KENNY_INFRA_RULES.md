# Kenny V4 Infrastructure Rules

## CRITICAL: Current Infrastructure State

### 🏗️ ACTIVE SERVICES & PORTS

#### Docker Services (Managed)
- **Open-WebUI**: Port 3000 (moved from 8080) - `ghcr.io/open-webui/open-webui:main`
- **n8n**: Port 5678 - `n8nio/n8n`
- **Langfuse Web**: Port 3002 - `langfuse/langfuse:3`
- **Langfuse Worker**: Port 3030 - `langfuse/langfuse-worker:3`
- **Flowise**: Port 3001 - `flowiseai/flowise`
- **Supabase Stack**: Ports 4000, 5432, 6543, 8000, 8443 - Various Supabase services
- **SearchNG**: Port 8081 - `searxng/searxng:latest`
- **ClickHouse**: Ports 8123, 9000, 9009 - `clickhouse/clickhouse-server`
- **PostgreSQL**: Port 5433 (LocalAI), 5432 (Supabase) - `postgres:latest`
- **Qdrant**: Ports 6333-6334 - `qdrant/qdrant`
- **MinIO**: Ports 9010-9011 - `minio/minio`
- **Neo4j**: Ports 7473-7474, 7687 - `neo4j:latest`
- **Caddy**: Ports 80, 443 - `caddy:2-alpine`

#### Non-Docker Services (Manual)
- **WhatsApp MCP Bridge**: Port 3004 - Node.js Express server
- **WhatsApp Go Bridge**: Port 8080 - Go binary (whatsmeow)
- **Cloudflare Tunnel**: External routing to port 3000

#### Docker Volumes (Active)
- `open-webui` - Open-WebUI data
- `n8n_data`, `n8n_storage` - n8n workflows and data
- `ollama` - Ollama models (if used)
- `supabase_db-config` - Supabase database config
- `localai_*` - LocalAI ecosystem (Langfuse, ClickHouse, MinIO, etc.)

### ⚠️ NEVER CREATE NEW INSTANCES OF THESE SERVICES:

### ✅ ALLOWED NEW SERVICES:

- Bridge services (Apple MCP on 3001, WhatsApp MCP on 3004)
- Processing scripts and utilities
- Background workers and cron jobs
- Custom API endpoints

## Repository Structure

```
Kenny v4/
├── local-ai-packaged/          # Main infrastructure (DO NOT MODIFY)
│   ├── docker-compose.yml      # Core services stack
│   └── supabase/              # Database infrastructure
├── apple-mcp/                 # Apple MCP server clone
├── whatsapp-mcp-bridge/       # WhatsApp HTTP bridge (port 3004)
├── scripts/                   # Data processing scripts
├── docs/                      # Documentation
├── workflows/                 # n8n workflow JSON files
└── [app-name]/                # Future microservices

```

## Port Allocation (UPDATED 2025-09-07)

### RESERVED (DO NOT USE):
- **3000**: Open-WebUI (moved from 8080)
- **3001**: Flowise
- **3002**: Langfuse Web
- **3004**: WhatsApp MCP Bridge (ACTIVE)
- **3030**: Langfuse Worker
- **4000**: Supabase Analytics
- **5432**: Supabase PostgreSQL
- **5433**: LocalAI PostgreSQL  
- **5678**: n8n (ACTIVE)
- **6333-6334**: Qdrant
- **6543**: Supabase Pooler
- **7473-7474, 7687**: Neo4j
- **8000, 8443**: Supabase Kong
- **8080**: WhatsApp Go Bridge (ACTIVE)
- **8081**: SearchNG
- **8123, 9000, 9009**: ClickHouse
- **9010-9011**: MinIO

### AVAILABLE FOR NEW SERVICES:
- **3003, 3005-3029**: Custom MCP bridges
- **3031-3999**: Custom APIs
- **7000-7472**: Custom services
- **8001-8079, 8082-8122**: Custom services  
- **9001-9008, 9012-9999**: Development services
- **10000+**: High-port services

### EXTERNAL:
- **80, 443**: Caddy (reverse proxy)
- **Cloudflare Tunnel**: `ai.youroldmatekenny.com` → `localhost:3000`

## Docker Rules

1. **NO new docker-compose.yml files** - Use existing infrastructure
2. **NO new Dockerfile** unless for standalone utilities
3. **Bridge services only** - Connect to existing services via HTTP/TCP
4. **Use host networking** for bridge services to connect to existing stack

## Data Storage

### Use Existing:
- **PostgreSQL** (via Supabase): Main application data
- **Vector Store** (via Supabase): pgvector for embeddings
- **File Storage**: Local volumes defined in main docker-compose.yml

### DO NOT CREATE:
- New databases
- New storage volumes
- New persistent data stores

## Development Workflow

1. **Extend, don't replace** - Build on existing infrastructure
2. **Bridge pattern** - HTTP APIs that connect to existing services
3. **Workflow imports** - Add n8n workflows via JSON imports
4. **Script integration** - Python/Node scripts that use existing DBs

## Integration Patterns

### ✅ CORRECT:
```
New Service → HTTP → Bridge → Existing Infrastructure
```

### ❌ INCORRECT:
```
New Docker Stack → Duplicate Services
```

## Emergency Procedures

If services conflict or duplicate:
1. Stop all custom services
2. Use only `local-ai-packaged/docker-compose.yml`
3. Rebuild from clean state
4. Re-add custom bridges one by one

## Service Management

### Required Services for Full Kenny V4 Operation

#### Docker Stack (Automated)
- All containers in `docker ps` output above
- Managed via existing docker-compose files
- Auto-restart policies configured

#### Manual Services (Need Management)
1. **WhatsApp MCP Bridge** (Port 3004)
   - Location: `/services/whatsapp-mcp-bridge/`
   - Command: `npm start`
   - Dependencies: Node.js, WhatsApp Go Bridge

2. **WhatsApp Go Bridge** (Port 8080)  
   - Location: `/whatsapp-mcp/whatsapp-bridge/`
   - Command: `go run main.go`
   - Dependencies: Go, WhatsApp authentication

3. **Cloudflare Tunnel**
   - Command: `cloudflared tunnel run`
   - Dependencies: `.cloudflared/config.yml`

4. **Apple MCP Bridge** (Future - Port 3003)
   - Location: TBD
   - Command: TBD
   - Dependencies: macOS, Apple frameworks

#### External Dependencies
- **Ollama**: Not currently active but required for local LLM
- **Apple Mail/Calendar/Messages**: System services (macOS only)

### Service Dependencies Graph
```
Internet → Cloudflare Tunnel → Open-WebUI (3000)
                            → n8n (5678) → WhatsApp MCP (3004) → WhatsApp Go (8080)
                                       → Apple MCP (3003) → macOS APIs
```

## TODO: Service Management Automation

**Epic 2 Task: "Service Management Clean up"**

### Goals:
1. **Centralized Configuration** - Single config file defining all ports/services
2. **Service Orchestration** - Script to start/stop/monitor all services
3. **Health Checking** - Automated service health monitoring  
4. **Documentation Cleanup** - Remove hardcoded ports from all documentation
5. **Development Workflow** - One command to bring up entire Kenny environment

### Implementation Plan:
- [ ] Create `kenny-config.json` with all service definitions
- [ ] Create `kenny-service-manager.sh` script
- [ ] Update all documentation to reference config file
- [ ] Add health check endpoints to all bridges
- [ ] Create systemd/launchd services for production

## Compliance Check

Before any infrastructure changes, verify:
- [ ] No duplicate service ports (check against RESERVED list above)
- [ ] Using existing databases (PostgreSQL via Supabase)
- [ ] Following bridge pattern (HTTP APIs to existing services)
- [ ] No new storage volumes (use existing Docker volumes)
- [ ] Integration tested with existing stack
- [ ] Port allocation recorded in this document