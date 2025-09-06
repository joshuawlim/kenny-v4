# MCP Bridge Testing Guide

## 🚀 Quick Health Check
```bash
curl -s http://localhost:3001/health | jq
```

## ✅ Working Endpoints

### Notes (Works without special permissions)
```bash
# Create a note
curl -X POST http://localhost:3001/notes/create \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Note","body":"This is a test note"}' | jq

# List notes
curl -s "http://localhost:3001/notes/list" | jq

# Search notes (may timeout on large note collections)
curl -s "http://localhost:3001/notes/search?searchText=test" | jq
```

## 🔒 Permission-Required Endpoints

### Contacts (Requires: Contacts permission for Terminal)
```bash
# List all contacts
curl -s "http://localhost:3001/contacts/list" | jq

# Search contacts by name
curl -s "http://localhost:3001/contacts/search?name=josh" | jq
```

### Messages (Requires: Full Disk Access for Terminal)
```bash
# Send message
curl -X POST http://localhost:3001/messages/send \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber":"+1234567890","message":"Test message"}' | jq

# Read messages from contact
curl -s "http://localhost:3001/messages/read?phoneNumber=+1234567890&limit=5" | jq

# Get unread messages
curl -s "http://localhost:3001/messages/unread?limit=10" | jq
```

### Mail (Requires: Mail app configured with accounts)
```bash
# Send email
curl -X POST http://localhost:3001/mail/send \
  -H "Content-Type: application/json" \
  -d '{"to":"test@example.com","subject":"Test","body":"Test email"}' | jq

# Search emails
curl -s "http://localhost:3001/mail/search?searchTerm=test&limit=5" | jq

# Get unread emails
curl -s "http://localhost:3001/mail/unread?limit=10" | jq

# List mail accounts
curl -s "http://localhost:3001/mail/accounts" | jq
```

## 📋 macOS Permission Setup

### Required Permissions:

1. **For Contacts**: 
   - System Settings → Privacy & Security → Contacts
   - Add Terminal.app

2. **For Messages**: 
   - System Settings → Privacy & Security → Full Disk Access
   - Add Terminal.app

3. **For Mail**: 
   - Ensure Mail.app is configured and accessible

4. **For Calendar**: 
   - System Settings → Privacy & Security → Calendars
   - Add Terminal.app

### Troubleshooting:

- **"Command failed" errors**: Usually permission issues
- **Timeouts**: Large data collections (contacts, notes) may timeout
- **"Unknown tool" errors**: Tool name mismatch in bridge endpoints

## 🧪 Testing Priority Order:

1. **Health Check** - Always test first
2. **Notes** - Works without special permissions
3. **Contacts** - Basic macOS permission
4. **Messages** - Requires full disk access
5. **Mail** - App-specific access needed

## 📊 Expected Results:

- **Full Success**: All endpoints return data
- **Partial Success**: Notes work, others need permissions
- **Permission Denied**: Grant required macOS permissions and restart Terminal

## 🔧 Development Testing:

```bash
# Direct Apple MCP testing (bypasses bridge)
cd /Users/joshwlim/Documents/Kenny\ v4/apple-mcp
bun run test:notes

# Check available tools
bun run test:mcp
```