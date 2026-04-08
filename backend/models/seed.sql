-- 초기 관리자 계정
-- 비밀번호: admin1234 (bcrypt hash)
INSERT INTO users (email, password_hash, name, role)
VALUES (
    'admin@g2b.ai',
    '$2b$12$hyVzDBusXeFqRaYIZRFigetXJdhiU3N8NTqb9WPtNz4FNn.GMlKau',
    '관리자',
    'admin'
) ON CONFLICT (email) DO NOTHING;
