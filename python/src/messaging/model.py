from dataclasses import dataclass
import pika

@dataclass
class RabbitHostConfig:
    """
    dataclass for rabbitmq server configuration
    """
    host:str
    username:str
    password:str

    def toPikaConnParam(self) -> pika.ConnectionParameters:
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            credentials=credentials
        )
        return parameters

@dataclass
class QueueConfig:
    """
    configuration for declare and bind queue
    """
    queue:str
    exchange:str
    routing_key:str
    dlq_exchange:str|None