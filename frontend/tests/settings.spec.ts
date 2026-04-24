import { test, expect } from '@playwright/test';

test('settings: page renders', async ({ page }) => {
  await page.goto('/settings');

  await expect(page).not.toHaveURL(/auth\/sign-in/);
  
  const gateways = page.getByRole('tab', { name: 'Gateway' });

  await expect(gateways).toBeVisible();
});

test('settings: add sensor', async ({ page }) => {
  await page.goto('/settings');

  const sensor = page.getByRole('tab', { name: 'Sensor' });
  await sensor.click();

  const addSensor = page.getByRole('button', { name: 'Legg til Sensor' });
  await addSensor.click();

  const nextButton = page.getByRole('button', { name: 'Neste'});

  await page.getByText('3-fase Strømmåler').click();
  await page.getByRole('textbox', { name: 'Sensor Navn'}).fill('Strømmåler');
  await nextButton.click();

  const sensorEUI = page.getByRole('textbox', { name: 'Sensor EUI'});
  await expect(sensorEUI).toBeVisible();
  await sensorEUI.fill('abcd1234');
  await nextButton.click();

  await expect(page.getByText('Spenningskonfigurasjon')).toBeVisible();
  await page.getByText('230V Enfase').click();
  await nextButton.click();

  await expect(page.getByText(/saved|lagret|created|opprettet/i)).toBeVisible();
});

test('settings: add machine', async ({ page }) => {
  await page.goto('/settings');

  await page.getByRole('tab', { name: 'Maskiner' }).click();

  await page.getByRole('button', { name: 'Legg til Maskin' }).click();

  const maskinNavn = page.getByRole('textbox', { name: 'Maskin navn'});
  await expect(maskinNavn).toBeVisible();
  await maskinNavn.fill('maskin1')
  
  await page.getByRole('button', { name: 'Opprett maskin'}).click();

  await expect(page.locator('body')).toContainText(/saved|updated|success|lagret|oppdatert/i);
});