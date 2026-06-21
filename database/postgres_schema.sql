CREATE TABLE IF NOT EXISTS accounts (
    id BIGINT PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    group_name TEXT NOT NULL,
    category TEXT NOT NULL,
    result_center TEXT NOT NULL,
    type TEXT NOT NULL,
    essential BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT PRIMARY KEY,
    tx_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    account_id BIGINT REFERENCES accounts(id),
    source TEXT NOT NULL DEFAULT 'Manual',
    external_id TEXT UNIQUE,
    counterparty TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS debts (
    id BIGINT PRIMARY KEY,
    creditor TEXT NOT NULL,
    debt_type TEXT NOT NULL,
    opened_at DATE,
    initial_balance NUMERIC(14, 2) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    monthly_interest_rate NUMERIC(8, 4) NOT NULL DEFAULT 0,
    minimum_payment NUMERIC(14, 2) NOT NULL DEFAULT 0,
    due_date DATE,
    strategy TEXT,
    source TEXT NOT NULL DEFAULT 'Manual',
    external_id TEXT UNIQUE,
    notes TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS budgets (
    id BIGINT PRIMARY KEY,
    category TEXT UNIQUE NOT NULL,
    monthly_limit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    action_hint TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS import_rules (
    id BIGINT PRIMARY KEY,
    priority INTEGER NOT NULL DEFAULT 100,
    contains_text TEXT NOT NULL,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    active BOOLEAN NOT NULL DEFAULT TRUE
);
