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
  await page.getByRole('textbox', { name: 'Sensor Navn'}).fill('Test Sensor');
  await nextButton.click();

  const sensorEUI = page.getByRole('textbox', { name: 'Sensor EUI'});
  await expect(sensorEUI).toBeVisible();
  await sensorEUI.fill('abcd1234');
  await nextButton.click();

  await expect(page.getByText('Spenningskonfigurasjon')).toBeVisible();
  await page.getByText('230V Enfase').click();
  await nextButton.click();

  await expect(page.getByRole('dialog')).not.toBeVisible({timeout: 2000});
  await expect(page.getByText('Test Sensor')).toBeVisible({timeout: 2000});
});

test('settings: add machine', async ({ page }) => {
  await page.goto('/settings');

  await page.getByRole('tab', { name: 'Maskiner' }).click();

  await page.getByRole('button', { name: 'Legg til Maskin' }).click();

  const machineName = page.getByRole('textbox', { name: 'Maskin navn' });
  await expect(machineName).toBeVisible();
  await machineName.fill('Test Machine');
  
  await page.getByRole('button', { name: 'Opprett maskin'}).click();

  await expect(page.getByRole('dialog')).not.toBeVisible({timeout: 2000});
  await expect(page.getByText('Test Machine')).toBeVisible({timeout: 2000});
});

test('settings: add department', async ({ page }) => {
  await page.goto('/settings');

  await page.getByRole('tab', { name: 'Avdelinger' }).click();

  await page.getByRole('button', { name: 'Ny avdeling' }).click();

  const departmentName = page.getByRole('textbox', { name: 'Navn' });
  await expect(departmentName).toBeVisible();
  await departmentName.fill('Test Department');

  await page.getByRole('button', { name: 'Opprett' }).click();

  await expect(page.getByRole('dialog')).not.toBeVisible({timeout: 2000});
  await expect(page.getByText('Test Department')).toBeVisible({timeout: 2000});
});

test('settings: add erp', async ({ page }) => {
  await page.goto('/settings');

  await page.getByRole('tab', { name: 'ERP' }).click();

  await page.getByRole('button', { name: 'Legg til ERP' }).click();

  const erpName = page.getByPlaceholder('F.eks. SAP Production System');
  await expect(erpName).toBeVisible();
  await erpName.fill('Test System');

  await page.getByText('Velg ERP-type').click();
  await page.getByText('Monitor ERP').click();
  
  const apiEndpoint = page.getByPlaceholder('https://api.example.com/v1');
  await expect(apiEndpoint).toBeVisible();
  await apiEndpoint.fill('https://api.test.com/v1')

  const nextButton = page.getByRole('button', { name: 'Neste' });
  await nextButton.click();

  await expect(page.getByText('Autentiseringstype')).toBeVisible();
  await nextButton.click();

  await expect(page.getByPlaceholder('order_id')).toBeVisible();
  
  await page.getByRole('button', { name: 'Opprett konfigurasjon' }).click();

  await expect(page.getByRole('dialog')).not.toBeVisible({timeout: 2000});
  await expect(page.getByText('Test System')).toBeVisible({timeout: 2000});
});