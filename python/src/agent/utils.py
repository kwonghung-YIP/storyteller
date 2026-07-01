import logging
from typing import Any
import json
import uuid

from omegaconf import DictConfig
from hydra.utils import instantiate
from google.genai.types import GenerateContentResponse, BatchJob, InlinedResponse, JobState
from google.genai.client import Client
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from .google_genai import GoogleLLM, GoogleGenContentRequest

from model import AgentRequest, AgentConfig, AgentResponse
from database import (
    PostgresHostConfig, open_session, 
    Chat, ChatMessage, ChatRepository,
    ModelResponse, GoogleBatchJob, GoogleBatchJobRepository
)
#from messaging.pika_asyncio import publish_response

logger = logging.getLogger(__name__)

async def load_chat(chatRepo:ChatRepository, request:AgentRequest) -> Chat:
    if request.chatId is None:
        chat:Chat = Chat(agentId=request.agentId)
        await chatRepo.create(chat)
    else:
        chat:Chat = await chatRepo.findById(request.chatId)

    return chat

def nvl(metadata:dict[str,str], key:str, default:uuid.UUID=None) -> uuid.UUID:
    if key in metadata.keys():
        return uuid.UUID(hex=metadata[key])
    else:
        return default

class AgentHelper:

    def __init__(self, appConfig:DictConfig, pubRespFunc=None) -> None:
        self._appConfig:DictConfig = appConfig
        self._pgHostConfig:PostgresHostConfig = instantiate(appConfig.postgres.connection)
        self._publishResponse = pubRespFunc

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
    

    async def save_google_response(self, request:AgentRequest, response: GenerateContentResponse) -> None:
        async with open_session(self._pgHostConfig) as session:
            self.save_google_response_internal(session, request, response)

    async def save_google_response_internal(self, session:AsyncSession, request:AgentRequest, response: GenerateContentResponse) -> None:

        config:AgentConfig = AgentConfig.load(agentId=request.agentId, config=self._appConfig)

        chatRepo:ChatRepository = ChatRepository(session)
        chat:Chat = await chatRepo.findById(request.chatId)

        record = ModelResponse(agentId=request.agentId, requestId=request.requestId,
            modelRespId=response.response_id, responseJson=response.model_dump_json())
        
        session.add(record)
        await session.flush()

        output:str = config.renderGoogleModelOutput(response)
        new_message = ChatMessage(role="model", responseId=record.responseId, text=output)
        chat.addMessage(new_message)

        await session.flush()

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
        
        target:GoogleBatchJob = GoogleBatchJob()
        target.copy_from_batch_job(batchJob)

        async with open_session(self._pgHostConfig) as session:
            session.add(target)

    async def check_batchjob_state(self) -> None:
        async with open_session(self._pgHostConfig) as session:
            repo:GoogleBatchJobRepository = GoogleBatchJobRepository(session)
        
            apikey:str = GoogleLLM.load_apikey()
            async with Client(api_key=apikey).aio as client:
                async for jobList in await client.batches.list():
                    logger.info("BatchJob name: %s", jobList.name)
                    #
                    # BatchJob instances returned from client.batches.list() do not have the src/dest properties
                    # instead of it, we have to call client.batches.get() to fetch each BatchJob by their name
                    #
                    job:BatchJob = await client.batches.get(name=jobList.name)

                    record:GoogleBatchJob = await repo.findByName(job.name)
                    if record is None:
                        logger.info("BatchJob %s has not found in database, state: %s", job.name, job.state)

                        record = GoogleBatchJob()
                        record.copy_from_batch_job(job)
                        record.error = "Cannot find the BatchJob record"
                        session.add(record)

                        #if job.done:
                        #    await self.handle_completed_batchjob(session, job, record)        

                    else:
                        if record.state == job.state:
                            logger.info("BatchJob state stay put: %s -> %s", record.state, job.state)
                        else:
                            logger.info("BatchJob state changed from %s -> %s", record.state, job.state)
                            
                            record.copy_from_batch_job(job)

                            if job.done:
                                await self.handle_completed_batchjob(session, job, record)

    async def handle_completed_batchjob(self, session:AsyncSession, batchJob:BatchJob, record:GoogleBatchJob) -> None:
        batchjob_handlers = {
            JobState.JOB_STATE_SUCCEEDED: self.handle_succeeded_batchjob
        }
        handler = batchjob_handlers[batchJob.state]
        if handler:
            await handler(session, batchJob, record)
        else:
            logger.info("No handler defined for BatchJob.state %s", batchJob.state.name)


    async def handle_succeeded_batchjob(self, session:AsyncSession, batchJob:BatchJob, record:GoogleBatchJob) -> None:

        if not batchJob.dest:
            return 
        
        inlinedResponse:InlinedResponse = batchJob.dest.inlined_responses[0]

        if not inlinedResponse.metadata:
            return

        metadata:dict[str,str] = inlinedResponse.metadata
        try:
            request:AgentRequest = AgentRequest(
                requestId=nvl(metadata, "request_id"),
                type=metadata.get("request_type"),
                agentId=metadata.get("agent_id"),
                chatId=nvl(metadata, "chat_id"),
                flowId=nvl(metadata, "flow_id"),
                flowType=metadata.get("flow_type"),
                userInput=None,
            )
        except ValidationError as err:
            logger.exception("Fail to create AgentRequest from metadata")
            record.error = "missing metadata to create the AgentRequest"
            return
        
        response:GenerateContentResponse = inlinedResponse.response

        agentResponse:AgentResponse = await self.save_google_response_internal(session, request, response)

        record.responseId = agentResponse.responseId
        
        body:str = agentResponse.model_dump_json(indent=4)

        self._publishResponse(body=body)

