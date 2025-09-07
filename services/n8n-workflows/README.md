# Kenny V4 n8n Workflows

## Production-Ready Workflows (n8n v1.109.2 Compatible)

### WhatsApp Integration
- `whatsapp-fixed-test.json` - List WhatsApp chats
- `whatsapp-search-fixed.json` - Search WhatsApp messages  
- `whatsapp-send-fixed.json` - Send WhatsApp messages
- `whatsapp-contacts-fixed.json` - Search WhatsApp contacts

### Apple MCP Integration (Located in Archive)
- `apple-mcp-contacts-fixed.json` - Search Apple Contacts
- `apple-mcp-messages-fixed.json` - Apple Messages actions
- `apple-mcp-mail-fixed.json` - Apple Mail actions
- `apple-mcp-calendar-fixed.json` - Apple Calendar actions
- `apple-mcp-router-fixed.json` - Master router for Apple MCP

## Import Instructions

1. **Import the "fixed" workflows** - These use the correct parameter format for n8n v1.109.2
2. **Test with provided payloads** in each workflow file
3. **Activate workflows** after successful testing

## Service Dependencies

- **WhatsApp Bridge**: Port 3004 (running)
- **Apple MCP Bridge**: Port 3001 (needs setup)
- **n8n**: Port 5678 (running)

## Archive

The `archive/` folder contains older workflow versions that had import issues. Keep for reference but use the "fixed" versions for production.

## Testing

All workflows include webhook endpoints. Test via:
```bash
curl -X POST http://localhost:5678/webhook/[workflow-name] -H "Content-Type: application/json" -d '[payload]'
```