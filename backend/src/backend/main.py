from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .database import create_db_and_tables, get_session, seed_db
from .models import Conversation, Message
from .llm import generate_llm_response  # <--- NRP LLM import


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_db()
    yield


app = FastAPI(lifespan=lifespan)

# middleware = "middle layer software that connects different apps, dbs, services"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CRUD functions
@app.post("/conversations/", response_model=Conversation)
def create_conversation(
    conversation: Conversation, session: Session = Depends(get_session)
):
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@app.get("/conversations/", response_model=List[Conversation])
def read_conversations(session: Session = Depends(get_session)):
    conversations = session.exec(select(Conversation)).all()

    # Attach messages
    for conv in conversations:
        conv.messages = session.exec(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        ).all()

    return conversations


@app.get("/conversations/{conversation_id}", response_model=Conversation)
def read_conversation(conversation_id: int, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Explicitly load messages
    session.refresh(conversation, ["messages"])
    return conversation


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    session.delete(conversation)
    session.commit()
    return {"ok": True}


# read in the messages
@app.get("/conversations/{conversation_id}/messages/", response_model=List[Message])
def read_conversation_messages(
    conversation_id: int, session: Session = Depends(get_session)
):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    statement = select(Message).where(Message.conversation_id == conversation_id)
    messages = session.exec(statement).all()
    return messages


# -----------------------
# POST messages + NRP LLM
# -----------------------
@app.post("/conversations/{conversation_id}/messages/", response_model=Message)
def create_message(
    conversation_id: int, message: Message, session: Session = Depends(get_session)
):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user's message first
    message.conversation_id = conversation_id
    session.add(message)
    session.commit()
    session.refresh(message)

    # Call NRP LLM to generate assistant response
    try:
        # Fetch conversation history for LLM context
        conversation_messages = session.exec(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        ).all()

        # Format messages for LLM API
        llm_messages = [
            {"role": m.role, "content": m.content} for m in conversation_messages
        ]

        # Generate assistant reply
        llm_response_content = generate_llm_response(llm_messages)

        # Save assistant response to DB
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=llm_response_content,
        )
        session.add(assistant_message)
        session.commit()
        session.refresh(assistant_message)

        # Return assistant message directly to frontend
        return assistant_message

    except Exception as e:
        print(f"LLM error: {e}")
        # Fallback: return user's message if LLM fails
        return message
