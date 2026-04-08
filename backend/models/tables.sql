-- G2B_AI DDL
-- ARCHITECTURE.md 섹션 4 기준

-- 사용자
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'staff',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 수집된 공고
CREATE TABLE IF NOT EXISTS bids (
    id SERIAL PRIMARY KEY,
    bid_ntce_no VARCHAR(50) NOT NULL,
    bid_ntce_ord VARCHAR(10),
    bid_ntce_nm TEXT NOT NULL,
    ntce_instt_nm VARCHAR(200),
    dminstt_nm VARCHAR(200),
    bid_close_dt TIMESTAMP,
    asign_bdgt_amt BIGINT,
    presmpt_prce BIGINT,
    bid_ntce_url TEXT,
    raw_data JSONB,
    status VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(bid_ntce_no, bid_ntce_ord)
);

-- 공고 첨부파일
CREATE TABLE IF NOT EXISTS bid_attachments (
    id SERIAL PRIMARY KEY,
    bid_id INTEGER REFERENCES bids(id) ON DELETE CASCADE,
    file_name VARCHAR(500),
    file_type VARCHAR(20),
    file_url TEXT,
    converted_html TEXT,
    converted_md TEXT,
    conversion_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI 분석 결과
CREATE TABLE IF NOT EXISTS analyses (
    id SERIAL PRIMARY KEY,
    bid_id INTEGER REFERENCES bids(id) ON DELETE CASCADE,
    issuing_org VARCHAR(200),
    deadline TIMESTAMP,
    project_summary TEXT,
    project_scope TEXT,
    eval_criteria JSONB,
    requirements JSONB,
    qualification TEXT,
    tech_requirements JSONB,
    poison_clauses JSONB,
    risk_level VARCHAR(20),
    raw_analysis JSONB,
    analysis_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 제안목차
CREATE TABLE IF NOT EXISTS proposal_outlines (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    outline_data JSONB NOT NULL,
    is_ismp BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 대상 리스트
CREATE TABLE IF NOT EXISTS bid_targets (
    id SERIAL PRIMARY KEY,
    bid_id INTEGER REFERENCES bids(id) ON DELETE CASCADE,
    assignee_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT '검토필요',
    required_staff INTEGER,
    office_info VARCHAR(200),
    estimated_cost BIGINT,
    bid_estimate BIGINT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(bid_id)
);
