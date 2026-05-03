import React from 'react';
import { vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (key === 'profile.security.passwordLastChanged') {
        return `profile.security.passwordLastChanged ${params?.days}`;
      }

      if (key === 'profile.security.hoursAgo') {
        return `profile.security.hoursAgo ${params?.hours}`;
      }

      return key;
    },
  }),
}));

vi.mock('app/auth', () => ({
  useUserGuardContext: () => ({
    user: {
      displayName: 'John Doe',
      primaryEmail: 'john@example.com',
      profileImageUrl: null,
    },
  }),
}));

vi.mock('components/Layout', () => ({
  Layout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="layout">{children}</div>
  ),
}));

vi.mock('lucide-react', () => ({
  User: () => <span data-testid="icon-user" />,
  Mail: () => <span />,
  Phone: () => <span />,
  MapPin: () => <span />,
  Camera: () => <span data-testid="camera-icon" />,
  Shield: () => <span />,
  Key: () => <span />,
  Activity: () => <span />,
  Calendar: () => <span />,
  Edit: () => <span />,
  Save: () => <span />,
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: any) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock('@/components/ui/input', () => ({
  Input: (props: any) => <input {...props} />,
}));

vi.mock('@/components/ui/label', () => ({
  Label: ({ children, ...props }: any) => (
    <label {...props}>{children}</label>
  ),
}));

vi.mock('@/components/ui/textarea', () => ({
  Textarea: (props: any) => <textarea {...props} />,
}));

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: any) => <div>{children}</div>,
  CardHeader: ({ children }: any) => <div>{children}</div>,
  CardTitle: ({ children }: any) => <h2>{children}</h2>,
  CardContent: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@/components/ui/avatar', () => ({
  Avatar: ({ children }: any) => <div>{children}</div>,
  AvatarImage: () => null,
  AvatarFallback: ({ children }: any) => (
    <div data-testid="avatar-fallback">{children}</div>
  ),
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));

vi.mock('@/components/ui/separator', () => ({
  Separator: () => <hr />,
}));

vi.mock('@/components/ui/tabs', () => {
  const React = require('react');

  return {
    Tabs: ({ value, onValueChange, children }: any) => (
      <div data-testid="tabs" data-value={value}>
        {React.Children.map(children, (child: any) =>
          React.isValidElement(child)
            ? React.cloneElement(child, { activeValue: value, onValueChange })
            : child
        )}
      </div>
    ),

    TabsList: ({ children, activeValue, onValueChange }: any) => (
      <div>
        {React.Children.map(children, (child: any) =>
          React.isValidElement(child)
            ? React.cloneElement(child, { activeValue, onValueChange })
            : child
        )}
      </div>
    ),

    TabsTrigger: ({ value, children, onValueChange }: any) => (
      <button type="button" onClick={() => onValueChange(value)}>
        {children}
      </button>
    ),

    TabsContent: ({ value, activeValue, children }: any) =>
      value === activeValue ? <div>{children}</div> : null,
  };
});