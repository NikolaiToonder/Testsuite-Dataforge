import { test, expect } from '@playwright/test';

test.describe('Settings page integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('renders settings page and system overview', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: 'Innstillinger' })
    ).toBeVisible();

    await expect(
      page.getByText('Administrer system, brukere og integrasjoner')
    ).toBeVisible();

    await expect(
      page.getByRole('heading', { name: 'Systemoversikt' })
    ).toBeVisible();

    await expect(page.getByText('Aktive gateways')).toBeVisible();
    await expect(page.getByText('Registrerte sensorer')).toBeVisible();
    await expect(page.getByText('Registrerte maskiner')).toBeVisible();
    await expect(page.getByText('Registrerte avdelinger')).toBeVisible();
  });

  test('can switch to sensors tab', async ({ page }) => {
    await page.getByRole('tab', { name: 'Sensorer' }).click();

    await expect(
      page.getByRole('heading', { name: 'Sensorer' })
    ).toBeVisible();

    await expect(page.getByText('Administrer sensorer')).toBeVisible();
  });

  test('can switch to machines tab', async ({ page }) => {
    await page.getByRole('tab', { name: 'Maskiner' }).click();

    await expect(
      page.getByRole('heading', { name: 'Maskiner' })
    ).toBeVisible();

    await expect(page.getByText('Administrer maskiner')).toBeVisible();
  });

  test('can switch to departments tab', async ({ page }) => {
    await page.getByRole('tab', { name: 'Avdelinger' }).click();

    await expect(page.locator('body')).toContainText(/Avdeling|Avdelinger/i);
  });

  test('can switch to users tab and see invite form', async ({ page }) => {
    await page.getByRole('tab', { name: 'Brukere' }).click();

    await expect(
      page.getByRole('heading', { name: 'Din konto' })
    ).toBeVisible();

    await expect(
      page.getByRole('heading', { name: 'Inviter bruker' })
    ).toBeVisible();

    await expect(
      page.getByPlaceholder('E-postadresse')
    ).toBeVisible();

    await expect(
      page.getByRole('button', { name: /Send invitasjon/i })
    ).toBeDisabled();
  });

  test('invite button becomes enabled when email is entered', async ({ page }) => {
    await page.getByRole('tab', { name: 'Brukere' }).click();

    const emailInput = page.getByPlaceholder('E-postadresse');
    const inviteButton = page.getByRole('button', { name: /Send invitasjon/i });

    await expect(inviteButton).toBeDisabled();

    await emailInput.fill('newuser@example.com');

    await expect(inviteButton).toBeEnabled();
  });

  test('can switch to ERP tab and open add ERP dialog', async ({ page }) => {
    await page.getByRole('tab', { name: 'ERP' }).click();

    await expect(
      page.getByRole('heading', { name: 'ERP Integrasjoner' })
    ).toBeVisible();

    await page.getByRole('button', { name: /Legg til ERP/i }).click();

    await expect(page.locator('body')).toContainText(/ERP/i);
    await expect(page.locator('body')).toContainText(/Navn|ERP Type|API Endpoint/i);
  });

  test('ERP add dialog requires ERP information', async ({ page }) => {
    await page.getByRole('tab', { name: 'ERP' }).click();

    await page.getByRole('button', { name: /Legg til ERP/i }).click();

    await expect(page.locator('body')).toContainText(/ERP/i);

    const nameInput = page.getByPlaceholder(/SAP Production System|F.eks/i);

    await expect(nameInput).toBeVisible();

    await nameInput.fill('Test ERP');

    await expect(nameInput).toHaveValue('Test ERP');
  });

  test('gateway tab currently shows overview', async ({ page }) => {
    await page.getByRole('tab', { name: 'Gateways' }).click();

    await expect(
      page.getByRole('heading', { name: 'Systemoversikt' })
    ).toBeVisible();

    await expect(page.getByText('Aktive gateways')).toBeVisible();
  });
});