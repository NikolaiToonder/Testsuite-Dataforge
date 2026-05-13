import '../../test-utils/profileMocks';

import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test } from 'vitest';
import { toast } from 'sonner';

const { default: Profile } = await import(
  '../../../../dataforge/frontend/src/pages/Profile'
);

describe('Profile page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders profile data from user context', () => {
    const { getByText, getByTestId } = render(<Profile />);

    expect(getByText('profile.title')).toBeInTheDocument();
    expect(getByText('John Doe')).toBeInTheDocument();
    expect(getByText('john@example.com')).toBeInTheDocument();
    expect(getByTestId('avatar-fallback')).toHaveTextContent('JD');
  });

  test('profile inputs are disabled by default', () => {
    const { getByLabelText } = render(<Profile />);

    expect(getByLabelText('profile.personalInfo.firstName')).toBeDisabled();
    expect(getByLabelText('profile.personalInfo.lastName')).toBeDisabled();
    expect(getByLabelText('profile.personalInfo.email')).toBeDisabled();
    expect(getByLabelText('profile.personalInfo.bio')).toBeDisabled();
  });

  test('clicking edit enables profile inputs', async () => {
    const { getByLabelText, getByRole } = render(<Profile />);

    await userEvent.click(
      getByRole('button', { name: /profile.editProfile/i })
    );

    expect(getByLabelText('profile.personalInfo.firstName')).toBeEnabled();
    expect(getByLabelText('profile.personalInfo.lastName')).toBeEnabled();
    expect(getByLabelText('profile.personalInfo.email')).toBeEnabled();
    expect(getByLabelText('profile.personalInfo.bio')).toBeEnabled();
  });

  test('changing first name updates profile overview', async () => {
    const { getByLabelText, getByRole, getByText } = render(<Profile />);

    await userEvent.click(
      getByRole('button', { name: /profile.editProfile/i })
    );

    const firstNameInput = getByLabelText('profile.personalInfo.firstName');

    await userEvent.clear(firstNameInput);
    await userEvent.type(firstNameInput, 'Alf');

    expect(getByText('Alf Doe')).toBeInTheDocument();
    expect(getByText('AD')).toBeInTheDocument();
  });

  test('cancel exits edit mode without success toast', async () => {
    const { getByLabelText, getByRole } = render(<Profile />);

    await userEvent.click(
      getByRole('button', { name: /profile.editProfile/i })
    );

    expect(getByLabelText('profile.personalInfo.firstName')).toBeEnabled();

    await userEvent.click(
      getByRole('button', { name: /profile.cancel/i })
    );

    expect(getByLabelText('profile.personalInfo.firstName')).toBeDisabled();
    expect(toast.success).not.toHaveBeenCalled();
  });

  test('save edit shows success toast', async () => {
    const { getByLabelText, getByRole } = render(<Profile />);

    await userEvent.click(
      getByRole('button', { name: /profile.editProfile/i })
    );

    await userEvent.click(
      getByRole('button', { name: /profile.saveChanges/i })
    );

    expect(getByLabelText('profile.personalInfo.firstName')).toBeDisabled();

    expect(toast.success).toHaveBeenCalledWith(
      'profile.profileUpdated'
    );
  });

  test('switches to security tab', async () => {
    const { getByRole, getByText } = render(<Profile />);

    await userEvent.click(
      getByRole('button', { name: /profile.tabs.security/i })
    );

    expect(getByText('profile.security.title')).toBeInTheDocument();
    expect(getByText('profile.security.password')).toBeInTheDocument();
    expect(getByText('profile.security.twoFactor')).toBeInTheDocument();
    expect(getByText('profile.security.activeSessions')).toBeInTheDocument();
  });

  test('renders activity log', async () => {
    const { getByRole, getByText } = render(<Profile />);

    await userEvent.click(
      getByRole('button', { name: /profile.tabs.activity/i })
    );

    expect(getByText('profile.activity.title')).toBeInTheDocument();
    expect(getByText('profile.activity.actions.loggedIn')).toBeInTheDocument();
    expect(getByText('profile.activity.details.desktopBrowser')).toBeInTheDocument();
  });
});