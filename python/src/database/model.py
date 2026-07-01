from typing import List
import uuid
import datetime
from dataclasses import dataclass

from sqlalchemy import func, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, TIMESTAMP, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.orm import declarative_base

from google.genai.types import BatchJob, InlinedResponse

Base = declarative_base()

@dataclass
class PostgresHostConfig:
    host:str
    username:str
    password:str
    database:str

    def to_connection_url(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}/{self.database}"

class Chat(Base):
    __tablename__ = "chat"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    agentId: Mapped[str] = mapped_column(String(30), name="agent_id")
    createdDate: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="created_ts", server_default=func.current_time())

    messages: Mapped[List[ChatMessage]] = relationship(cascade="all, delete-orphan")

    def addMessage(self, message:ChatMessage) -> None:
        lastSeq = self.messages[-1].seq if self.messages else 0
        message.seq = lastSeq + 1
        self.messages.append(message)

class ChatMessage(Base):
    __tablename__ = "chat_message"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    chatId: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat.id"), name="chat_id")
    seq: Mapped[int]
    role: Mapped[str]
    requestId: Mapped[uuid.UUID] = mapped_column(UUID, name="request_id")
    responseId: Mapped[uuid.UUID] = mapped_column(UUID, name="response_id")
    text: Mapped[str]
    createdDate: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="created_ts", server_default=func.current_time())

class ModelResponse(Base):
    __tablename__ = "model_response"

    agentId: Mapped[str] = mapped_column(String(30), name="agent_id") 
    requestId: Mapped[uuid.UUID] = mapped_column(UUID, name="request_id")
    responseId: Mapped[uuid.UUID] = mapped_column(UUID, name="response_id", primary_key=True, server_default=func.gen_random_uuid())
    modelRespId: Mapped[str] = mapped_column(String(255), name="model_resp_id")
    responseJson = Column(JSONB, nullable=True, name="response_json")
    createdDate: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="created_ts", server_default=func.current_time())

class GoogleBatchJob(Base):
    __tablename__ = "google_genai_batch_job"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    displayName: Mapped[str] = mapped_column(String(255), name="display_name", nullable=True)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    createTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), name="create_time", nullable=False)
    startTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), name="start_time", nullable=False)
    updateTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), name="update_time", nullable=False)
    endTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), name="end_time", nullable=False)
    requestId: Mapped[uuid.UUID] = mapped_column(UUID, name="request_id", nullable=True)
    responseId: Mapped[uuid.UUID] = mapped_column(UUID, name="response_id", nullable=True)
    error = Column(JSONB, nullable=True)
    batchjobJson = Column(JSONB, name="batchjob_json", nullable=False)
    
    def copy_from_batch_job(self, batchJob:BatchJob) -> None:
        self.name = batchJob.name
        self.displayName = batchJob.display_name
        self.state = batchJob.state
        self.createTime = batchJob.create_time
        self.startTime = batchJob.start_time
        self.updateTime = batchJob.update_time
        self.endTime = batchJob.end_time
        self.error = batchJob.error
        self.batchjobJson = batchJob.model_dump_json()

        if batchJob.dest:
            inlinedResponse:InlinedResponse = batchJob.dest.inlined_responses[0]
            if inlinedResponse.metadata:
                self.requestId = uuid.UUID(inlinedResponse.metadata["request_id"])
