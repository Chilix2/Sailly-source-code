-- Tenant column on google_calls for dashboards / joins (session_data also carries tenant_id).
ALTER TABLE google_calls ADD COLUMN IF NOT EXISTS tenant_id TEXT;
