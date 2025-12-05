from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
import httpx

# Load environment variables
load_dotenv()

# Environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate environment variables (warnings only at startup)
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY environment variable is missing")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("WARNING: SUPABASE_URL and SUPABASE_KEY environment variables are missing")

# Initialize agents
Gift_agent = Agent(
    model="openrouter:amazon/nova-2-lite-v1:free",
    system_prompt="""
Role: An expert gift recommendation specialist.

CRITICAL INSTRUCTIONS:
- READ THE FULL CONVERSATION HISTORY PROVIDED
- NEVER ask for information you already have
- NEVER repeat questions about budget, occasion, interests, or recipient details that have been answered
- If a user says "that's good to know" or "I already told you", acknowledge and move forward
- Track what information you have: recipient type, interests, budget, occasion, what to avoid
- If user asks for more ideas, variations, or different suggestions - provide them directly
- Only ask clarifying questions about NEW information you need

Instructions:
1. Acknowledge the User's Input: Start responses with recognition of what they've shared.
2. Analyze and Brainstorm: Use ALL provided details to generate 3-5 unique and tailored gift ideas.
3. Structure the Output: Present gift ideas in a clear, numbered list format with:
    - Title: (e.g., *High-Quality Hiking Socks*)
    - Description: What it is and specific examples
    - Rationale: Why it's perfect for THIS specific person
4. Be Conversational and Helpful: Maintain a friendly, creative, and practical tone.
5. Respect Constraints: Adhere to the budget, occasion, and preferences mentioned.

Important Notes:
- Use the conversation history to understand what has ALREADY been discussed
- Do NOT re-ask for budget if already provided
- Do NOT re-ask for occasion if already provided
- Do NOT re-ask for interests if already provided
- Move the conversation forward naturally
- If user wants different options, provide them without asking the same questions again
"""
)

chips_agent = Agent(
    model="openrouter:microsoft/phi-3-mini-128k-instruct:free",
    system_prompt="""
Role: Generate quick reply messages that the USER can send to the assistant.
Instructions:
1. Generate exactly 3 short messages that the USER would send back to continue the conversation.
2. These are complete user messages, NOT questions TO ask the user.
3. Think of them as example responses the user might type next.
4. Each message should be a natural, complete thought (5-12 words maximum).
5. Output ONLY the 3 messages separated by "|" with no additional text, explanations, or numbering.

Examples of GOOD replies (what we want):
"They're really into photography" | "My budget is around $75" | "It's for their birthday party"
"I want something they can use daily" | "They prefer minimalist design" | "Looking for something handmade"
"It's for my coworker" | "They love cooking and travel" | "Any price under $100 is fine"

Examples of BAD replies (don't do this):
"What are you shopping for?" (this is a question TO the user, not FROM)
"Tell me more about budget" (this is asking, not telling)
"Personalized Coffee Mug" (this is a suggestion, not a user reply)
"No preferences really" (too vague and unhelpful)

Constraints:
*   Generate messages FROM the user, not TO the user
*   Be conversational and natural
*   No questions (no "?")
*   No explanations or preamble
*   Separate with " | " (space, pipe, space)
*   Each message 5-12 words
*   No numbering or bullets
*   Focus on providing helpful information or preferences
"""
)

app = FastAPI()

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    reply: str
    chips: list[str]

# Supabase functions
async def get_history(session_id: str) -> list[dict]:
    """Fetch chat history from Supabase"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": SUPABASE_KEY or "",
                "Authorization": f"Bearer {SUPABASE_KEY or ''}",
                "Content-Type": "application/json",
            }
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/chat_messages?session_id=eq.{session_id}&order=created_at.asc",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            return []
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return []

async def save_message(session_id: str, role: str, content: str) -> bool:
    """Save message to Supabase"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": SUPABASE_KEY or "",
                "Authorization": f"Bearer {SUPABASE_KEY or ''}",
                "Content-Type": "application/json",
            }
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/chat_messages",
                headers=headers,
                json={
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                },
            )
            return response.status_code == 201
    except Exception as e:
        print(f"Error saving message: {e}")
        return False

def build_context_string(messages: list[dict]) -> str:
    """Convert chat history into context string"""
    if not messages:
        return ""
    
    context_lines = ["CONVERSATION HISTORY:"]
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        context_lines.append(f"{role}: {content}")
    
    context_lines.append("\n---\nCRITICAL: You already have all the information above. DO NOT ask for details you've already received. Continue the conversation naturally based on what the user has told you. If they're asking for more ideas or different suggestions, provide them directly without re-asking for information.\n---\n")
    
    return "\n".join(context_lines)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint"""
    try:
        history = await get_history(request.session_id)
        context = build_context_string(history)
        full_input = context + f"USER: {request.message}"
        
        reply = await Gift_agent.run(full_input)
        agent_reply = reply.output
        
        chips_list = []
        try:
            chips_reply = await chips_agent.run(full_input)
            chips_text = chips_reply.output.strip()
            
            if chips_text:
                chips_list = [chip.strip() for chip in chips_text.split("|") if chip.strip()]
                chips_list = chips_list[:3]
                while len(chips_list) < 3:
                    chips_list.append("")
        except Exception as e:
            print(f"Error generating chips: {e}")
            chips_list = []
        
        await save_message(request.session_id, "user", request.message)
        await save_message(request.session_id, "bot", agent_reply)
        
        return ChatResponse(reply=agent_reply, chips=chips_list)
    except Exception as e:
        import traceback
        print(f"Error in /chat endpoint: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Export app for Vercel
app = app

