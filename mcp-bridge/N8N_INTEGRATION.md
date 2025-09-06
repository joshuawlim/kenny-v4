# n8n Integration Guide for Apple MCP Bridge

## 🚀 Quick Start

### Prerequisites
1. **MCP Bridge running**: `npm start` in `/mcp-bridge/` directory
2. **n8n installed**: Follow [n8n installation guide](https://docs.n8n.io/getting-started/installation/)
3. **Apple apps accessible**: Notes, Mail, Messages, Contacts

### Basic HTTP Request Node Setup

1. **Add HTTP Request Node** in n8n
2. **Configure Base Settings**:
   - Method: `POST` or `GET` (see endpoint list)
   - URL: `http://host.docker.internal:3003/[endpoint]` (for n8n Docker)
   - URL: `http://localhost:3003/[endpoint]` (for local n8n)
   - Authentication: None required

## 📋 Ready-to-Use Node Configurations

### 1. Create Apple Note
```json
{
  "method": "POST",
  "url": "http://host.docker.internal:3003/notes/create",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "title": "{{ $json.title }}",
    "body": "{{ $json.content }}",
    "folderName": "Kenny"
  }
}
```

### 2. Send Email via Apple Mail
```json
{
  "method": "POST", 
  "url": "http://host.docker.internal:3003/mail/send",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "to": "{{ $json.recipient }}",
    "subject": "{{ $json.subject }}",
    "body": "{{ $json.emailBody }}"
  }
}
```

### 3. Send iMessage/SMS
```json
{
  "method": "POST",
  "url": "http://host.docker.internal:3003/messages/send", 
  "headers": {"Content-Type": "application/json"},
  "body": {
    "phoneNumber": "{{ $json.phone }}",
    "message": "{{ $json.text }}"
  }
}
```

### 4. Search Contacts
```json
{
  "method": "GET",
  "url": "http://host.docker.internal:3003/contacts/search",
  "parameters": {
    "name": "{{ $json.searchName }}"
  }
}
```

## 🔗 Multi-App Workflow Example

**Scenario**: Contact lookup → Create note → Send confirmation email

1. **Node 1**: Search Contacts
   - GET `/contacts/search?name=John`
   - Output: Contact details

2. **Node 2**: Create Meeting Note
   - POST `/notes/create`
   - Input: Contact info from Node 1
   - Output: Note creation confirmation

3. **Node 3**: Send Email
   - POST `/mail/send`
   - Input: Contact email from Node 1
   - Body: References note from Node 2

## 🧪 Testing Your Workflow

### Test Data Examples
```json
{
  "title": "Test Note",
  "content": "This note was created via n8n workflow",
  "recipient": "test@example.com", 
  "subject": "Test from Kenny",
  "phone": "+1234567890",
  "searchName": "Sarah"
}
```

### Verification Steps
1. **Run workflow in n8n**
2. **Check Apple Notes** for created note
3. **Check Mail.app Sent** for sent emails
4. **Check Messages.app** for sent messages

## 📊 Endpoint Reference

| Feature | Method | Endpoint | Body/Params |
|---------|--------|----------|-------------|
| Health Check | GET | `/health` | None |
| Create Note | POST | `/notes/create` | `{title, body, folderName}` |
| List Notes | GET | `/notes/list` | `?limit=10` |
| Send Email | POST | `/mail/send` | `{to, subject, body, cc, bcc}` |
| Send Message | POST | `/messages/send` | `{phoneNumber, message}` |
| Search Contacts | GET | `/contacts/search` | `?name=...` |

## 🔧 Troubleshooting

**Bridge Not Responding**: 
```bash
cd /Users/joshwlim/Documents/Kenny\ v4/mcp-bridge
PORT=3003 npm start
```

**n8n Getting HTML Instead of JSON**: Port conflicts with Docker services
- Ensure bridge runs on port 3003: `PORT=3003 npm start`
- Use `host.docker.internal:3003` in n8n workflows
- Check `lsof -i :3003` to verify only one service is using the port

**Permission Errors**: Check macOS privacy settings
- System Settings → Privacy & Security
- Add Terminal to required permissions

**JSON Errors**: Ensure proper escaping in n8n expressions
- Use `{{ $json.field }}` syntax
- Avoid special characters in test data

## 🎯 Production Notes

- **Local Development**: Bridge runs on `localhost:3003`  
- **n8n Docker Integration**: Use `host.docker.internal:3003`
- **Production**: Consider reverse proxy for external access
- **Security**: Bridge has no authentication - use in trusted environments
- **Performance**: Each request spawns AppleScript - expect 1-3s response times

## 📚 Complete Examples

See `n8n-workflows.json` for importable workflow templates with:
- ✅ Pre-configured HTTP nodes
- ✅ Example input data  
- ✅ Multi-step workflows
- ✅ Error handling patterns