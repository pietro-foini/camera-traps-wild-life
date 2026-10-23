from typing import Any, Type, TypeVar

import sqlalchemy
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

from camera_traps.db.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class PostgresHandler:
    """PostgreSQL database handler implementation."""

    def __init__(self, db_user: str, db_password: str, db_host: str, db_port: str, db_name: str):
        """
        Initialize the database handler.

        :param db_user: database username
        :param db_password: database password
        :param db_host: database host address
        :param db_port: database port number
        :param db_name: database name
        """

        self.db_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self.engine = create_engine(self.db_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def connect(self) -> None:
        """Connect to the database and verify connection status."""

        with self.engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))

    def disconnect(self) -> None:
        """Disconnect from the database and dispose connection pool."""

        self.engine.dispose()

    def init_db(self) -> None:
        """Create all physical database tables defined by ORM models."""

        Base.metadata.create_all(bind=self.engine)

    def add_record(self, record: ModelType) -> ModelType:
        """
        Insert a single ORM record into the database.

        :param record: the ORM model instance to insert
        :return: the inserted ORM model instance with refreshed fields
        """

        session = self.session_factory()
        try:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_record(self, model: Type[ModelType], record_id: int, **kwargs: Any) -> None:
        """
        Update specific columns of a record by its primary key ID.

        :param model: the ORM model class
        :param record_id: the ID of the record to update
        :param kwargs: column names and their new values
        """

        session = self.session_factory()
        try:
            stmt = update(model).where(model.id == record_id).values(**kwargs)
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
