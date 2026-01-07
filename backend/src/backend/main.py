from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select


from typing import Dict

from .llm import generate_llm_response


from .database import create_db_and_tables, get_session, seed_db
from .models import Conversation, Message


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


# @app.post("/conversations/{conversation_id}/messages/", response_model=Message)
# def create_message(
#     conversation_id: int, message: Message, session: Session = Depends(get_session)
# ):
#     conversation = session.get(Conversation, conversation_id)
#     if not conversation:
#         raise HTTPException(status_code=404, detail="Conversation not found")

#     message.conversation_id = conversation_id
#     session.add(message)
#     session.commit()
#     session.refresh(message)
#     return message


@app.post("/conversations/{conversation_id}/messages/")
def create_message(
    conversation_id: int, message: Message, session: Session = Depends(get_session)
) -> Dict[str, Message]:

    # Step 1: Validate conversation exists
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Step 2: Save USER message first
    message.role = "user"
    message.conversation_id = conversation_id

    session.add(message)
    session.commit()
    session.refresh(message)

    # Step 3: Collect FULL conversation history from DB
    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    ).all()

    # Step 4: Convert to LLM API format
    history = [{"role": m.role, "content": m.content} for m in messages]

    # Step 5: Call LLM API
    try:
        assistant_text = generate_llm_response(history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Step 6: Save ASSISTANT reply
    assistant_message = Message(
        role="assistant", content=assistant_text, conversation_id=conversation_id
    )

    session.add(assistant_message)
    session.commit()
    session.refresh(assistant_message)

    # Step 7: Return both
    return {"user_message": message, "assistant_message": assistant_message}
