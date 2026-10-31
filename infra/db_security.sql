-- ═══════════════════════════════════════════════════════
-- SHIELD Platform — PostgreSQL Security Schema
-- Row-Level Security policies for zero-loophole access
-- ═══════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Row-Level Security on Cases ──────────────────────────
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;

-- Policy: Officers can only see their assigned cases or cases they created
-- Senior officers (DGP, ADGP, IGP) bypass via application layer
CREATE POLICY case_access_policy ON cases
    USING (
        assigned_officer_id = current_setting('app.current_officer_id')::uuid
        OR created_by_officer_id = current_setting('app.current_officer_id')::uuid
    );

-- ─── Row-Level Security on Evidence ───────────────────────
ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;

-- Evidence is accessible only if the officer can access the parent case
CREATE POLICY evidence_access_policy ON evidence
    USING (
        case_id IN (
            SELECT id FROM cases WHERE
                assigned_officer_id = current_setting('app.current_officer_id')::uuid
                OR created_by_officer_id = current_setting('app.current_officer_id')::uuid
        )
    );

-- ─── Immutable Audit Log (Append-Only) ────────────────────
-- Prevent any UPDATE or DELETE on audit_logs
CREATE RULE audit_log_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_log_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

-- ─── Trigger: Auto-update updated_at ──────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all main tables
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'public'
             AND table_name NOT IN ('audit_logs') -- Never update audit logs
    LOOP
        EXECUTE format(
            'CREATE TRIGGER %I BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION update_updated_at()',
            t || '_updated_at', t
        );
    END LOOP;
END $$;

-- ─── Database Users ────────────────────────────────────────
-- App user: limited privileges (no DROP, no TRUNCATE)
CREATE USER shield_app WITH PASSWORD 'CHANGE_IN_PRODUCTION';
GRANT CONNECT ON DATABASE shielddb TO shield_app;
GRANT USAGE ON SCHEMA public TO shield_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO shield_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO shield_app;
-- Explicitly DENY delete on audit logs
REVOKE DELETE ON audit_logs FROM shield_app;

-- Read-only user for Auditors
CREATE USER shield_auditor WITH PASSWORD 'CHANGE_IN_PRODUCTION';
GRANT CONNECT ON DATABASE shielddb TO shield_auditor;
GRANT USAGE ON SCHEMA public TO shield_auditor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO shield_auditor;

-- ─── Indexes for performance ────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cases_assigned ON cases(assigned_officer_id);
CREATE INDEX IF NOT EXISTS idx_cases_created_by ON cases(created_by_officer_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_category ON cases(category);
CREATE INDEX IF NOT EXISTS idx_audit_officer ON audit_logs(officer_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_behavior_officer ON behavior_signals(officer_id);
CREATE INDEX IF NOT EXISTS idx_behavior_timestamp ON behavior_signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_officer_badge ON officers(badge_number);
CREATE INDEX IF NOT EXISTS idx_officer_rank ON officers(rank);
CREATE INDEX IF NOT EXISTS idx_location_officer ON officer_locations(officer_id);
CREATE INDEX IF NOT EXISTS idx_location_timestamp ON officer_locations(timestamp);
