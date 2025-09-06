import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class MCPClient {
  constructor() {
    this.mcpProcess = null;
    this.requestId = 1;
    this.pendingRequests = new Map();
  }

  async start() {
    if (this.mcpProcess) {
      console.log('MCP server already running');
      return;
    }

    const appleMcpPath = join(__dirname, '..', 'apple-mcp');
    console.log('Starting Apple MCP server from:', appleMcpPath);
    
    this.mcpProcess = spawn('bun', ['run', 'index.ts'], {
      cwd: appleMcpPath,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    // Handle stdout - parse JSON-RPC responses
    this.mcpProcess.stdout.on('data', (data) => {
      const lines = data.toString().split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const response = JSON.parse(line);
          if (response.id && this.pendingRequests.has(response.id)) {
            const { resolve, reject } = this.pendingRequests.get(response.id);
            this.pendingRequests.delete(response.id);
            
            if (response.error) {
              reject(new Error(response.error.message || 'MCP Error'));
            } else {
              resolve(response.result);
            }
          }
        } catch (err) {
          // Non-JSON output, probably debug info
          console.log('[MCP stdout]:', line);
        }
      }
    });

    this.mcpProcess.stderr.on('data', (data) => {
      console.log('[MCP stderr]:', data.toString().trim());
    });

    this.mcpProcess.on('close', (code) => {
      console.log(`MCP process exited with code ${code}`);
      this.mcpProcess = null;
      // Reject all pending requests
      for (const [id, { reject }] of this.pendingRequests) {
        reject(new Error('MCP process terminated'));
      }
      this.pendingRequests.clear();
    });

    // Wait a moment for the process to initialize
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  async callTool(toolName, args = {}) {
    return new Promise((resolve, reject) => {
      if (!this.mcpProcess) {
        reject(new Error('MCP server not running'));
        return;
      }

      const id = this.requestId++;
      const request = {
        jsonrpc: '2.0',
        id,
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: args
        }
      };

      // Set timeout
      const timeoutId = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error('MCP request timeout'));
      }, 30000);

      // Store request handlers
      this.pendingRequests.set(id, {
        resolve: (result) => {
          clearTimeout(timeoutId);
          resolve(result);
        },
        reject: (error) => {
          clearTimeout(timeoutId);
          reject(error);
        }
      });

      // Send request
      const requestLine = JSON.stringify(request) + '\n';
      this.mcpProcess.stdin.write(requestLine);
    });
  }

  isRunning() {
    return this.mcpProcess !== null;
  }

  async stop() {
    if (this.mcpProcess) {
      this.mcpProcess.kill('SIGTERM');
      this.mcpProcess = null;
    }
  }
}

export default MCPClient;