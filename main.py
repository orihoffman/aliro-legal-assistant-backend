from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
from uuid import uuid4
from Conversation import ConversationSession

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

sessions: Dict[str, ConversationSession] = {}

class InitResponse(BaseModel):
    session_id: str

class MessageRequest(BaseModel):
    session_id: str
    message: str

class MessageResponse(BaseModel):
    response: str

@app.post("/start", response_model=InitResponse)
async def start_session():
    session_id = str(uuid4())
    session = ConversationSession(session_id=session_id)
    sessions[session_id] = session

    # Start the session asynchronously
    await session.start()
    return InitResponse(session_id=session_id)

@app.post("/message", response_model=MessageResponse)
async def send_message(req: MessageRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Send and receive the message asynchronously
    response = await session.send_and_receive(req.message)
    return MessageResponse(response=response)

@app.post("/stop")
async def stop_session(session_id: str):
    session = sessions.pop(session_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Stop the session asynchronously
    await session.stop()
    return {"message": f"Session {session_id} stopped."}

# Add this block to run the app in debug mode
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=10000, reload=True)
