import logging
from pydantic import BaseModel
import uuid
from typing import Any, List
from jinja2 import Template
from omegaconf import DictConfig
from hydra.utils import instantiate
from google.genai.types import GenerateContentResponse
from database import ChatMessage

logger = logging.getLogger(__name__)

class AgentRequest(BaseModel):
    requestId: uuid.UUID
    type: str
    agentId: str
    chatId: uuid.UUID|None
    flowId: uuid.UUID
    flowType: str
    userInput: dict[str,Any]

class AgentResponse(BaseModel):
    responseId: uuid.UUID
    type: str
    requestId: uuid.UUID
    agentId: str
    chatId: uuid.UUID
    flowId: uuid.UUID
    flowType: str
    modelOutput: dict[str,Any]

class AgentConfig(BaseModel):
    id: str
    provider: str
    mode: str
    model: str    
    role: str
    goal: str
    rules: List[str]
    response_type_mapping: dict[str,str]
    templates: dict[str,str|dict[str,str]]

    @classmethod
    def load(cls, config:DictConfig, agentId:str) -> AgentConfig:
        result:AgentConfig = instantiate(config.agent[agentId])
        return result

    def mapResponseType(self, requestType: str) -> str:
        return self.response_type_mapping[requestType]

    def renderSystemInstruction(self) -> str:
        return self.renderTemplate("system-instruction", None, { "config": self })

    def renderRequestPrompt(self, request:AgentRequest) -> str:
        return self.renderTemplate("request", request.type, request)

    def renderChatMessage(self, message:ChatMessage) -> str:
        return self.renderTemplate("chat-message", None, message.__dict__)
    
    def renderGoogleModelOutput(self, response:GenerateContentResponse) -> str:
        return self.renderTemplate("model-output", "google-genai", { "response": response })
    
    def renderTemplate(self, category: str, type: str, values:dict[str,Any]) -> str:
        result = self.templates.get(category)
        if result is None:
            raise Exception("Cannot find the template for category:[%s], please check the config :[%s]", category, self.id)
            
        jinjaTemplate:str = result if type is None else result.get(type)

        if jinjaTemplate is None:
            raise Exception("Cannot find the template for type:[%s.%s], please check the config:[%s]", cateogory, type, self.id)
        
        try:
            template: Template = Template(jinjaTemplate)
            output: str = template.render(values)
            return output
        except Exception as e:
            logger.error("Exception when rendering the Jinja2 template, template:[%s] values:[%s]", jinjaTemplate, values)
            raise e