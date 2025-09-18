-- Kenny Conversation Memory and Context Management System
-- Supabase SQL schema for storing conversation state and context

-- Enable vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Conversations table for session management
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    user_email TEXT,
    user_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    conversation_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Conversation turns table for storing individual exchanges
CREATE TABLE IF NOT EXISTS conversation_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    user_message_embedding VECTOR(384), -- nomic-embed-text produces 384d vectors
    kenny_response TEXT NOT NULL,
    intent_classified TEXT,
    intent_confidence REAL,
    agent_used TEXT,
    response_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Context memories table for long-term memory storage
CREATE TABLE IF NOT EXISTS context_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    memory_type TEXT NOT NULL, -- 'preference', 'fact', 'pattern', 'relationship'
    memory_content TEXT NOT NULL,
    memory_embedding VECTOR(384),
    confidence_score REAL DEFAULT 1.0,
    source_conversation_id UUID REFERENCES conversations(id),
    source_turn_id UUID REFERENCES conversation_turns(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- User patterns table for learning user behavior
CREATE TABLE IF NOT EXISTS user_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL, -- 'time_preference', 'intent_frequency', 'response_style'
    pattern_data JSONB NOT NULL,
    confidence_score REAL DEFAULT 1.0,
    sample_size INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Conversation analytics table for monitoring system performance
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    turn_id UUID REFERENCES conversation_turns(id),
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_data JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_conversation_id ON conversation_turns(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_turn_number ON conversation_turns(conversation_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_intent ON conversation_turns(intent_classified);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_timestamp ON conversation_turns(timestamp);

CREATE INDEX IF NOT EXISTS idx_context_memories_user_id ON context_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_context_memories_type ON context_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_context_memories_active ON context_memories(user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_user_patterns_user_id ON user_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_user_patterns_type ON user_patterns(pattern_type);

-- Vector similarity search indexes
CREATE INDEX IF NOT EXISTS idx_conversation_turns_embedding
ON conversation_turns USING ivfflat (user_message_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_context_memories_embedding
ON context_memories USING ivfflat (memory_embedding vector_cosine_ops)
WITH (lists = 100);

-- Function to get recent conversation context
CREATE OR REPLACE FUNCTION get_conversation_context(
    p_session_id TEXT,
    p_limit INTEGER DEFAULT 5
) RETURNS TABLE (
    turn_number INTEGER,
    user_message TEXT,
    kenny_response TEXT,
    intent_classified TEXT,
    timestamp TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ct.turn_number,
        ct.user_message,
        ct.kenny_response,
        ct.intent_classified,
        ct.timestamp
    FROM conversation_turns ct
    JOIN conversations c ON ct.conversation_id = c.id
    WHERE c.session_id = p_session_id
    ORDER BY ct.turn_number DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to search conversation history by semantic similarity
CREATE OR REPLACE FUNCTION search_conversation_history(
    p_user_id TEXT,
    p_query_embedding VECTOR(384),
    p_similarity_threshold REAL DEFAULT 0.7,
    p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
    conversation_id UUID,
    turn_number INTEGER,
    user_message TEXT,
    kenny_response TEXT,
    intent_classified TEXT,
    similarity REAL,
    timestamp TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ct.conversation_id,
        ct.turn_number,
        ct.user_message,
        ct.kenny_response,
        ct.intent_classified,
        (ct.user_message_embedding <=> p_query_embedding) AS similarity,
        ct.timestamp
    FROM conversation_turns ct
    JOIN conversations c ON ct.conversation_id = c.id
    WHERE c.user_id = p_user_id
    AND ct.user_message_embedding IS NOT NULL
    AND (ct.user_message_embedding <=> p_query_embedding) < (1 - p_similarity_threshold)
    ORDER BY similarity ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get user memories by type
CREATE OR REPLACE FUNCTION get_user_memories(
    p_user_id TEXT,
    p_memory_type TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
) RETURNS TABLE (
    memory_content TEXT,
    memory_type TEXT,
    confidence_score REAL,
    created_at TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE,
    access_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cm.memory_content,
        cm.memory_type,
        cm.confidence_score,
        cm.created_at,
        cm.last_accessed,
        cm.access_count
    FROM context_memories cm
    WHERE cm.user_id = p_user_id
    AND cm.is_active = TRUE
    AND (p_memory_type IS NULL OR cm.memory_type = p_memory_type)
    ORDER BY cm.last_accessed DESC, cm.confidence_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to search memories by semantic similarity
CREATE OR REPLACE FUNCTION search_user_memories(
    p_user_id TEXT,
    p_query_embedding VECTOR(384),
    p_similarity_threshold REAL DEFAULT 0.7,
    p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
    memory_content TEXT,
    memory_type TEXT,
    confidence_score REAL,
    similarity REAL,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    -- Update access count for retrieved memories
    UPDATE context_memories
    SET last_accessed = NOW(), access_count = access_count + 1
    WHERE id IN (
        SELECT cm.id
        FROM context_memories cm
        WHERE cm.user_id = p_user_id
        AND cm.is_active = TRUE
        AND cm.memory_embedding IS NOT NULL
        AND (cm.memory_embedding <=> p_query_embedding) < (1 - p_similarity_threshold)
        ORDER BY (cm.memory_embedding <=> p_query_embedding) ASC
        LIMIT p_limit
    );

    RETURN QUERY
    SELECT
        cm.memory_content,
        cm.memory_type,
        cm.confidence_score,
        (cm.memory_embedding <=> p_query_embedding) AS similarity,
        cm.created_at
    FROM context_memories cm
    WHERE cm.user_id = p_user_id
    AND cm.is_active = TRUE
    AND cm.memory_embedding IS NOT NULL
    AND (cm.memory_embedding <=> p_query_embedding) < (1 - p_similarity_threshold)
    ORDER BY similarity ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to update user patterns
CREATE OR REPLACE FUNCTION update_user_pattern(
    p_user_id TEXT,
    p_pattern_type TEXT,
    p_pattern_data JSONB,
    p_confidence_score REAL DEFAULT 1.0
) RETURNS UUID AS $$
DECLARE
    pattern_id UUID;
BEGIN
    INSERT INTO user_patterns (user_id, pattern_type, pattern_data, confidence_score, updated_at)
    VALUES (p_user_id, p_pattern_type, p_pattern_data, p_confidence_score, NOW())
    ON CONFLICT (user_id, pattern_type)
    DO UPDATE SET
        pattern_data = p_pattern_data,
        confidence_score = p_confidence_score,
        sample_size = user_patterns.sample_size + 1,
        updated_at = NOW()
    RETURNING id INTO pattern_id;

    RETURN pattern_id;
END;
$$ LANGUAGE plpgsql;

-- Function to log conversation analytics
CREATE OR REPLACE FUNCTION log_conversation_metric(
    p_conversation_id UUID,
    p_turn_id UUID DEFAULT NULL,
    p_metric_name TEXT,
    p_metric_value REAL DEFAULT NULL,
    p_metric_data JSONB DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    analytics_id UUID;
BEGIN
    INSERT INTO conversation_analytics (conversation_id, turn_id, metric_name, metric_value, metric_data)
    VALUES (p_conversation_id, p_turn_id, p_metric_name, p_metric_value, p_metric_data)
    RETURNING id INTO analytics_id;

    RETURN analytics_id;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old conversation data
CREATE OR REPLACE FUNCTION cleanup_old_conversations(
    p_days_old INTEGER DEFAULT 90
) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Archive conversations older than specified days
    UPDATE conversations
    SET is_active = FALSE
    WHERE last_activity < NOW() - INTERVAL '%s days' % p_days_old
    AND is_active = TRUE;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Archive related memories with low confidence and access
    UPDATE context_memories
    SET is_active = FALSE
    WHERE created_at < NOW() - INTERVAL '%s days' % p_days_old
    AND confidence_score < 0.5
    AND access_count < 3
    AND is_active = TRUE;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update conversation last_activity
CREATE OR REPLACE FUNCTION update_conversation_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET last_activity = NOW(),
        conversation_count = conversation_count + 1,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_update_conversation_activity
    AFTER INSERT ON conversation_turns
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_activity();

-- Row Level Security (RLS) policies
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE context_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_analytics ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (adjust based on your authentication setup)
CREATE POLICY conversations_user_policy ON conversations
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY conversation_turns_user_policy ON conversation_turns
    FOR ALL USING (EXISTS (
        SELECT 1 FROM conversations c
        WHERE c.id = conversation_id
        AND c.user_id = auth.uid()::text
    ));

CREATE POLICY context_memories_user_policy ON context_memories
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY user_patterns_user_policy ON user_patterns
    FOR ALL USING (auth.uid()::text = user_id);

CREATE POLICY conversation_analytics_user_policy ON conversation_analytics
    FOR ALL USING (EXISTS (
        SELECT 1 FROM conversations c
        WHERE c.id = conversation_id
        AND c.user_id = auth.uid()::text
    ));

-- Grant necessary permissions
GRANT ALL ON conversations TO service_role, authenticated;
GRANT ALL ON conversation_turns TO service_role, authenticated;
GRANT ALL ON context_memories TO service_role, authenticated;
GRANT ALL ON user_patterns TO service_role, authenticated;
GRANT ALL ON conversation_analytics TO service_role, authenticated;

GRANT EXECUTE ON FUNCTION get_conversation_context TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION search_conversation_history TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION get_user_memories TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION search_user_memories TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION update_user_pattern TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION log_conversation_metric TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_conversations TO service_role;