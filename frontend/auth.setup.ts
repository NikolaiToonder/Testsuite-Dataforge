import { test, expect } from '@playwright/test';

test('authenticate', async ({ page, context }) => {
  const email = process.env.TEST_EMAIL;
  const password = process.env.TEST_PASSWORD;

  if (!email) throw new Error('Missing EMAIL');
  if (!password) throw new Error('Missing PASSWORD');

  await page.goto('/auth/sign-in?next=%2Fprofile');

  await page.getByRole('textbox', { name: /email/i }).fill(email);
  await page.getByRole('textbox', { name: /password/i }).fill(password);
  await page.locator('button[type="submit"]').click();

  await expect
    .poll(async () => {
      const cookies = await context.cookies();
      return cookies.some(c => c.name.startsWith('stack-access') || c.name.startsWith('stack-refresh'));
    })
    .toBeTruthy();

  await page.goto('/profile');
  await expect(page).not.toHaveURL(/auth\/sign-in/);

  await context.storageState({ path: 'playwright/.auth/state.json' });
});