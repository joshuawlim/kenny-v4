# Kenny V4 - Personal AI Assistant

Kenny V4 is a personal AI assistant that provides intelligent routing across multiple specialized agents to help with search, calendar management, weekly digests, and personal memory recall.

## Architecture

### Router Agent Workflow
The core of Kenny is the Router Agent workflow that:
1. Receives requests via webhook endpoint
2. Uses Qwen2.5 (3B) model to classify intent into categories:
   - `search` - Information retrieval, finding data  
   - `digest` - Weekly summaries, reports, analytics
   - `calendar` - Scheduling, events, meetings
   - `memory` - Contacts, relationships, personal info
   - `general` - Everything else, casual conversation

3. Routes to appropriate specialized agent
4. Returns formatted JSON response

### Services
- **n8n** (localhost:5678) - Workflow orchestration
- **Open WebUI** (localhost:3000) - User interface  
- **Ollama** (localhost:11434) - Local LLM inference
- **Supabase** (localhost:8000) - Database and auth
- **Neo4j** (localhost:7474) - Graph database for relationships

## Setup

### Prerequisites
- Docker and Docker Compose
- Git

### Installation

1. **Clone and start infrastructure:**
   ```bash
   cd local-ai-packaged
   docker-compose up -d n8n open-webui
   ```

2. **Start Ollama and pull model:**
   ```bash
   docker run -d --name ollama-standalone -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
   docker exec ollama-standalone ollama pull qwen2.5:3b-instruct
   ```

3. **Import workflow:**
   - Open n8n at http://localhost:5678
   - Import `router-agent-workflow.json` or `simple-router-test.json`
   - Activate the workflow

### Testing

Test the router endpoint:
```bash
curl -X POST http://localhost:5678/webhook/kenny-router \
  -H "Content-Type: application/json" \
  -d '{"message": "help me find information about AI"}'
```

Expected response:
```json
{
  "response": "I received your search request: \"help me find information about AI\"",
  "intent": "search", 
  "timestamp": "2025-09-05T04:16:23.480Z",
  "status": "success"
}
```

## Development Status

### ✅ Completed (Epic 1: Foundation Setup)
- [x] Environment Setup & Docker Configuration  
- [x] Mobile Access via Cloudflare Tunnel
- [x] Basic Router Agent Workflow (in progress)

### 🚧 In Progress
- Router Agent testing and refinement
- Error handling and logging
- End-to-end Open WebUI integration

### 📋 Planned  
- Epic 2: MacOS + WhatsApp Integration
- Epic 3: Cross-Platform Search Agent
- Epic 4: Weekly Digest + Analytics Foundation

## Router Categories

The router classifies queries into these categories:

- **search** - "find information about X", "search for Y", "lookup Z"
- **digest** - "weekly summary", "what happened this week", "analytics"  
- **calendar** - "schedule meeting", "check my calendar", "book appointment"
- **memory** - "who is X", "remember that Y", "contact details for Z"
- **general** - casual conversation, help requests, unclassified queries

## Webhook Endpoint

- **URL:** `http://localhost:5678/webhook/kenny-router`
- **Method:** POST
- **Body:** `{"message": "your query here"}`
- **Response:** JSON with response, intent, timestamp, and status

## Next Steps

1. Complete router testing with all categories
2. Add error handling and logging  
3. Integrate with Open WebUI frontend
4. Build specialized agent workflows for each category
5. Add MacOS app integrations