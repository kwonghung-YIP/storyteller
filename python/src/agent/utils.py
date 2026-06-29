import logging
from typing import Any
import json

from omegaconf import DictConfig
from hydra.utils import instantiate
from google.genai.types import GenerateContentResponse, BatchJob

from .google_genai import GoogleLLM, GoogleGenContentRequest

from model import AgentRequest, AgentConfig, AgentResponse
from database import (
    PostgresHostConfig, open_session, 
    Chat, ChatMessage, ChatRepository,
    ModelResponse, GoogleBatchJob
)

logger = logging.getLogger(__name__)


async def load_chat(chatRepo:ChatRepository, request:AgentRequest) -> Chat:
    if request.chatId is None:
        chat:Chat = Chat(agentId=request.agentId)
        await chatRepo.create(chat)
    else:
        chat:Chat = await chatRepo.findById(request.chatId)

    return chat

class AgentHelper:

    def __init__(self, appConfig:DictConfig) -> None:
        self._appConfig:DictConfig = appConfig
        self._pgHostConfig:PostgresHostConfig = instantiate(appConfig.postgres.connection)

    async def convert_request(self, agentConfig:AgentConfig, source:AgentRequest) -> GoogleGenContentRequest:
        
        async with open_session(self._pgHostConfig) as session:
            chatRepo:ChatRepository = ChatRepository(session)

            if source.chatId is None:
                chat:Chat = Chat(agentId=source.agentId)
                session.add(chat)
            else:
                chat:Chat = await chatRepo.findById(source.chatId)

            prompt:str = agentConfig.renderRequestPrompt(source)
            new_message = ChatMessage(role="user", requestId=source.requestId, text=prompt)
            chat.addMessage(new_message)

        if source.chatId is None:
            source.chatId = chat.id

        target:GoogleGenContentRequest = GoogleLLM.convert_request(source, agentConfig, chat)

        return target
    
    async def save_google_response(self, config:AgentConfig, request:AgentRequest, response: GenerateContentResponse) -> None:

        async with open_session(self._pgHostConfig) as session:
            chatRepo:ChatRepository = ChatRepository(session)
            chat:Chat = await chatRepo.findById(request.chatId)

            record = ModelResponse(agentId=request.agentId, requestId=request.requestId,
                modelRespId=response.response_id, responseJson=response.model_dump_json())
            
            session.add(record)
            session.flush()

            output:str = config.renderGoogleModelOutput(response)
            new_message = ChatMessage(role="model", responseId=record.responseId, text=output)
            chat.addMessage(new_message)

        target:AgentResponse = AgentResponse(
            responseId=record.responseId, 
            type=config.mapResponseType(request.type),
            requestId=request.requestId, 
            agentId=request.agentId, 
            chatId=chat.id,
            flowId=request.flowId, 
            flowType=request.flowType, 
            modelOutput=json.loads(output))
        
        return target
    
    async def save_google_batchjob(self, batchJob:BatchJob) -> None:
        
        target:GoogleBatchJob = GoogleBatchJob.from_batch_job(batchJob)

        async with open_session(self._pgHostConfig) as session:
            session.add(target)

