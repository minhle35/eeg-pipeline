## How db.py works, line by line:

```python
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
```
The engine is SQLAlchemy's connection to your database. Think of it as the "phone line" to Postgres. ```pool_pre_ping=True``` means it checks the connection is alive before using it (prevents stale connection errors).

```python
SessionLocal = sessionmaker(bind=engine)
```
A session is a conversation with the database. sessionmaker is a factory — every time you call ```SessionLocal()```, you get a fresh session that can run queries, insert rows, etc. When you're done, you close it.

```python
class Base(DeclarativeBase):
    pass
```
```Base``` is the parent class for all your ORM models. When you write class EegSample(Base), SQLAlchemy registers that model and knows what table it maps to. DeclarativeBase is the modern SQLAlchemy 2.0 way of doing this (older code uses declarative_base() function).

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This is a FastAPI dependency. When an API endpoint needs the database, FastAPI calls get_db(), gives the endpoint a session, and guarantees it gets closed after the request — even if there's an error. The yield pattern is how FastAPI manages this lifecycle.

```python
def init_db():
    from pipeline.models import EegSample, IngestionLog
    Base.metadata.create_all(bind=engine)
```

This imports the models (so SQLAlchemy knows about them), then calls create_all() — which looks at every class that inherits from Base, generates the CREATE TABLE SQL, and runs it against Postgres. It uses IF NOT EXISTS internally, so it's safe to run multiple times.

The flow: 
```
engine connects → Base registers models → create_all() creates tables → SessionLocal provides sessions for reading/writing data.
```


