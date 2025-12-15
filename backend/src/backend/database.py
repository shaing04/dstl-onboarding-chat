from sqlmodel import Session, SQLModel, create_engine, select

from .models import *  # Import models to ensure they are registered with SQLModel

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# seeding db = populating db with initial data
def seed_db():
    with Session(engine) as session:
        existing_convs = session.exec(select(Conversation)).first()
        if existing_convs:
            return

        print("No existing conversations found. Seeding database...")
        # Conversation 1: General greeting
        conv1 = Conversation(title="Welcome Chat")
        msg1_1 = Message(role="user", content="Hello, who are you?", conversation=conv1)
        msg1_2 = Message(
            role="assistant",
            content="I am an AI assistant here to help you with your onboarding.",
            conversation=conv1,
        )
        msg1_3 = Message(
            role="user",
            content="Great, what should I do first?",
            conversation=conv1,
        )
        msg1_4 = Message(
            role="assistant",
            content="You should start by exploring the documentation.",
            conversation=conv1,
        )

        # Conversation 2: Technical question
        conv2 = Conversation(title="Python Help")
        msg2_1 = Message(
            role="user",
            content="How do I create a list in Python?",
            conversation=conv2,
        )
        msg2_2 = Message(
            role="assistant",
            content="You can create a list using square brackets, like this: `my_list = [1, 2, 3]`.",
            conversation=conv2,
        )
        msg2_3 = Message(
            role="user",
            content="Can I store different types in it?",
            conversation=conv2,
        )
        msg2_4 = Message(
            role="assistant",
            content="Yes, Python lists can contain elements of different data types.",
            conversation=conv2,
        )

        session.add(conv1)
        session.add(conv2)
        session.add(msg1_1)
        session.add(msg1_2)
        session.add(msg1_3)
        session.add(msg1_4)
        session.add(msg2_1)
        session.add(msg2_2)
        session.add(msg2_3)
        session.add(msg2_4)

        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
