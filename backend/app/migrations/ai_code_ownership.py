"""Preserve pre-owner AI code histories without assigning private data to a user."""
from sqlalchemy import inspect, text


def migrate_ai_code_ownership(engine):
    inspector = inspect(engine)
    if "ai_code_conversations" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_code_conversations")}
    with engine.begin() as connection:
        if "owner_id" not in columns:
            connection.execute(text("ALTER TABLE ai_code_conversations ADD COLUMN owner_id VARCHAR(36)"))
        names = {index["name"] for index in inspect(connection).get_indexes("ai_code_conversations")}
        if "ix_ai_code_conversations_owner_id" not in names:
            connection.execute(text("CREATE INDEX ix_ai_code_conversations_owner_id ON ai_code_conversations (owner_id)"))
