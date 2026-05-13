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

vi.mock('components/Layout', () => ({
  Layout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="layout">{children}</div>
  ),
}));

vi.mock('lucide-react', () => {
  const Icon = (props: any) => <span data-testid="icon" {...props} />;

  return {
    Settings: Icon,
    User: Icon,
    Mail: Icon,
    Phone: Icon,
    MapPin: Icon,
    Camera: (props: any) => <span data-testid="camera-icon" {...props} />,
    Shield: Icon,
    Key: Icon,
    Activity: Icon,
    Calendar: Icon,
    Edit: Icon,
    Save: Icon,
    Router: Icon,
    Database: Icon,
    Users: Icon,
    UserPlus: Icon,
    Trash2: Icon,
    Plus: Icon,
    AlertCircle: Icon,
    Wifi: Icon,
    WifiOff: Icon,
    Factory: Icon,
    Building: Icon,
    Monitor: Icon,
    Cpu: Icon,
    Battery: Icon,
    Thermometer: Icon,
  };
});

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, variant, size, ...props }: any) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: any) => <div>{children}</div>,
  CardHeader: ({ children }: any) => <div>{children}</div>,
  CardTitle: ({ children }: any) => <h2>{children}</h2>,
  CardContent: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));

vi.mock('@/components/ui/input', () => ({
  Input: (props: any) => <input {...props} />,
}));

vi.mock('@/components/ui/tabs', () => ({
  Tabs: ({ value, onValueChange, children }: any) => (
    <div data-testid="tabs" data-value={value}>
      {React.Children.map(children, (child) =>
        React.isValidElement(child)
          ? React.cloneElement(child as React.ReactElement<any>, {
              activeValue: value,
              onValueChange,
            })
          : child
      )}
    </div>
  ),

  TabsList: ({ children, activeValue, onValueChange }: any) => (
    <div>
      {React.Children.map(children, (child) =>
        React.isValidElement(child)
          ? React.cloneElement(child as React.ReactElement<any>, {
              activeValue,
              onValueChange,
            })
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
}));