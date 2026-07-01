import logging
import os
from pathlib import Path
import json
import re

from pydantic import BaseModel
from google.genai.client import Client
from google.genai.types import Content, Part, GenerateContentConfig, GenerateContentResponse
from google.genai.types import BatchJob, InlinedRequest, CreateBatchJobConfig

from model import AgentRequest, AgentConfig
from database import Chat, open_session

logger = logging.getLogger(__name__)

mockPath = Path("/home/hung/projects/storyteller/python/resources/mock/google-genai/")

def load_latest_mock_response(mode:str, request:GoogleGenContentRequest) -> GenerateContentResponse:
    filePrefix = f"{request.agentId}-{request.type}-gen-content-resp"
    mockfiles = list((mockPath / mode).glob(f"{filePrefix}-*.json"))
    mockfiles.sort()
    if mockfiles:
        logger.info("Return generate_content mock response from:[%s]", mockfiles[-1])
        response = GenerateContentResponse.model_validate_json(mockfiles[-1].read_text())
        return response

def load_latest_mock_batchjob(mode:str, request:GoogleGenContentRequest) -> GenerateContentResponse:
    filePrefix = f"{request.agentId}-{request.type}-batch"
    mockfiles = list((mockPath / mode).glob(f"{filePrefix}-*.json"))
    mockfiles.sort()
    if mockfiles:
        logger.info("Return batch job from:[%s]", mockfiles[-1])
        batchjob = BatchJob.model_validate_json(mockfiles[-1].read_text())
        return batchjob

def save_batchjob_to_mock(mode:str, request:AgentRequest, batchJob:BatchJob) -> None:
    filePrefix = f"{request.agentId}-{request.type}-batch"

    cnt:int = 1
    mockfiles = list((mockPath / mode).glob(f"{filePrefix}-*.json"))
    mockfiles.sort()
    if mockfiles:
        match = re.search(f"{filePrefix}-(\d+)", mockfiles[-1].stem)
        cnt = int(match.group(1)) if match else 1
        
    mockJsonFile = mockPath / mode / f"{filePrefix}-{cnt+1:05d}.json"
    with open(mockJsonFile, mode="w") as f:
        f.write(batchJob.model_dump_json(indent=4))

class GoogleGenContentRequest(AgentRequest):
    model:str
    userPrompt:Content
    config:GenerateContentConfig
        
class GoogleLLM(BaseModel):

    mockCall:bool = True

    @staticmethod
    def load_apikey(envvar:str="GOOGLE_API_KEY", dockerSecretName:str="google-api-key") -> str|None:
        logger.info("get apikey from %s env variable...", envvar)
        apikey = os.getenv(envvar)
        if apikey is not None:
            return apikey
        
        secret = Path("/run/secrets") / dockerSecretName
        logger.info("get apikey from docker secret %s", secret)
        if secret.is_file():
            return secret.read_text()
        
        logger.info("no google-api-key was defined.")

    @staticmethod
    def convert_request(source:AgentRequest, agentConfig:AgentConfig, chat:Chat) -> GoogleGenContentRequest:
        logger.info("construct the System Instruction...")

        system_instruction:Content = Content(
            role = "system",
            parts = [
                Part.from_text(text=agentConfig.renderSystemInstruction())
            ]
        )

        genContentConfig:GenerateContentConfig = GenerateContentConfig(
            system_instruction=system_instruction
        )

        logger.info("construct the User Prompt...")

        user_prompt:Content = Content(
            role = "user",
            parts = [ Part.from_text(text=agentConfig.renderChatMessage(msg)) for msg in chat.messages]
        )

        target = GoogleGenContentRequest(
            **source.model_dump(),
            model=agentConfig.model,
            userPrompt=user_prompt,
            config=genContentConfig
        )

        return target

    async def create_content(self, request:GoogleGenContentRequest) -> GenerateContentResponse:
        if self.mockCall:
            response:GenerateContentResponse = load_latest_mock_response('async', request)
        else:
            apikey:str = GoogleLLM.load_apikey()
            
            logger.info("call generate_content API...")

            async with Client(api_key=apikey).aio as client:
                response:GenerateContentResponse = await client.models.generate_content(
                    model = request.model,
                    contents = request.userPrompt,
                    config = request.config
                )

            self.save_response_to_mock(request, response)

        return response

    async def create_content_batch(self, request:GoogleGenContentRequest) -> BatchJob:
        if self.mockCall:
            batchJob:BatchJob = load_latest_mock_batchjob('async-batch', request)
        else:
            apikey:str = GoogleLLM.load_apikey()
            
            inline:InlinedRequest = InlinedRequest(
                contents=request.userPrompt,
                config=request.config,
                metadata= {
                   "request_id": str(request.requestId),
                   "request_type": request.type,
                   "agent_id": request.agentId,
                   "chat_id": str(request.chatId),
                   "flow_id": str(request.flowId),
                   "flow_type": request.flowType
                }
            )

            logger.info("call client.batches.create API...")

            async with Client(api_key=apikey).aio as client:
                batchJob:BatchJob = await client.batches.create(
                    model=request.model,
                    src=[inline],
                    config=CreateBatchJobConfig(
                        display_name="BatchJob..."
                    )
                )

            save_batchjob_to_mock('async-batch', request, batchJob)

        return batchJob








