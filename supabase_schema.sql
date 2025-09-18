-- Kenny V4 Supabase Vector Database Schema
-- Enable vector extension (already done)
CREATE EXTENSION IF NOT EXISTS vector;

-- Core conversations table for storing messages and embeddings
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  content TEXT,
  embedding vector(384),
  source TEXT,
  timestamp TIMESTAMP DEFAULT NOW()
);

-- User feedback table for improving responses
CREATE TABLE IF NOT EXISTS user_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_text TEXT,
  response_text TEXT,
  feedback_type TEXT CHECK (feedback_type IN ('like', 'dislike')),
  timestamp TIMESTAMP DEFAULT NOW()
);

-- Create indexes for vector similarity searches
CREATE INDEX IF NOT EXISTS conversations_embedding_idx 
ON conversations USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Create index for timestamp queries
CREATE INDEX IF NOT EXISTS conversations_timestamp_idx 
ON conversations (timestamp DESC);

-- Create index for source queries
CREATE INDEX IF NOT EXISTS conversations_source_idx 
ON conversations (source);

-- Emails table for Apple Mail integration
CREATE TABLE IF NOT EXISTS emails (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id TEXT UNIQUE NOT NULL,
  subject TEXT,
  sender TEXT,
  recipient TEXT,
  cc TEXT,
  bcc TEXT,
  date_sent TIMESTAMP,
  content TEXT,
  has_attachments BOOLEAN DEFAULT FALSE,
  source TEXT DEFAULT 'apple_mail',
  processed_at TIMESTAMP DEFAULT NOW(),
  embedding vector(768)  -- Using larger embeddings for better quality
);

-- Create indexes for email searches
CREATE INDEX IF NOT EXISTS emails_message_id_idx ON emails (message_id);
CREATE INDEX IF NOT EXISTS emails_sender_idx ON emails (sender);
CREATE INDEX IF NOT EXISTS emails_date_sent_idx ON emails (date_sent DESC);
CREATE INDEX IF NOT EXISTS emails_subject_idx ON emails USING gin(to_tsvector('english', subject));
CREATE INDEX IF NOT EXISTS emails_content_idx ON emails USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS emails_embedding_idx
ON emails USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Email search function using vector similarity
CREATE OR REPLACE FUNCTION search_emails(
  search_query TEXT,
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id UUID,
  message_id TEXT,
  subject TEXT,
  sender TEXT,
  recipient TEXT,
  date_sent TIMESTAMP,
  content TEXT,
  has_attachments BOOLEAN,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
DECLARE
  query_embedding vector(768);
BEGIN
  -- For now, we'll do text-based search until we have embedding generation
  -- In production, you'd generate the embedding for search_query here

  RETURN QUERY
  SELECT
    e.id,
    e.message_id,
    e.subject,
    e.sender,
    e.recipient,
    e.date_sent,
    LEFT(e.content, 500) as content, -- Limit content for performance
    e.has_attachments,
    CASE
      WHEN e.subject ILIKE '%' || search_query || '%' THEN 0.9
      WHEN e.content ILIKE '%' || search_query || '%' THEN 0.8
      WHEN e.sender ILIKE '%' || search_query || '%' THEN 0.7
      ELSE 0.5
    END as similarity
  FROM emails e
  WHERE
    e.subject ILIKE '%' || search_query || '%' OR
    e.content ILIKE '%' || search_query || '%' OR
    e.sender ILIKE '%' || search_query || '%'
  ORDER BY similarity DESC, e.date_sent DESC
  LIMIT match_count;
END;
$$;

-- Function to get recent emails
CREATE OR REPLACE FUNCTION get_recent_emails(
  days_back INT DEFAULT 7,
  limit_count INT DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  message_id TEXT,
  subject TEXT,
  sender TEXT,
  date_sent TIMESTAMP,
  content TEXT,
  has_attachments BOOLEAN
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.id,
    e.message_id,
    e.subject,
    e.sender,
    e.date_sent,
    LEFT(e.content, 300) as content,
    e.has_attachments
  FROM emails e
  WHERE e.date_sent >= CURRENT_DATE - INTERVAL '%s days' % days_back
  ORDER BY e.date_sent DESC
  LIMIT limit_count;
END;
$$;

-- Test embedding storage and retrieval
DO $$
BEGIN
  -- Test insert with dummy embedding
  INSERT INTO conversations (user_id, content, embedding, source) VALUES
  (gen_random_uuid(), 'Test message for Kenny AI', array_fill(0.1, ARRAY[384])::vector, 'test');

  -- Test vector similarity search
  PERFORM * FROM conversations
  ORDER BY embedding <-> array_fill(0.1, ARRAY[384])::vector
  LIMIT 1;

  RAISE NOTICE 'Vector database setup test successful';
END $$;