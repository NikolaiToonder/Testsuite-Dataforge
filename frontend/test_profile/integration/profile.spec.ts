import { test, expect } from '@playwright/test';

test.describe('Profile page integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/profile');
  });

  test('renders profile overview', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /profile|profil/i })).toBeVisible();

    await expect(page.locator('body')).toContainText(/John|Doe|Innoveria|Production/i);
    await expect(page.locator('body')).toContainText(/john|example|@/i);
    await expect(page.locator('body')).toContainText(/Oslo/i);
  });

  test('profile fields are disabled before editing', async ({ page }) => {
    await expect(page.locator('#firstName')).toBeDisabled();
    await expect(page.locator('#lastName')).toBeDisabled();
    await expect(page.locator('#email')).toBeDisabled();
    await expect(page.locator('#bio')).toBeDisabled();
  });

  test('clicking edit enables profile fields', async ({ page }) => {
    await page.getByRole('button', { name: /edit profile|rediger profil/i }).click();

    await expect(page.locator('#firstName')).toBeEnabled();
    await expect(page.locator('#lastName')).toBeEnabled();
    await expect(page.locator('#email')).toBeEnabled();
    await expect(page.locator('#bio')).toBeEnabled();
  });

  test('changing first name updates profile overview', async ({ page }) => {
    await page.getByRole('button', { name: /edit profile|rediger profil/i }).click();

    await page.locator('#firstName').fill('Alf');

    await expect(page.locator('body')).toContainText(/Alf Doe|Alf/i);
  });

  test('cancel exits edit mode', async ({ page }) => {
    await page.getByRole('button', { name: /edit profile|rediger profil/i }).click();

    await expect(page.locator('#firstName')).toBeEnabled();

    await page.getByRole('button', { name: /cancel|avbryt/i }).click();

    await expect(page.locator('#firstName')).toBeDisabled();
  });

  test('save exits edit mode', async ({ page }) => {
    await page.getByRole('button', { name: /edit profile|rediger profil/i }).click();

    await page.locator('#firstName').fill('Alf');

    await page.getByRole('button', { name: /save changes|lagre endringer|lagre/i }).click();

    await expect(page.locator('#firstName')).toBeDisabled();
  });

  test('security tab shows security settings', async ({ page }) => {
    await page.getByRole('tab', { name: /security|sikkerhet/i }).click();

    await expect(page.locator('body')).toContainText(/password|passord/i);
    await expect(page.locator('body')).toContainText(/two-factor|2fa|tofaktor/i);
    await expect(page.locator('body')).toContainText(/active sessions|aktive økter|session/i);
  });

  test('activity tab shows activity log', async ({ page }) => {
    await page.getByRole('tab', { name: /activity|aktivitet/i }).click();

    await expect(page.locator('body')).toContainText(/logged in|logget inn/i);
    await expect(page.locator('body')).toContainText(/dashboard|rapport|machine|maskin/i);
  });
});