import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' })

export default defineConfig({
  testDir: '.',
  testMatch: ['**/end-to-end/**/*.spec.ts', '**/integration/**/*.spec.ts'],
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
      use: {
        baseURL: 'http://localhost:5173',
      },
    },
    {
      name: 'chromium',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:5173',
        storageState: 'playwright/.auth/state.json',
      },
    },
  ],
});