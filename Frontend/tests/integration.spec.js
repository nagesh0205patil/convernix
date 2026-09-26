import { test, expect } from '@playwright/test';

test('Convernix desktop and mobile sign-in preserve the theme and existing API contract', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/api/auth/providers/', route => route.fulfill({ json: { password: true, google: { enabled: false }, microsoft: { enabled: false } } }));
  await page.route('**/api/auth/login/', async route => {
    expect(route.request().method()).toBe('POST');
    expect(route.request().postDataJSON()).toEqual({ email: 'member@example.com', password: 'test-password' });
    await route.fulfill({ status: 401, json: { detail: 'Incorrect email or password' } });
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('One WhatsApp number');
  await expect(page.locator('.convernix-site')).toHaveCSS('background-color', 'rgb(11, 13, 20)');
  await page.getByRole('button', { name: 'Sign in', exact: true }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: /Continue with Google/ })).toBeDisabled();
  await expect(dialog.getByRole('button', { name: /Continue with Microsoft/ })).toBeDisabled();
  await expect(dialog.getByRole('button', { name: /Sign up to create company workspace/i })).toBeVisible();
  await dialog.getByLabel('Email address').fill('member@example.com');
  await dialog.getByLabel('Password', { exact: true }).fill('test-password');
  await dialog.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(dialog.getByRole('alert')).toHaveText('Incorrect email or password');
  await page.screenshot({ path: 'test-results/signin-desktop.png' });
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('.mobile-toggle').click();
  await page.locator('.mobile-actions').getByRole('button', { name: /Sign in/i }).click();
  await expect(dialog).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/signin-mobile.png' });
  expect(errors).toEqual([]);
});

test('successful sign-in opens the existing business selector and sign-out returns home', async ({ page }) => {
  await page.route('**/api/**', async route => {
    const url = route.request().url();
    if (url.endsWith('/auth/login/')) return route.fulfill({ json: { access: 'test-token', user: { email: 'member@example.com', number_access: 'both' } } });
    if (url.endsWith('/auth/me/')) {
      expect(route.request().headers().authorization).toBe('Bearer test-token');
      return route.fulfill({ json: { email: 'member@example.com', number_access: 'both' } });
    }
    if (url.endsWith('/whatsapp/business-numbers/')) return route.fulfill({ json: [] });
    return route.fulfill({ json: { google: { enabled: false }, microsoft: { enabled: false } } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Sign in', exact: true }).first().click();
  await page.getByLabel('Email address').fill('member@example.com');
  await page.getByLabel('Password', { exact: true }).fill('test-password');
  await page.getByRole('dialog').getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('.crm-workspace')).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('crm_access_token'))).toBe('test-token');
  await page.getByRole('button', { name: /Sign out/i }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('One WhatsApp number');
});

test('newly registered workspace shows enterprise administration console', async ({ page }) => {
  await page.route('**/api/**', async route => {
    const url = route.request().url();
    if (url.endsWith('/auth/login/')) {
      return route.fulfill({ json: { access: 'test-token', user: { email: 'member@example.com', number_access: 'both' } } });
    }
    if (url.endsWith('/auth/me/')) {
      return route.fulfill({ json: { email: 'member@example.com', number_access: 'both', role: 'owner', team_name: 'Operations' } });
    }
    if (url.endsWith('/whatsapp/business-numbers/')) {
      return route.fulfill({ json: [{ id: 101, label: 'Cloudtronix Support', number: '+91 98765 43210' }] });
    }
    if (url.endsWith('/tenant/me/')) {
      return route.fulfill({ json: { name: 'Cloudtronix Demo Pvt Ltd', tier: 'mid', tier_display: 'Professional' } });
    }
    return route.fulfill({ json: { google: { enabled: false }, microsoft: { enabled: false } } });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Sign in', exact: true }).first().click();
  await page.getByLabel('Email address').fill('member@example.com');
  await page.getByLabel('Password', { exact: true }).fill('test-password');
  await page.getByRole('dialog').getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('.crm-workspace')).toBeVisible();
  await page.getByRole('button', { name: 'Cloudtronix Support' }).click();
  await page.getByRole('button', { name: 'Administration' }).click();

  await expect(page.getByRole('heading', { name: 'Administration' }).first()).toBeVisible();
  await expect(page.getByText('Complete your account setup')).toBeVisible();
  await expect(page.getByText('WhatsApp Connection')).toBeVisible();
  await expect(page.getByText('Manage users')).toBeVisible();
});

test('pricing section renders INR plans, toggles billing cycle, and preselects registration tier', async ({ page }) => {
  await page.route('**/api/**', async route => {
    route.fulfill({ json: { password: true, google: { enabled: false }, microsoft: { enabled: false } } });
  });
  await page.goto('/');

  // Verify Pricing is NOT shown on the main landing page
  await expect(page.locator('#pricing')).not.toBeVisible();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('One WhatsApp number');

  // Verify Navbar Pricing link points to #pricing
  const pricingNav = page.getByRole('link', { name: 'Pricing' }).first();
  await expect(pricingNav).toHaveAttribute('href', '#pricing');

  // Click Pricing to open the separate pricing page
  await pricingNav.click();

  // Verify we are now on the dedicated Pricing page and main landing hero is hidden
  const pricingPage = page.locator('#pricing');
  await expect(pricingPage).toBeVisible();
  await expect(page.getByText('Back to Home')).toBeVisible();
  await expect(pricingPage).toContainText('Simple plans in INR');

  // Verify 15-day trial hero badge
  await expect(pricingPage).toContainText('15-day free trial. No credit card required.');

  // Verify Monthly Prices in INR (Basic: ₹2,499, Standard: ₹6,499, Premium: ₹8,499)
  await expect(pricingPage).toContainText('₹2,499');
  await expect(pricingPage).toContainText('₹6,499');
  await expect(pricingPage).toContainText('₹8,499');

  // Verify Storage quotas in comparison table
  await expect(pricingPage.getByText('Compare plans and features')).toBeVisible();
  await expect(pricingPage.getByText('5 GB', { exact: true })).toBeVisible();
  await expect(pricingPage.getByText('10 GB', { exact: true })).toBeVisible();
  await expect(pricingPage.getByText('15 GB', { exact: true })).toBeVisible();

  // Toggle to Annual Billing (Save 20%: Basic ₹1,999, Standard ₹5,199, Premium ₹6,799)
  const annualBtn = pricingPage.getByRole('button', { name: 'Annual Billing' });
  await annualBtn.click();
  await expect(pricingPage).toContainText('₹1,999');
  await expect(pricingPage).toContainText('₹5,199');
  await expect(pricingPage).toContainText('₹6,799');

  // Click Start 15-Day Free Trial on Standard (mid) tier
  const standardCard = pricingPage.locator('.pricing-card.featured');
  await standardCard.getByRole('button', { name: /Start 15-Day Free Trial/i }).click();

  // Verify Dialog opens with Create Company Workspace and Standard tier selected
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('Create Company Workspace').first()).toBeVisible();
  const midOption = dialog.locator('.pm-tier-option-card.selected');
  await expect(midOption).toContainText('Standard');
  await expect(midOption).toContainText('10 GB Storage');

  // Verify option to switch to Sign in from Signup popup
  const signInSwitch = dialog.getByRole('button', { name: /Sign in to existing workspace/i });
  await expect(signInSwitch).toBeVisible();
  await signInSwitch.click();
  await expect(dialog.getByText('Welcome back.').first()).toBeVisible();
  await expect(dialog.getByLabel('Email address')).toBeVisible();

  // Verify option to switch back to Signup from Signin popup
  const signUpSwitch = dialog.getByRole('button', { name: /Sign up to create company workspace/i });
  await expect(signUpSwitch).toBeVisible();
  await signUpSwitch.click();
  await expect(dialog.getByText('Create Company Workspace').first()).toBeVisible();

  // Close dialog and verify navigating Back to Home returns to main landing page
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await page.getByRole('button', { name: /Back to Home/i }).click();
  await expect(page.locator('#pricing')).not.toBeVisible();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('One WhatsApp number');
});

