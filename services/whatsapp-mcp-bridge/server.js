import express from 'express';
import { spawn } from 'child_process';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json());
app.use(cors());

const PORT = process.env.PORT || 3004;

// Path to WhatsApp MCP server
const WHATSAPP_MCP_PATH = path.join(__dirname, '..', '..', 'whatsapp-mcp', 'whatsapp-mcp-server');
const UV_PATH = '/Library/Frameworks/Python.framework/Versions/3.13/bin/uv';

// Helper function to call MCP tools
async function callMCPTool(toolName, args = {}) {
  return new Promise((resolve, reject) => {
    const mcpProcess = spawn(UV_PATH, [
      '--directory',
      WHATSAPP_MCP_PATH,
      'run',
      'python',
      '-c',
      `
import json
import sys
from datetime import datetime
from whatsapp import ${toolName}

def serialize_result(obj):
    if isinstance(obj, list):
        return [serialize_result(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_result(v) for k, v in obj.items()}
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return serialize_result(obj.__dict__)
    else:
        return obj

args = json.loads('${JSON.stringify(args)}')
if '${toolName}' == 'search_contacts':
    result = ${toolName}(args['query'])
elif '${toolName}' == 'get_contact_chats':
    result = ${toolName}(args['jid'])
elif '${toolName}' == 'get_chat':
    result = ${toolName}(args['chat_jid'], args.get('include_last_message', True))
elif '${toolName}' == 'get_last_interaction':
    result = ${toolName}(args['jid'])
elif '${toolName}' == 'send_message':
    result = ${toolName}(args['recipient'], args['message'])
elif '${toolName}' == 'send_file':
    result = ${toolName}(args['recipient'], args['file_path'], args.get('caption'))
elif '${toolName}' == 'download_media':
    result = ${toolName}(args['message_id'], args['chat_jid'])
else:
    result = ${toolName}(**args)
serialized = serialize_result(result)
print(json.dumps(serialized))
      `
    ]);

    let output = '';
    let error = '';

    mcpProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    mcpProcess.stderr.on('data', (data) => {
      error += data.toString();
    });

    mcpProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`MCP process exited with code ${code}: ${error}`));
      } else {
        try {
          const result = JSON.parse(output.trim());
          resolve(result);
        } catch (e) {
          reject(new Error(`Failed to parse MCP output: ${output}`));
        }
      }
    });
  });
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'whatsapp-mcp-bridge' });
});

// Search contacts endpoint
app.post('/search-contacts', async (req, res) => {
  try {
    const { query } = req.body;
    const result = await callMCPTool('search_contacts', { query });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error searching contacts:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// List messages endpoint
app.post('/list-messages', async (req, res) => {
  try {
    const {
      after,
      before,
      sender_phone_number,
      chat_jid,
      query,
      limit = 20,
      page = 0,
      include_context = true,
      context_before = 1,
      context_after = 1
    } = req.body;

    const result = await callMCPTool('list_messages', {
      after,
      before,
      sender_phone_number,
      chat_jid,
      query,
      limit,
      page,
      include_context,
      context_before,
      context_after
    });
    
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error listing messages:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// List chats endpoint
app.post('/list-chats', async (req, res) => {
  try {
    const {
      query,
      limit = 20,
      page = 0,
      include_last_message = true,
      sort_by = "last_active"
    } = req.body;

    const result = await callMCPTool('list_chats', {
      query,
      limit,
      page,
      include_last_message,
      sort_by
    });
    
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error listing chats:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get chat endpoint
app.post('/get-chat', async (req, res) => {
  try {
    const { chat_jid, include_last_message = true } = req.body;
    const result = await callMCPTool('get_chat', { chat_jid, include_last_message });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error getting chat:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get contact chats endpoint
app.post('/get-contact-chats', async (req, res) => {
  try {
    const { jid, limit = 20, page = 0 } = req.body;
    const result = await callMCPTool('get_contact_chats', { jid, limit, page });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error getting contact chats:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Send message endpoint
app.post('/send-message', async (req, res) => {
  try {
    const { recipient, message } = req.body;
    const result = await callMCPTool('send_message', { recipient, message });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error sending message:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Send file endpoint
app.post('/send-file', async (req, res) => {
  try {
    const { recipient, file_path, caption } = req.body;
    const result = await callMCPTool('send_file', { recipient, file_path, caption });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error sending file:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Download media endpoint
app.post('/download-media', async (req, res) => {
  try {
    const { message_id, chat_jid } = req.body;
    const result = await callMCPTool('download_media', { message_id, chat_jid });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error downloading media:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get last interaction endpoint
app.post('/get-last-interaction', async (req, res) => {
  try {
    const { jid } = req.body;
    const result = await callMCPTool('get_last_interaction', { jid });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error getting last interaction:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get message context endpoint
app.post('/get-message-context', async (req, res) => {
  try {
    const { message_id, chat_jid, context_before = 5, context_after = 5 } = req.body;
    const result = await callMCPTool('get_message_context', {
      message_id,
      chat_jid,
      context_before,
      context_after
    });
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Error getting message context:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`WhatsApp MCP Bridge running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log('\nAvailable endpoints:');
  console.log('  POST /search-contacts');
  console.log('  POST /list-messages');
  console.log('  POST /list-chats');
  console.log('  POST /get-chat');
  console.log('  POST /get-contact-chats');
  console.log('  POST /send-message');
  console.log('  POST /send-file');
  console.log('  POST /download-media');
  console.log('  POST /get-last-interaction');
  console.log('  POST /get-message-context');
});