"""
Kenny Pipeline Function for Open WebUI
Connects Open WebUI conversations to n8n router workflow
"""

import requests
import json
import time
import uuid
from typing import List, Dict, Any, Iterator, Optional
from pydantic import BaseModel

class Pipe:
    class Valves(BaseModel):
        # Configuration for Kenny pipeline
        n8n_webhook_url: str = "http://host.docker.internal:5678/webhook/kenny-router"
        n8n_timeout: int = 30
        fallback_model: str = "qwen2.5:7b-instruct"
        debug_mode: bool = True
        session_timeout: int = 3600  # 1 hour

    def __init__(self):
        self.type = "manifold"
        self.id = "kenny_router"
        self.name = "Kenny Router"
        self.valves = self.Valves()
        self.session_cache = {}

    def get_session_id(self, __user__: Dict[str, Any]) -> str:
        """Generate or retrieve session ID for conversation continuity"""
        user_id = __user__.get("id", "anonymous")
        current_time = time.time()

        # Clean up expired sessions
        expired_sessions = [
            sid for sid, data in self.session_cache.items()
            if current_time - data.get("last_activity", 0) > self.valves.session_timeout
        ]
        for sid in expired_sessions:
            del self.session_cache[sid]

        # Find existing active session for user
        for session_id, session_data in self.session_cache.items():
            if session_data.get("user_id") == user_id:
                session_data["last_activity"] = current_time
                return session_id

        # Create new session
        session_id = str(uuid.uuid4())
        self.session_cache[session_id] = {
            "user_id": user_id,
            "created_at": current_time,
            "last_activity": current_time,
            "conversation_history": []
        }
        return session_id

    def call_n8n_router(self, message: str, session_id: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Call n8n router workflow with conversation context"""
        try:
            payload = {
                "message": message,
                "session_id": session_id,
                "user": {
                    "id": user_info.get("id", "anonymous"),
                    "email": user_info.get("email", ""),
                    "name": user_info.get("name", "User")
                },
                "timestamp": time.time(),
                "conversation_history": self.session_cache.get(session_id, {}).get("conversation_history", [])[-5:]  # Last 5 exchanges
            }

            if self.valves.debug_mode:
                print(f"[Kenny Pipeline] Calling n8n with payload: {json.dumps(payload, indent=2)}")

            response = requests.post(
                self.valves.n8n_webhook_url,
                json=payload,
                timeout=self.valves.n8n_timeout,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()

                # Update conversation history
                if session_id in self.session_cache:
                    self.session_cache[session_id]["conversation_history"].append({
                        "user_message": message,
                        "kenny_response": result.get("response", ""),
                        "intent": result.get("intent", "unknown"),
                        "confidence": result.get("confidence", 0.0),
                        "timestamp": time.time()
                    })

                    # Keep only last 10 exchanges
                    if len(self.session_cache[session_id]["conversation_history"]) > 10:
                        self.session_cache[session_id]["conversation_history"] = \
                            self.session_cache[session_id]["conversation_history"][-10:]

                return result
            else:
                print(f"[Kenny Pipeline] n8n call failed with status {response.status_code}: {response.text}")
                return {"error": f"n8n router failed: {response.status_code}", "fallback": True}

        except requests.exceptions.Timeout:
            print(f"[Kenny Pipeline] n8n call timed out after {self.valves.n8n_timeout}s")
            return {"error": "Kenny router timeout", "fallback": True}
        except Exception as e:
            print(f"[Kenny Pipeline] n8n call error: {str(e)}")
            return {"error": f"Kenny router error: {str(e)}", "fallback": True}

    def pipes(self) -> List[Dict[str, Any]]:
        """Define available pipes/models"""
        return [
            {
                "id": "kenny",
                "name": "Kenny Assistant",
                "description": "Kenny V4 - Your local AI assistant with access to Mail, Calendar, Messages, WhatsApp, and more"
            }
        ]

    def pipe(self, body: Dict[str, Any]) -> Iterator[str]:
        """Main pipeline function called by Open WebUI"""
        try:
            # Extract message and user info
            messages = body.get("messages", [])
            if not messages:
                yield "data: " + json.dumps({"error": "No messages provided"}) + "\n\n"
                return

            last_message = messages[-1]
            user_message = last_message.get("content", "")
            user_info = body.get("user", {})

            if self.valves.debug_mode:
                print(f"[Kenny Pipeline] Processing message: {user_message}")

            # Get or create session
            session_id = self.get_session_id(user_info)

            # Call Kenny's n8n router
            kenny_result = self.call_n8n_router(user_message, session_id, user_info)

            if kenny_result.get("fallback"):
                # Fallback to local model if Kenny router fails
                yield f"data: {json.dumps({'choices': [{'delta': {'content': '⚠️ Kenny router unavailable, using fallback mode.\\n\\n'}}]})}\n\n"

                # Here you could call a local Ollama model directly as fallback
                fallback_response = f"I received your message: '{user_message}', but Kenny's advanced features are currently unavailable. Please check that all services are running."

                for chunk in fallback_response.split():
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk + ' '}}]})}\n\n"
                    time.sleep(0.01)  # Small delay for streaming effect
            else:
                # Stream Kenny's response
                kenny_response = kenny_result.get("response", "I'm having trouble processing your request.")
                intent = kenny_result.get("intent", "unknown")
                confidence = kenny_result.get("confidence", 0.0)

                # Add metadata to response
                if self.valves.debug_mode and intent != "unknown":
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': f'🎯 Intent: {intent} ({confidence:.1%})\\n\\n'}}]})}\n\n"

                # Stream the main response
                words = kenny_response.split()
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"
                    time.sleep(0.02)  # Realistic typing speed

            # End stream
            yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            print(f"[Kenny Pipeline] {error_msg}")
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
            yield "data: [DONE]\n\n"