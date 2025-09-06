import express from 'express';
import cors from 'cors';
import MCPClient from './mcp-client.js';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// Initialize MCP client
const mcpClient = new MCPClient();

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    mcpRunning: mcpClient.isRunning(),
    timestamp: new Date().toISOString() 
  });
});

// Messages endpoints
app.post('/messages/send', async (req, res) => {
  try {
    const { phoneNumber, message } = req.body;
    
    if (!phoneNumber || !message) {
      return res.status(400).json({ 
        error: 'phoneNumber and message are required' 
      });
    }

    const result = await mcpClient.callTool('messages', {
      operation: 'send',
      phoneNumber,
      message
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Send message error:', error);
    res.status(500).json({ 
      error: 'Failed to send message', 
      details: error.message 
    });
  }
});

app.get('/messages/read', async (req, res) => {
  try {
    const { phoneNumber, limit = 10 } = req.query;
    
    if (!phoneNumber) {
      return res.status(400).json({ 
        error: 'phoneNumber parameter is required' 
      });
    }

    const result = await mcpClient.callTool('messages', {
      operation: 'read',
      phoneNumber,
      limit: parseInt(limit)
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Read messages error:', error);
    res.status(500).json({ 
      error: 'Failed to read messages', 
      details: error.message 
    });
  }
});

app.get('/messages/unread', async (req, res) => {
  try {
    const { limit = 10 } = req.query;
    
    const result = await mcpClient.callTool('messages', {
      operation: 'unread',
      limit: parseInt(limit)
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Get unread messages error:', error);
    res.status(500).json({ 
      error: 'Failed to get unread messages', 
      details: error.message 
    });
  }
});

// Contacts endpoints
app.get('/contacts/search', async (req, res) => {
  try {
    const { name } = req.query;
    
    const result = await mcpClient.callTool('contacts', { name });
    res.json({ success: true, result });
  } catch (error) {
    console.error('Search contacts error:', error);
    res.status(500).json({ 
      error: 'Failed to search contacts', 
      details: error.message 
    });
  }
});

app.get('/contacts/list', async (req, res) => {
  try {
    const result = await mcpClient.callTool('contacts', {});
    res.json({ success: true, result });
  } catch (error) {
    console.error('List contacts error:', error);
    res.status(500).json({ 
      error: 'Failed to list contacts', 
      details: error.message 
    });
  }
});

// Mail endpoints
app.post('/mail/send', async (req, res) => {
  try {
    const { to, subject, body, cc, bcc, account } = req.body;
    
    if (!to || !subject || !body) {
      return res.status(400).json({ 
        error: 'to, subject, and body are required' 
      });
    }

    const result = await mcpClient.callTool('mail', {
      operation: 'send',
      to,
      subject,
      body,
      cc,
      bcc,
      account
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Send email error:', error);
    res.status(500).json({ 
      error: 'Failed to send email', 
      details: error.message 
    });
  }
});

app.get('/mail/search', async (req, res) => {
  try {
    const { searchTerm, account, mailbox, limit = 10 } = req.query;
    
    if (!searchTerm) {
      return res.status(400).json({ 
        error: 'searchTerm parameter is required' 
      });
    }

    const result = await mcpClient.callTool('mail', {
      operation: 'search',
      searchTerm,
      account,
      mailbox,
      limit: parseInt(limit)
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Search emails error:', error);
    res.status(500).json({ 
      error: 'Failed to search emails', 
      details: error.message 
    });
  }
});

app.get('/mail/unread', async (req, res) => {
  try {
    const { account, mailbox, limit = 10 } = req.query;
    
    const result = await mcpClient.callTool('mail', {
      operation: 'unread',
      account,
      mailbox,
      limit: parseInt(limit)
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Get unread emails error:', error);
    res.status(500).json({ 
      error: 'Failed to get unread emails', 
      details: error.message 
    });
  }
});

app.get('/mail/accounts', async (req, res) => {
  try {
    const result = await mcpClient.callTool('mail', {
      operation: 'accounts'
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Get mail accounts error:', error);
    res.status(500).json({ 
      error: 'Failed to get mail accounts', 
      details: error.message 
    });
  }
});

// Calendar endpoints
app.post('/calendar/create-event', async (req, res) => {
  try {
    const { title, startDate, endDate, location, notes } = req.body;
    
    if (!title || !startDate) {
      return res.status(400).json({ 
        error: 'title and startDate are required' 
      });
    }

    const result = await mcpClient.callTool('create_calendar_event', {
      title,
      startDate,
      endDate,
      location,
      notes
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Create calendar event error:', error);
    res.status(500).json({ 
      error: 'Failed to create calendar event', 
      details: error.message 
    });
  }
});

app.get('/calendar/events', async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    
    const result = await mcpClient.callTool('get_calendar_events', {
      startDate,
      endDate
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Get calendar events error:', error);
    res.status(500).json({ 
      error: 'Failed to get calendar events', 
      details: error.message 
    });
  }
});

// Notes endpoints
app.post('/notes/create', async (req, res) => {
  try {
    const { title, body, folderName } = req.body;
    
    if (!title || !body) {
      return res.status(400).json({ 
        error: 'title and body are required' 
      });
    }

    const result = await mcpClient.callTool('notes', {
      operation: 'create',
      title,
      body,
      folderName: folderName || 'Claude'
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Create note error:', error);
    res.status(500).json({ 
      error: 'Failed to create note', 
      details: error.message 
    });
  }
});

app.get('/notes/search', async (req, res) => {
  try {
    const { searchText, limit = 10 } = req.query;
    
    if (!searchText) {
      return res.status(400).json({ 
        error: 'searchText parameter is required' 
      });
    }

    const result = await mcpClient.callTool('notes', {
      operation: 'search',
      searchText,
      limit: parseInt(limit)
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Search notes error:', error);
    res.status(500).json({ 
      error: 'Failed to search notes', 
      details: error.message 
    });
  }
});

app.get('/notes/list', async (req, res) => {
  try {
    const { limit = 10 } = req.query;
    
    const result = await mcpClient.callTool('notes', {
      operation: 'list',
      limit: parseInt(limit)
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('List notes error:', error);
    res.status(500).json({ 
      error: 'Failed to list notes', 
      details: error.message 
    });
  }
});

// Reminders endpoints
app.post('/reminders/create', async (req, res) => {
  try {
    const { title, dueDate, priority, list } = req.body;
    
    if (!title) {
      return res.status(400).json({ 
        error: 'title is required' 
      });
    }

    const result = await mcpClient.callTool('create_reminder', {
      title,
      dueDate,
      priority,
      list
    });

    res.json({ success: true, result });
  } catch (error) {
    console.error('Create reminder error:', error);
    res.status(500).json({ 
      error: 'Failed to create reminder', 
      details: error.message 
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({ 
    error: 'Internal server error',
    details: error.message 
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`MCP Bridge Server running on http://localhost:${PORT}`);
  console.log('Available endpoints:');
  console.log('  GET  /health');
  console.log('  POST /messages/send');
  console.log('  GET  /messages/read');
  console.log('  GET  /messages/unread');
  console.log('  GET  /contacts/search');
  console.log('  GET  /contacts/list');
  console.log('  POST /mail/send');
  console.log('  GET  /mail/search');
  console.log('  GET  /mail/unread');
  console.log('  GET  /mail/accounts');
  console.log('  POST /calendar/create-event');
  console.log('  GET  /calendar/events');
  console.log('  POST /notes/create');
  console.log('  GET  /notes/search');
  console.log('  GET  /notes/list');
  console.log('  POST /reminders/create');
  
  // Start MCP client after HTTP server is ready
  mcpClient.start().catch(err => {
    console.error('Failed to start MCP client:', err);
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Shutting down gracefully...');
  await mcpClient.stop();
  process.exit(0);
});