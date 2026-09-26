import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: { baseURL: 'http://127.0.0.1:3000', headless: true },
  reporter: 'list',
  webServer: { command: 'node serve.cjs', url: 'http://127.0.0.1:3000', reuseExistingServer: true },
});
