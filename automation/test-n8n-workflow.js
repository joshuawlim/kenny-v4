const puppeteer = require('puppeteer');
const axios = require('axios');

class N8nWorkflowTester {
  constructor(n8nUrl = 'http://localhost:5678') {
    this.n8nUrl = n8nUrl;
    this.browser = null;
    this.page = null;
  }

  async init() {
    this.browser = await puppeteer.launch({
      headless: false, // Set to true for CI
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    this.page = await this.browser.newPage();
  }

  async testWebhookEndpoint(webhookPath, testData) {
    const url = `${this.n8nUrl}/webhook/${webhookPath}`;
    
    try {
      const response = await axios.post(url, testData, {
        headers: { 'Content-Type': 'application/json' }
      });
      
      console.log(`✅ Webhook test passed: ${webhookPath}`);
      console.log('Response:', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      console.log(`❌ Webhook test failed: ${webhookPath}`);
      console.log('Error:', error.message);
      return { success: false, error: error.message };
    }
  }

  async activateWorkflow(workflowName) {
    await this.page.goto(`${this.n8nUrl}/workflows`);
    
    // Wait for workflow list to load
    await this.page.waitForSelector('[data-test-id="workflow-card"]');
    
    // Find and activate the workflow
    const workflowCard = await this.page.$x(`//div[contains(text(), "${workflowName}")]`);
    if (workflowCard.length > 0) {
      await workflowCard[0].click();
      
      // Look for activation toggle
      await this.page.waitForSelector('[data-test-id="workflow-activate-switch"]');
      const toggle = await this.page.$('[data-test-id="workflow-activate-switch"]');
      
      if (toggle) {
        await toggle.click();
        console.log(`✅ Workflow activated: ${workflowName}`);
        return true;
      }
    }
    
    console.log(`❌ Failed to activate workflow: ${workflowName}`);
    return false;
  }

  async testRouterWorkflow() {
    const testCases = [
      { message: "help me find information about AI", expectedIntent: "search" },
      { message: "what meetings do I have today?", expectedIntent: "calendar" },
      { message: "weekly summary please", expectedIntent: "digest" },
      { message: "who is John Doe?", expectedIntent: "memory" },
      { message: "hello there", expectedIntent: "general" }
    ];

    const results = [];
    
    for (const testCase of testCases) {
      const result = await this.testWebhookEndpoint('kenny-router', testCase);
      
      if (result.success) {
        const intentMatch = result.data.intent === testCase.expectedIntent;
        results.push({
          ...testCase,
          actualIntent: result.data.intent,
          passed: intentMatch,
          response: result.data.response
        });
        
        if (!intentMatch) {
          console.log(`⚠️  Intent mismatch: expected ${testCase.expectedIntent}, got ${result.data.intent}`);
        }
      } else {
        results.push({
          ...testCase,
          passed: false,
          error: result.error
        });
      }
    }
    
    return results;
  }

  async generateReport(results) {
    const report = {
      timestamp: new Date().toISOString(),
      totalTests: results.length,
      passed: results.filter(r => r.passed).length,
      failed: results.filter(r => !r.passed).length,
      details: results
    };
    
    console.log('\n📊 Test Report:');
    console.log(`Total: ${report.totalTests}`);
    console.log(`Passed: ${report.passed}`);
    console.log(`Failed: ${report.failed}`);
    console.log(`Success Rate: ${((report.passed / report.totalTests) * 100).toFixed(1)}%`);
    
    return report;
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

// Usage example
async function runTests() {
  const tester = new N8nWorkflowTester();
  
  try {
    await tester.init();
    
    // Test the router workflow
    const results = await tester.testRouterWorkflow();
    await tester.generateReport(results);
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await tester.cleanup();
  }
}

if (require.main === module) {
  runTests();
}

module.exports = N8nWorkflowTester;