-- Test database schema for Dataforge
-- Derived from SQL queries across the codebase

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core multi-tenant table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT true,
    settings JSONB NOT NULL DEFAULT '{}',
    tenant_type TEXT NOT NULL DEFAULT 'factory',
    parent_tenant_id UUID REFERENCES tenants(id),
    display_name TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'
);

-- Departments within tenants
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#6B7280',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT true
);

-- Machines (sensor devices per tenant)
CREATE TABLE machines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    eui TEXT NOT NULL,
    name TEXT NOT NULL,
    location TEXT DEFAULT '',
    max_expected_amps FLOAT DEFAULT 50.0,
    min_expected_amps FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}',
    department_id UUID REFERENCES departments(id),
    erp_work_center_id TEXT
);

-- User-tenant-role mapping
CREATE TABLE tenant_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stack_user_id TEXT NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    role TEXT NOT NULL DEFAULT 'customer_user',
    permissions JSONB DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(stack_user_id, tenant_id)
);

-- Super admin list (Innoveria employees)
CREATE TABLE super_admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User invitations
CREATE TABLE user_invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    invited_by TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer_user',
    invitation_token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    used_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- LoRaWAN gateways
CREATE TABLE gateways (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    description TEXT,
    gateway_eui TEXT NOT NULL,
    location TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'active',
    last_seen_at TIMESTAMPTZ,
    firmware_version TEXT,
    hardware_version TEXT,
    network_config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    department_id UUID REFERENCES departments(id)
);

-- Individual sensor devices
CREATE TABLE sensors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    gateway_id UUID REFERENCES gateways(id),
    sensor_type TEXT NOT NULL DEFAULT 'power_3phase',
    sensor_eui TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    location TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    model TEXT,
    firmware_version TEXT,
    hardware_version TEXT,
    sampling_rate_seconds INTEGER DEFAULT 60,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    precision_digits INTEGER DEFAULT 2,
    unit TEXT,
    scale_factor DOUBLE PRECISION DEFAULT 1.0,
    offset_value DOUBLE PRECISION DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'active',
    last_seen_at TIMESTAMPTZ,
    battery_level INTEGER,
    signal_strength INTEGER,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    connectivity_status TEXT DEFAULT 'unknown',
    last_data_at TIMESTAMPTZ,
    signal_quality TEXT,
    data_category TEXT,
    voltage_type TEXT,
    deleted_at TIMESTAMPTZ
);

-- Sensor readings (time-series data)
CREATE TABLE sensor_readings (
    id SERIAL PRIMARY KEY,
    sensor_eui TEXT NOT NULL,
    machine_name TEXT,
    machine_id UUID REFERENCES machines(id),
    tenant_id UUID REFERENCES tenants(id),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rms_amps DOUBLE PRECISION,
    max_amps DOUBLE PRECISION,
    min_amps DOUBLE PRECISION,
    amp_hour_accumulation DOUBLE PRECISION,
    capacitor_voltage DOUBLE PRECISION,
    temperature DOUBLE PRECISION,
    signal_strength INTEGER,
    battery_status TEXT,
    raw_payload BYTEA,
    power_kw DOUBLE PRECISION,
    rssi INTEGER,
    snr DOUBLE PRECISION
);

CREATE INDEX idx_sensor_readings_eui_ts ON sensor_readings(sensor_eui, timestamp DESC);
CREATE INDEX idx_sensor_readings_tenant_ts ON sensor_readings(tenant_id, timestamp DESC);
CREATE INDEX idx_sensor_readings_machine_ts ON sensor_readings(machine_id, timestamp DESC);

-- Tenant-scoped view for sensor readings joined with machine/tenant info
CREATE VIEW tenant_machine_readings AS
SELECT
    sr.*,
    t.slug AS tenant_slug
FROM sensor_readings sr
JOIN machines m ON sr.sensor_eui = m.eui
JOIN tenants t ON m.tenant_id = t.id;

-- Legacy user dashboard layouts
CREATE TABLE user_dashboard_layouts (
    user_id TEXT PRIMARY KEY,
    layout_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Named dashboard layouts
CREATE TABLE named_dashboard_layouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    layout_data JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_system_template BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Production context tracking
CREATE TABLE production_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    machine_id UUID NOT NULL REFERENCES machines(id),
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    context_type TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
