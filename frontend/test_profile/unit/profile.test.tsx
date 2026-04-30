import '../../test-utils/mocks';

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const { default: Profile } = await import(
  '../../../../dataforge/frontend/src/pages/Profile'
);

describe('Profile page', () => {
  test('inputs are disabled by default and enabled after clicking edit', async () => {
    render(<Profile />);

    const firstNameInput = screen.getByLabelText('profile.personalInfo.firstName');

    expect(firstNameInput).toBeDisabled();

    await userEvent.click(
      screen.getByRole('button', { name: /profile.editProfile/i })
    );

    expect(firstNameInput).toBeEnabled();
  });
});