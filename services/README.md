# Kenny V4 Services Directory

This directory contains bridge services and utilities that extend Kenny's capabilities without duplicating infrastructure.

## Service Registry

### Active Services

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| Apple MCP Bridge | 3001 | HTTP bridge for Apple MCP tools | Running |
| WhatsApp MCP Bridge | 3004 | HTTP bridge for WhatsApp MCP tools | Running |

### Core Infrastructure (DO NOT DUPLICATE)

| Service | Port | Location | Purpose |
|---------|------|----------|---------|
| OpenWebUI | 8080 | local-ai-packaged | Chat interface |
| n8n | 5678 | local-ai-packaged | Workflow automation |
| Supabase | 8005 | local-ai-packaged | Database & storage |
| Ollama | 11434 | local-ai-packaged | LLM inference |

## Adding New Services

1. **Check port availability** in KENNY_INFRA_RULES.md
2. **Use bridge pattern** - HTTP API that connects to existing services
3. **Update this registry** when adding new services
4. **Test integration** with existing stack

## Service Templates

See `templates/` directory for:
- Express.js bridge service template
- Python processing script template
- n8n workflow integration examples

## Monitoring

All bridge services should:
- Expose `/health` endpoint
- Log to stdout/stderr (captured by Docker)
- Handle graceful shutdown (SIGTERM)
- Include error recovery logic