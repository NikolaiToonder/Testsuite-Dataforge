import { vi } from 'vitest';
import './mocks';

vi.mock('app', async () => {
  const { apiClientMock } = await import('./apiMock');

  return {
    apiClient: apiClientMock,
  };
});

vi.mock('app/auth', () => ({
  useUserGuardContext: () => ({
    user: {
      displayName: 'Admin User',
      primaryEmail: 'admin@example.com',
    },
  }),
}));

vi.mock('@/apiclient/data-contracts', () => ({
  UserRole: {
    CustomerUser: 'customer_user',
  },
}));

vi.mock('@/components/ui/table', () => ({
  Table: ({ children }: any) => <table>{children}</table>,
  TableBody: ({ children }: any) => <tbody>{children}</tbody>,
  TableCell: ({ children }: any) => <td>{children}</td>,
  TableHead: ({ children }: any) => <th>{children}</th>,
  TableHeader: ({ children }: any) => <thead>{children}</thead>,
  TableRow: ({ children }: any) => <tr>{children}</tr>,
}));

vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ open, children }: any) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
}));

vi.mock('@/components/ui/select', () => ({
  Select: ({ children }: any) => <div>{children}</div>,
  SelectTrigger: ({ children }: any) => <button>{children}</button>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
}));

vi.mock('components/AddGatewayDialog', () => ({
  AddGatewayDialog: ({ isOpen }: any) =>
    isOpen ? <div data-testid="add-gateway-dialog">Add Gateway Dialog</div> : null,
}));

vi.mock('components/EditGatewayDialog', () => ({
  EditGatewayDialog: ({ open }: any) =>
    open ? <div data-testid="edit-gateway-dialog">Edit Gateway Dialog</div> : null,
}));

vi.mock('components/AddSensorDialog', () => ({
  AddSensorDialog: ({ open }: any) =>
    open ? <div data-testid="add-sensor-dialog">Add Sensor Dialog</div> : null,
}));

vi.mock('components/EditSensorDialog', () => ({
  EditSensorDialog: ({ open }: any) =>
    open ? <div data-testid="edit-sensor-dialog">Edit Sensor Dialog</div> : null,
}));

vi.mock('components/AddMachineDialog', () => ({
  AddMachineDialog: ({ open }: any) =>
    open ? <div data-testid="add-machine-dialog">Add Machine Dialog</div> : null,
}));

vi.mock('components/AddErpConfigDialog', () => ({
  AddErpConfigDialog: ({ open }: any) =>
    open ? <div data-testid="add-erp-dialog">Add ERP Dialog</div> : null,
}));

vi.mock('components/EditErpConfigDialog', () => ({
  EditErpConfigDialog: ({ open }: any) =>
    open ? <div data-testid="edit-erp-dialog">Edit ERP Dialog</div> : null,
}));

vi.mock('components/AssignSensorToMachine', () => ({
  AssignSensorToMachine: () => <button>Assign Sensor</button>,
}));

vi.mock('components/AssignSensorsToMachine', () => ({
  AssignSensorsToMachine: () => <button>Assign Sensors</button>,
}));

vi.mock('components/SensorMiniChart', () => ({
  SensorMiniChart: () => <div data-testid="sensor-mini-chart" />,
}));

vi.mock('components/DepartmentSettings', () => ({
  DepartmentSettings: ({ departments }: any) => (
    <div>
      <h2>Department Settings Mock</h2>
      <p>Departments: {departments.length}</p>
    </div>
  ),
}));

vi.mock('components/TenantInfoCard', () => ({
  TenantInfoCard: () => <div data-testid="tenant-info-card" />,
}));

vi.mock('components/MachineDetailsSheet', () => ({
  MachineDetailsSheet: ({ open }: any) =>
    open ? <div data-testid="machine-details-sheet">Machine Details</div> : null,
}));