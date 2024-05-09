from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated
from pra_api import setting
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware



class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)


# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(setting.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg2"
)


# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300,echo=True
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# The first part of the function, before the yield, will
# be executed before the application starts.
# https://fastapi.tiangolo.com/advanced/events/#lifespan-function
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables..")
    create_db_and_tables()
    yield 


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", 
    )
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Hello": "kamil husssain attari"}

@app.post("/todos/", response_model=Task)
def create_todo(todo: Task, session: Annotated[Session, Depends(get_session)]):
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo


@app.get("/todos/", response_model=list[Task])
def read_todos(session: Annotated[Session, Depends(get_session)]):
        todos = session.exec(select(Task)).all()
        return todos

@app.put("/todos/{todo_id}", response_model=Task)
def update_heroes(todo_id: int, todo: Task, session: Session = Depends(get_session)):
    statement = select(Task).where(Task.id == todo_id)
    result = session.exec(statement)
    db_task = result.first()

    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    db_task.content = todo.content
    
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

# @app.delete("/{todo_id}",response_model=Task)
# def delete_todo(todo_id: int,  session: Session = Depends(get_session)):
#     db_task = session.get(Task,todo_id)
#     if db_task is None:
#         raise HTTPException(status_code=404, detail="Task not found")
    
#     session.delete(db_task)
#     session.commit()
#     return {"message": "Task deleted successfully"}

#
#
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_task(todo_id: int, session: Session = Depends(get_session)):
    statement = select(Task).where(Task.id == todo_id)
    result = session.exec(statement)
    db_task = result.first()

    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    session.delete(db_task)
    session.commit()
    return {"message": "Task deleted successfully"}