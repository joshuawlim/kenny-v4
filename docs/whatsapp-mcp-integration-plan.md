# WhatsApp-MCP Integration Research & Plan

## Executive Summary
Research completed on integrating lharries' WhatsApp-MCP server with Kenny V4. The solution provides a robust bridge between WhatsApp Web API and n8n workflows via MCP protocol.

## Architecture Overview

### Components
1. **Go WhatsApp Bridge** (`whatsapp-bridge/`)
   - Connects via WhatsApp Web multidevice API (whatsmeow library)
   - QR code authentication (session lasts ~20 days)
   - Stores messages in local SQLite database
   - Real-time message sync

2. **Python MCP Server** (`whatsapp-mcp-server/`)
   - Implements Model Context Protocol
   - Provides standardized tools for message access
   - Handles media downloads and uploads
   - Interfaces with Go bridge via SQLite

### Data Storage
- **SQLite Database**: `whatsapp-bridge/store/`
  - `chats` table: JID, name, last_message_time
  - `messages` table: id, chat_jid, sender, content, timestamp, media metadata
- **Media Files**: Downloaded on-demand, stored locally
- **Privacy**: All data stored locally, no external API calls

## Available MCP Tools

### Contact Management
- `search_contacts`: Search by name/phone
- `get_contact_chats`: List chats with specific contact
- `get_last_interaction`: Recent message with contact

### Message Operations
- `list_messages`: Retrieve with filters (date, sender, chat, query)
- `get_message_context`: Get surrounding messages
- `download_media`: Download images/videos/documents

### Chat Management
- `list_chats`: Get chat list with metadata
- `get_chat`: Chat details by JID
- `get_direct_chat_by_contact`: Find direct chat

### Sending
- `send_message`: Text messages to individuals/groups
- `send_file`: Images, videos, documents
- `send_audio_message`: Voice messages (requires .ogg or FFmpeg)

## Integration Architecture with n8n

### Option 1: Direct MCP Integration (Recommended)
```
n8n Workflow → HTTP Request → MCP Bridge Service → WhatsApp-MCP → WhatsApp
```

**Implementation:**
1. Create Express.js bridge service (similar to Apple MCP bridge)
2. Expose WhatsApp-MCP tools as HTTP endpoints
3. n8n workflows call bridge endpoints
4. Bridge translates to MCP protocol calls

**Advantages:**
- Consistent with existing Apple MCP bridge pattern
- Easy to debug and monitor
- Can add custom middleware (rate limiting, logging)

### Option 2: Direct SQLite Access
```
n8n Workflow → SQLite Node → WhatsApp Database
```

**Implementation:**
1. n8n directly queries SQLite database
2. Use Go bridge only for sending messages
3. Custom n8n nodes for WhatsApp operations

**Advantages:**
- Lower latency for reads
- Simpler architecture

**Disadvantages:**
- Bypasses MCP abstraction layer
- More complex n8n workflows
- Harder to maintain

## Implementation Plan

### Phase 1: Setup & Authentication (2 hours)
1. Install Go and Python dependencies
2. Run WhatsApp bridge and authenticate via QR
3. Verify message sync to SQLite
4. Test MCP server tools manually

### Phase 2: Bridge Service Development (3 hours)
1. Create `whatsapp-mcp-bridge/` service
2. Implement HTTP endpoints for key tools:
   - `/search-contacts`
   - `/list-messages`
   - `/send-message`
   - `/download-media`
3. Add error handling and logging
4. Test with curl/Postman

### Phase 3: n8n Integration (2 hours)
1. Create n8n HTTP Request nodes for bridge
2. Build test workflow for message search
3. Create workflow for sending messages
4. Test media handling

### Phase 4: Kenny Integration (2 hours)
1. Add WhatsApp intent to router agent
2. Create WhatsApp sub-workflow
3. Integrate with vector database for search
4. Test end-to-end flow

## Technical Considerations

### Authentication
- QR code scan required initially
- Session persists ~20 days
- Need monitoring for re-auth requirements
- Consider automation for session refresh

### Rate Limiting
- WhatsApp has unofficial rate limits
- Implement exponential backoff
- Queue for bulk operations
- Monitor for blocks/bans

### Media Handling
- Media stored as references in SQLite
- Download on-demand via `download_media`
- Consider caching strategy
- FFmpeg required for audio conversion

### Privacy & Security
- All data stored locally
- No cloud dependencies
- Consider encryption at rest
- Implement access controls in bridge

## Success Metrics
- [ ] Messages sync within 1 second
- [ ] Search returns results <500ms
- [ ] Media downloads <5 seconds
- [ ] 99% message delivery success
- [ ] Zero data leakage

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WhatsApp blocks/bans | High | Rate limiting, natural usage patterns |
| Session expiry | Medium | Monitoring, auto-reconnect logic |
| Database corruption | Medium | Regular backups, validation |
| Privacy concerns | High | Local storage only, encryption |

## Next Steps
1. Set up WhatsApp-MCP in test environment
2. Build bridge service prototype
3. Create n8n test workflows
4. Document setup process
5. Plan production deployment

## Resources
- Repository: https://github.com/lharries/whatsapp-mcp
- WhatsApp Web API: whatsmeow library
- MCP Protocol: https://modelcontextprotocol.io
- n8n HTTP Nodes: https://docs.n8n.io/nodes/http-request