import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  testDir: './tests', timeout: 120000, workers: 1, expect: {timeout:30000},
  use: {baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:3000', trace: 'retain-on-failure'},
  projects: [
    {name:'desktop',use:{...devices['Desktop Chrome']}},
    {name:'mobile',use:{...devices['iPhone 13'], defaultBrowserType:'chromium'}},
  ],
})
