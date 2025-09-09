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