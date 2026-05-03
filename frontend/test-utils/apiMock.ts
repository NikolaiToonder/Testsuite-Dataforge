import { vi } from 'vitest';

const jsonResponse = (data: any, ok = true) => ({
  ok,
  status: ok ? 200 : 400,
  json: vi.fn().mockResolvedValue(data),
});

export const apiClientMock = {
  list_gateways: vi.fn(),
  list_sensors: vi.fn(),
  get_sensor_data: vi.fn(),
  get_my_machines: vi.fn(),
  list_departments: vi.fn(),
  list_invitations: vi.fn(),
  list_tenant_users: vi.fn(),
  list_erp_configurations: vi.fn(),

  create_department: vi.fn(),
  update_department: vi.fn(),
  delete_department: vi.fn(),

  update_tenant_user: vi.fn(),

  test_erp_configuration: vi.fn(),
  delete_erp_configuration: vi.fn(),

  create_my_machine: vi.fn(),
  delete_my_machine: vi.fn(),
  update_my_machine: vi.fn(),

  delete_gateway: vi.fn(),
  update_sensor: vi.fn(),

  invite_user: vi.fn(),
  cancel_invitation: vi.fn(),
};

export function resetSettingsApiMocks() {
  Object.values(apiClientMock).forEach((mock) => mock.mockReset());

  apiClientMock.list_gateways.mockResolvedValue(
    jsonResponse([
      {
        id: 'gateway-1',
        name: 'Main Gateway',
        gateway_eui: 'GW-001',
        description: 'Factory gateway',
        department: 'Production',
        created_at: '2025-01-01T00:00:00Z',
      },
    ])
  );

  apiClientMock.list_sensors.mockResolvedValue(
    jsonResponse([
      {
        id: 'sensor-1',
        name: 'Temperatursensor',
        sensor_eui: 'SENSOR-001',
        sensor_type: 'temperature',
        machine_id: null,
        battery_level: 90,
        signal_strength: -70,
        created_at: '2025-01-01T00:00:00Z',
        last_seen: new Date().toISOString(),
      },
    ])
  );

  apiClientMock.get_sensor_data.mockResolvedValue(jsonResponse([]));

  apiClientMock.get_my_machines.mockResolvedValue(
    jsonResponse({
      machines: [
        {
          id: 'machine-1',
          eui: 'MACHINE-001',
          name: 'CNC Machine',
          machine_type: 'CNC',
          description: 'Main CNC machine',
          department: 'Production',
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
    })
  );

  apiClientMock.list_departments.mockResolvedValue(
    jsonResponse([
      {
        id: 'department-1',
        name: 'Production',
        description: 'Production department',
      },
    ])
  );

  apiClientMock.list_invitations.mockResolvedValue(
    jsonResponse({
      invitations: [
        {
          id: 'invitation-1',
          email: 'invited@example.com',
          role: 'customer_user',
          status: 'pending',
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
    })
  );

  apiClientMock.list_tenant_users.mockResolvedValue(
    jsonResponse({
      users: [
        {
          id: 'user-1',
          email: 'active@example.com',
          display_name: 'Active User',
          role: 'customer_user',
          joined_at: '2025-01-01T00:00:00Z',
        },
      ],
    })
  );

  apiClientMock.list_erp_configurations.mockResolvedValue(
    jsonResponse([
      {
        id: '1',
        name: 'Business Central',
        erp_type: 'business_central',
        api_endpoint: 'https://api.example.com',
        sync_frequency: 'Daglig',
        created_at: '2025-01-01T00:00:00Z',
      },
    ])
  );

  apiClientMock.invite_user.mockResolvedValue(
    jsonResponse({ id: 'new-invitation' })
  );

  apiClientMock.test_erp_configuration.mockResolvedValue(
    jsonResponse({ success: true })
  );

  apiClientMock.delete_erp_configuration.mockResolvedValue(
    jsonResponse({})
  );
}