import { test, expect } from '@playwright/test';

test('profile: page renders', async ({ page }) => {
  await page.goto('/profile');

  await expect(page).not.toHaveURL(/auth\/sign-in/);
  await expect(page.locator('#firstName')).toBeVisible();
});

test('profile: edit and save', async ({ page }) => {
  await page.goto('/profile');

  await expect(page).not.toHaveURL(/auth\/sign-in/);

  const firstName = page.locator('#firstName');
  await expect(firstName).toBeVisible();

  if (!(await firstName.isEnabled())) {
    const editButton = page.getByRole('button', { name: /edit|rediger|endre/i });
    await expect(editButton).toBeVisible();
    await editButton.click();
    await expect(firstName).toBeEnabled();
  }

  await firstName.fill('Jane');

  const saveButton = page.getByRole('button', { name: /save|lagre|save changes/i });
  await expect(saveButton).toBeVisible();
  await saveButton.click();

  await expect(page.locator('body')).toContainText(/saved|updated|success|lagret|oppdatert/i);
});