-- pgvector 확장 설치 필요
CREATE EXTENSION IF NOT EXISTS vector;
-- ENUM 타입 정의
CREATE TYPE source_type_enum AS ENUM (
    'VIDEO_EVALUATION',
    'VIDEO_SUMMARY',
    'COMMENT_REACTION',
    'VIEWER_ESCAPE_ANALYSIS',
    'ALGORITHM_OPTIMIZATION',
    'PERSONALIZED_KEYWORDS',
    'IDEA_RECOMMENDATION'
);
-- 1. 콘텐츠 청크 테이블 (텍스트 데이터와 벡터 저장)
CREATE TABLE IF NOT EXISTS content_chunk (
    id SERIAL PRIMARY KEY,
    source_type source_type_enum NOT NULL,
    -- video_id, channel_id, report_id 등
    source_id INT NOT NULL,
    -- 텍스트 데이터(청크)
    content TEXT NOT NULL,
    -- 원본에서의 청크 순서 
    chunk_index INT NOT NULL,
    -- 벡터 데이터
    embedding vector(1536) NOT NULL,
    -- 메타데이터
    meta JSONB,
    -- 시간 관리
    created_at TIMESTAMP DEFAULT NOW()
);

-- -- 3. 검색 로그 테이블 (성능 최적화용)
-- CREATE TABLE IF NOT EXISTS search_logs (
--     id SERIAL PRIMARY KEY,
--     query_embedding vector(1536),
--     retrieved_chunk_ids TEXT [],
--     -- 검색된 청크 ID 배열
--     similarity_scores FLOAT [],
--     -- 각 청크의 유사도 점수
--     response_quality FLOAT,
--     -- 응답 품질 (피드백 기반)
--     created_at TIMESTAMP DEFAULT NOW()
-- );
-- 인덱스
CREATE INDEX idx_source ON content_chunk(source_type, source_id);
CREATE INDEX idx_embedding ON content_chunk USING ivfflat (embedding vector_cosine_ops);