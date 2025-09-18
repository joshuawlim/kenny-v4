"""
Kenny Session Manager
Handles concurrent conversations and context persistence
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import aioredis
from supabase import create_client, Client

@dataclass
class ConversationContext:
    session_id: str
    user_id: str
    turns: List[Dict[str, Any]]
    created_at: float
    last_activity: float
    metadata: Dict[str, Any]

class KennySessionManager:
    def __init__(self, supabase_url: str, supabase_key: str, redis_url: str = "redis://localhost:6379"):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.redis_url = redis_url
        self.redis = None
        self.sessions: Dict[str, ConversationContext] = {}
        self.session_timeout = 3600  # 1 hour

    async def initialize(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url(self.redis_url)

    async def get_or_create_session(self, session_id: str, user_id: str) -> ConversationContext:
        """Get existing session or create new one"""
        # Check memory cache first
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_activity = time.time()
            return session

        # Check Redis cache
        if self.redis:
            cached = await self.redis.get(f"kenny:session:{session_id}")
            if cached:
                session_data = json.loads(cached)
                session = ConversationContext(**session_data)
                self.sessions[session_id] = session
                return session

        # Load from Supabase or create new
        result = self.supabase.table('conversations').select('*').eq('session_id', session_id).execute()

        if result.data:
            # Load existing conversation
            conv_data = result.data[0]
            turns_result = self.supabase.table('conversation_turns').select('*').eq('conversation_id', conv_data['id']).order('turn_number').execute()

            session = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                turns=[turn for turn in turns_result.data] if turns_result.data else [],
                created_at=conv_data['created_at'],
                last_activity=time.time(),
                metadata=conv_data.get('metadata', {})
            )
        else:
            # Create new conversation
            conv_result = self.supabase.table('conversations').insert({
                'session_id': session_id,
                'user_id': user_id,
                'created_at': time.time(),
                'last_activity': time.time()
            }).execute()

            session = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                turns=[],
                created_at=time.time(),
                last_activity=time.time(),
                metadata={}
            )

        self.sessions[session_id] = session
        await self._cache_session(session)
        return session

    async def add_turn(self, session_id: str, user_message: str, kenny_response: str, intent: str, confidence: float):
        """Add conversation turn to session"""
        session = self.sessions.get(session_id)
        if not session:
            return

        turn_data = {
            'user_message': user_message,
            'kenny_response': kenny_response,
            'intent_classified': intent,
            'intent_confidence': confidence,
            'timestamp': time.time(),
            'turn_number': len(session.turns) + 1
        }

        session.turns.append(turn_data)
        session.last_activity = time.time()

        # Keep only last 10 turns in memory
        if len(session.turns) > 10:
            session.turns = session.turns[-10:]

        await self._cache_session(session)

    async def _cache_session(self, session: ConversationContext):
        """Cache session in Redis"""
        if self.redis:
            await self.redis.setex(
                f"kenny:session:{session.session_id}",
                self.session_timeout,
                json.dumps(asdict(session), default=str)
            )

    async def cleanup_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired = [
            sid for sid, session in self.sessions.items()
            if current_time - session.last_activity > self.session_timeout
        ]

        for sid in expired:
            del self.sessions[sid]
            if self.redis:
                await self.redis.delete(f"kenny:session:{sid}")

# Global session manager instance
session_manager = KennySessionManager(
    supabase_url="http://localhost:8000",  # Update with actual URL
    supabase_key="your-supabase-key"       # Update with actual key
)