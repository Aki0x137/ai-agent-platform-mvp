-- FinAgent MVP - PostgreSQL initialization script

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Agent Registry Table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    version INT DEFAULT 1,
    system_prompt TEXT NOT NULL,
    model_policy VARCHAR(50) NOT NULL DEFAULT 'hybrid' CHECK (model_policy IN ('sensitive', 'general', 'hybrid')),
    max_session_hours INT DEFAULT 4,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_is_active ON agents(is_active);

-- Connectors Registry
CREATE TABLE IF NOT EXISTS connectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('postgresql', 'rest_api', 'inmemory', 'mcp', 'logs', 'sandbox')),
    config JSONB NOT NULL,
    credentials_vault_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_connectors_type ON connectors(type);

-- Agent-Connector Mappings
CREATE TABLE IF NOT EXISTS agent_connectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    connector_id UUID NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    allowed_operations VARCHAR(50)[] DEFAULT ARRAY['read'],
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_id, connector_id)
);

CREATE INDEX idx_agent_connectors_agent_id ON agent_connectors(agent_id);
CREATE INDEX idx_agent_connectors_connector_id ON agent_connectors(connector_id);

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'paused')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(255),
    input_params JSONB,
    output_result JSONB,
    error_message TEXT,
    total_tool_calls INT DEFAULT 0,
    total_tokens_used INT DEFAULT 0
);

CREATE INDEX idx_sessions_agent_id ON sessions(agent_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_sessions_created_by ON sessions(created_by);

-- Tool Calls Log
CREATE TABLE IF NOT EXISTS tool_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    input_params JSONB NOT NULL,
    output_data JSONB,
    execution_duration_ms INT,
    model_used VARCHAR(100),
    routing_policy VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    order_index INT NOT NULL
);

CREATE INDEX idx_tool_calls_session_id ON tool_calls(session_id);
CREATE INDEX idx_tool_calls_tool_name ON tool_calls(tool_name);
CREATE INDEX idx_tool_calls_created_at ON tool_calls(created_at DESC);

-- Demo Data Tables (for settlement reconciliation demo)
-- NOTE: Full seed data will be generated in P0.2 via data/generate_mock_data.py

CREATE TABLE IF NOT EXISTS demo_internal_payouts (
    id SERIAL PRIMARY KEY,
    payout_id VARCHAR(100) NOT NULL UNIQUE,
    account_id VARCHAR(50) NOT NULL,
    amount_usd DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    settled_at DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'settled',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS demo_exchange_settlements (
    id SERIAL PRIMARY KEY,
    payout_id VARCHAR(100) NOT NULL UNIQUE,
    account_id VARCHAR(50) NOT NULL,
    amount_usd DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    settled_at DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'settled',
    exchange_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS demo_fx_rates (
    id SERIAL PRIMARY KEY,
    from_currency VARCHAR(10) NOT NULL,
    to_currency VARCHAR(10) NOT NULL,
    rate DECIMAL(18, 8) NOT NULL,
    rate_date DATE NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'mock',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, rate_date)
);

-- ── Seed: demo agent ─────────────────────────────────────────────────────────
INSERT INTO agents (name, description, model_policy, system_prompt, max_session_hours, created_by)
VALUES (
    'settlement-reconciliation-agent',
    'End-of-day settlement reconciliation agent for FinAgent MVP demo.',
    'hybrid',
    'You are a settlement reconciliation agent. You compare internal payout records against exchange settlement data, identify discrepancies, collect log evidence, and prepare a structured report for human review.',
    1,
    'init.sql'
)
ON CONFLICT (name) DO NOTHING;

-- ── Seed: demo connectors ────────────────────────────────────────────────────
INSERT INTO connectors (name, type, config) VALUES
    ('demo_postgres',      'postgresql', '{"host": "postgres", "port": 5432, "database": "finagentagent_db", "user": "finagentagent"}'),
    ('mock_exchange',      'rest_api',   '{"base_url": "http://mock_exchange_api:8000"}'),
    ('fx_rates_inmemory',  'inmemory',   '{"source": "config/fx_rates.json"}'),
    ('account_mapping',    'inmemory',   '{"source": "config/account_mapping.json"}'),
    ('reconcile_sandbox',  'sandbox',    '{"timeout_seconds": 30}'),
    ('payment_gateway_logs','logs',      '{"log_path": "docker/fixtures/payment_gateway.log"}')
ON CONFLICT (name) DO NOTHING;

-- ── Seed: demo internal payouts ──────────────────────────────────────────────
INSERT INTO demo_internal_payouts (payout_id, account_id, amount_inr, currency, settled_at, status) VALUES
    ('PAYOUT-1001', 'ACC001', 1000.00,  'INR', '2026-04-20', 'settled'),
    ('PAYOUT-1002', 'ACC002', 2150.25,  'EUR', '2026-04-20', 'pending_review'),
    ('PAYOUT-1003', 'ACC003',  780.00,  'GBP', '2026-04-20', 'settled')
ON CONFLICT (payout_id) DO NOTHING;

-- ── Seed: demo exchange settlements ─────────────────────────────────────────
-- PAYOUT-1001: exact match; PAYOUT-1002: amount mismatch (EUR slippage);
-- PAYOUT-1003: absent (exchange has PAYOUT-1004 instead → two-way discrepancy)
INSERT INTO demo_exchange_settlements (payout_id, account_id, amount_inr, currency, settled_at, status, exchange_timestamp) VALUES
    ('PAYOUT-1001', 'ACC001', 1000.00,  'INR', '2026-04-20', 'settled', '2026-04-20T08:14:58Z'),
    ('PAYOUT-1002', 'ACC002', 2098.75,  'EUR', '2026-04-20', 'settled', '2026-04-20T08:15:18Z'),
    ('PAYOUT-1004', 'ACC003',  120.00,  'GBP', '2026-04-20', 'settled', '2026-04-20T09:01:00Z')
ON CONFLICT (payout_id) DO NOTHING;

-- ── Seed: demo FX rates ──────────────────────────────────────────────────────
INSERT INTO demo_fx_rates (from_currency, to_currency, rate, rate_date, source) VALUES
    ('INR', 'INR', 1.00000000,   '2026-04-20', 'generator'),
    ('EUR', 'INR', 90.60000000,   '2026-04-20', 'generator'),
    ('GBP', 'INR', 105.63000000,   '2026-04-20', 'generator'),
    ('USD', 'INR', 83.45000000,   '2026-04-20', 'generator')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO finagentagent;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO finagentagent;
GRANT USAGE ON SCHEMA public TO finagentagent;
