import { test as base, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    await use(page);

    const coverage = await page.evaluate(() => (window as any).__coverage__);

    if (!coverage) {
      return;
    }

    const dir = path.resolve(
      process.cwd(),
      'logs/coverage/playwright/.nyc_output'
    );

    fs.mkdirSync(dir, { recursive: true });

    const safeTitle = testInfo.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();

    fs.writeFileSync(
      path.join(dir, `coverage-${safeTitle}-${Date.now()}.json`),
      JSON.stringify(coverage)
    );
  },
});

export { expect };