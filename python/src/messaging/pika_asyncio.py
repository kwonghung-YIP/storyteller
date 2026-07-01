import logging
from contextlib import asynccontextmanager
import asyncio
from functools import partial
from typing import Any
import threading
from collections.abc import Callable

from hydra.utils import instantiate
from omegaconf import DictConfig

from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties, Exchange, Queue
from pika.exchange_type import ExchangeType

from google.genai.types import GenerateContentResponse, BatchJob

from .model import RabbitHostConfig, QueueConfig

from model import AgentRequest, AgentConfig, AgentResponse
from agent import AgentHelper, GoogleGenContentRequest, GoogleLLM
from database import PostgresHostConfig

publish_response = Callable[[str|bytes, BasicProperties|None], None]

logger = logging.getLogger(__name__)

###
# Wrap the AsyncioConnection within an async context manager
###

@asynccontextmanager
async def openConnection(config:RabbitHostConfig, timeout:float=30):

    try:
        openedEvent = asyncio.Event()
        closedEvent = asyncio.Event()
        connection = AsyncioConnection(
            parameters=config.toPikaConnParam(),
            on_open_callback=partial(on_connection_open, event=openedEvent),
            on_open_error_callback=on_connection_open_error,
            on_close_callback=partial(on_connection_close, event=closedEvent)
        )
        await asyncio.wait_for(openedEvent.wait(), timeout)
        yield connection
    except Exception as err:
        logger.error("Exception when using the connection: %s", err)
        raise err
    finally:
        connection.close()
        await asyncio.wait_for(closedEvent.wait(), timeout)

def on_connection_open(conn:AsyncioConnection, event:asyncio.Event) -> None:
    """
    callback function when rabbitmq connection is established
    """
    event.set()

def on_connection_close(conn:AsyncioConnection, reason:BaseException, event:asyncio.Event) -> None:
    """
    callback function when rabbitmq connection is closed
    """
    event.set()

def on_connection_open_error(conn:AsyncioConnection, error:BaseException) -> None:
    pass

###
# Wrap the Channel within an async context manager
###

@asynccontextmanager
async def openChannel(connection:AsyncioConnection, timeout:float=30):

    try:
        openedEvent = asyncio.Event()
        closedEvent = asyncio.Event()

        channel = connection.channel(
            on_open_callback=partial(on_channel_open,
                event=openedEvent,
                onClosedCallback=partial(on_channel_close, event=closedEvent))
        )
        await asyncio.wait_for(openedEvent.wait(), timeout)
        yield channel
    except Exception as err:
        logger.error("Exception when using the channel: %s", err)
        raise err
    finally:
        channel.close()
        await asyncio.wait_for(closedEvent.wait(), timeout)

def on_channel_open(channel:Channel, 
    event:asyncio.Event, onClosedCallback:function) -> None:
    channel.add_on_close_callback(onClosedCallback)
    event.set()

def on_channel_close(channel:Channel, reason:Exception, event:asyncio.Event):
    event.set()

###
# Declare a Exchange 
###

async def declare_exchange(channel:Channel, name:str, timeout:float=30):
    """
    declare an exchange
    """
    declaredEvent = asyncio.Event()
    
    channel.exchange_declare(
        exchange=name,
        exchange_type=ExchangeType.direct,
        callback=partial(on_exchange_declare_ok, event=declaredEvent)
    )
    await asyncio.wait_for(declaredEvent.wait(), timeout)

def on_exchange_declare_ok(declare_ok:Exchange.DeclareOk, event:asyncio.Event) -> None:
    event.set()

###
# Declare a queue and bind to a Exchange
###

async def declare_and_bind_queue(channel:Channel, queue_name:str, exchange_name:str, 
    routing_key:str, arguments:dict[str,Any], timeout:float=30) -> None:
    """
    declare an exchange
    """
    declaredEvent = asyncio.Event()

    channel.queue_declare(
        queue=queue_name,
        durable=True,
        arguments=arguments,
        callback=partial(on_queue_declare, event=declaredEvent)
    )

    await asyncio.wait_for(declaredEvent.wait(), timeout)

    bindEvent = asyncio.Event()

    channel.queue_bind(
        exchange=exchange_name,
        queue=queue_name,
        routing_key=routing_key,
        callback=partial(on_queue_bind, event=bindEvent)
    )

    await asyncio.wait_for(bindEvent.wait(), timeout)

def on_queue_declare(declare_ok:Queue.DeclareOk, event:asyncio.Event) -> None:
    event.set()

def on_queue_bind(bind_ok:Queue.BindOk, event:asyncio.Event) -> None:
    event.set()

###
# Declare a queue and bind to a Exchange
###

async def declare_queue_and_dlq(channel:Channel, config:QueueConfig) -> None:
    await declare_queue_and_dlq2(channel,
        queue_name=config.queue,
        exchange_name=config.exchange,
        routing_key=config.routing_key,
        dlq_exchange=config.dlq_exchange
    )

async def declare_queue_and_dlq2(channel:Channel, queue_name:str, 
    exchange_name:str, routing_key:str, dlq_exchange:str) -> None:
    
    dlq_queue_name:str = f"{queue_name}-dlq"
    dlq_routing_key:str = f"{routing_key}-dlq"

    # define the DLQ queue and bind to DLQ exchange
    arguments = {
        'x-queue-type': 'quorum',
    }
    await declare_and_bind_queue(channel, 
        queue_name=dlq_queue_name,
        exchange_name=dlq_exchange,
        routing_key=dlq_routing_key,
        arguments=arguments)
    
    # define main queue and bind to exchange
    
    # Quorum Queue delayed-retry feature
    # https://www.rabbitmq.com/docs/quorum-queues#delayed-retry
    arguments = {
        'x-queue-type': 'quorum',
        'x-delayed-retry-type': 'all', #disabled/all/failed/returned
        'x-delayed-retry-min': 1000, #ms
        'x-delayed-retry-max': 30000, #ms
        'x-delivery-limit': 5,
        'x-dead-letter-exchange': dlq_exchange,
        'x-dead-letter-routing-key': dlq_routing_key
    }
    await declare_and_bind_queue(channel, 
        queue_name=queue_name,
        exchange_name=exchange_name,
        routing_key=routing_key,
        arguments=arguments)

###
# Declare a queue and bind to a Exchange
###

def subscribe_queue(channel:Channel, queue_name:str, tg:asyncio.TaskGroup, handler:function) -> str:
    consumer_tag:str = channel.basic_consume(
        queue=queue_name,
        on_message_callback=partial(on_channel_message, taskgroup=tg, handler=handler),
        callback=on_channel_basic_consume_ok
    )
    return consumer_tag

def on_channel_message(channel:Channel, method:Basic.Deliver, 
    props:BasicProperties, raw:bytes, taskgroup:asyncio.TaskGroup, handler:function) -> None:

    if props.headers:
        for (key,value) in props.headers.items():
            logger.info(f"header {key}:{value}")

    taskCount = len(taskgroup._tasks) + 1
    # if one of the task in the taskgroup throw exception that will stop the whole task group
    # so we call the wrapper to catch the exception and keep the group running
    task = taskgroup.create_task(
        task_wrapper(channel, method.delivery_tag, handler(channel, raw, props)), 
        name=f"handlerTask_{taskCount}"
    )

async def task_wrapper(channel:Channel, delivery_tag:int, handler:asyncio.coroutines) -> None:
    try:
        result = await handler
        channel.basic_ack(delivery_tag)
    except Exception as err:
        logger.error("exception when running task %s", err)
        # will Quorum Queue, once the no of times a message being rejected hit the x-delivery-limit
        # it will be move to the dead letter queue by the rabbitmq and don't need to explivitly specify 
        # the basic.reject reqeueue flag to False
        channel.basic_reject(delivery_tag, requeue=True)
    finally:
        pass

def on_channel_basic_consume_ok(consumeOK:Basic.ConsumeOk) -> None:
    logger.info("channel basic ConsumeOK")

###
# Declare a queue and bind to a Exchange
###

def publish_message(channel:Channel, exchange:str, routing_key:str, body:str|bytes, props:BasicProperties|None=None) -> None:
    """
    """
    channel.basic_publish(exchange, routing_key, body, properties=props)

###
# Declare a queue and bind to a Exchange
###

async def cancel_subscription(channel:Channel, consumer_tag:str, timeout:float=30) -> None:
    cancelOKEvent = asyncio.Event()
    logger.info(f"Cancelling conumer subscription consumer_tag:{consumer_tag}")
    channel.basic_cancel(
        consumer_tag=consumer_tag,
        callback=partial(on_channel_basic_cancel_ok, event=cancelOKEvent)
    )
    await asyncio.wait_for(cancelOKEvent.wait(), timeout)

def on_channel_basic_cancel_ok(cancelOk:Basic.CancelOk, event:asyncio.Event) -> None:
    logger.info(f"channel BasicCancelOK")
    event.set()

class PikaConsumer(threading.Thread):

    def __init__(self, appConfig:DictConfig):
        super().__init__()
        self._appConfig:DictConfig = appConfig
        self._termSignal:threading.Event = threading.Event()

        mockCall:bool = appConfig['google-genai']['mock']
        self._googleLLM:GoogleLLM = GoogleLLM(mockCall=mockCall)

    def run(self) -> None:
        """
        The runnable function for this Thread, and it switch to async here,
        a new eventloop initial under this thread when call asyncio below.
        """
        try:
            logger.info("Call asyncio.run() to start accepting agent request...")
            asyncio.run(self.acceptRequest())
        finally:
            logger.info("asyncio.run()... completed.")

    def stop(self) -> None:
        """ 
        Allow the parent thread to stop this thread, set the self._termSignal to 
        trigger the stop process
        """
        logger.info("set termSignal")
        self._termSignal.set()

    async def acceptRequest(self) -> None:
        """
        """
        rabbitmqConfig = self._appConfig.rabbitmq
        rabbitHost:RabbitHostConfig = instantiate(rabbitmqConfig.connection)
        async with openConnection(rabbitHost) as conn, openChannel(conn) as channel:
            await declare_exchange(channel, rabbitmqConfig.exchange['dead-letter-queue'])

            await declare_exchange(channel, rabbitmqConfig.exchange['agent-request'])
            await declare_exchange(channel, rabbitmqConfig.exchange['request-routing'])

            await declare_queue_and_dlq(channel, rabbitmqConfig['queue-and-binding']['agent-request'])
            await declare_queue_and_dlq(channel, rabbitmqConfig['queue-and-binding']['google-genai-async'])
            await declare_queue_and_dlq(channel, rabbitmqConfig['queue-and-binding']['google-genai-async-batch'])

            await declare_exchange(channel, rabbitmqConfig.exchange['agent-response'])

            await declare_queue_and_dlq(channel, rabbitmqConfig['queue-and-binding']['agent-response'])

            pub_resp_func:publish_response = partial(publish_message, channel=channel,
                exchange=rabbitmqConfig.exchange['agent-response'],
                routing_key=rabbitmqConfig['queue-and-binding']['agent-response'].routing_key)

            helper:AgentHelper = AgentHelper(self._appConfig, pub_resp_func)

            consumer_tags = []
            async with asyncio.TaskGroup() as tg:
                # define background tasks
                bgTask = tg.create_task(self.backgroundTask(tg), name="backgroundTask")
                googleBatchJobTask = tg.create_task(self.googleBatchJobBGTask(helper), name="googleBatchJobTask")
                consumer_tags.append(subscribe_queue(channel, rabbitmqConfig['queue-and-binding']['agent-request'].queue, tg, self.request_routing))
                consumer_tags.append(subscribe_queue(channel, rabbitmqConfig['queue-and-binding']['google-genai-async'].queue, tg, self.google_generate_content))
                consumer_tags.append(subscribe_queue(channel, rabbitmqConfig['queue-and-binding']['google-genai-async-batch'].queue, tg, self.google_batch_job))

            logger.info("asyncio.TaskGroup completed.")

            for tag in consumer_tags:
                await cancel_subscription(channel, tag)

    async def backgroundTask(self, taskgroup:asyncio.TaskGroup, interval:float=1) -> None:
        """
        This background task keep running until any external party call the self.stop()
        function to set the self._termSignal, without this background thread, the taskgroup
        will end immediately and will not wait for incoming message.
        """
        myTask = asyncio.current_task()
        try:
            logger.info("Starting the background task...")
            while not self._termSignal.is_set():
                logger.debug("The self._termSignal has not activated sleep for %d sec...", interval)
                await asyncio.sleep(interval)

            logger.info("Canceling other tasks in the same taskgroup...")
            others = [ task for task in taskgroup._tasks if task.get_name() != myTask.get_name()]
            for task in others:
                task.cancel()
        finally:
            logger.info("task [%s] completed.", myTask.get_name())

    async def googleBatchJobBGTask(self, helper:AgentHelper, interval:float=60*5) -> None:
        """
        """
        myTask = asyncio.current_task()
        try:
            while not self._termSignal.is_set():
                logger.info("Check Google GenAI BatchJob state...")
                await helper.check_batchjob_state()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Task [%s] has been cancelled.", myTask.get_name())
        finally:
            logger.info("task [%s] completed.", myTask.get_name())

    async def request_routing(self, channel:Channel, raw:bytes, props:BasicProperties) -> None:
        agentRequest:AgentRequest = AgentRequest.model_validate_json(raw)

        agentConfig:AgentConfig = AgentConfig.load(self._appConfig, agentRequest.agentId)

        helper:AgentHelper = AgentHelper(appConfig=self._appConfig)

        match agentConfig.provider:
            case "google-genai":
                googleRequest:GoogleGenContentRequest = await helper.convert_request(agentConfig, agentRequest)
                routing_key:str = f"{agentConfig.provider}-{agentConfig.mode}"
                body:str = googleRequest.model_dump_json(indent=4)
            case _:
                raise Exception(f"unknown agent provider:[{agentConfig.provider}]")

        exchange:str = self._appConfig.rabbitmq.exchange['request-routing']
        publish_message(channel, exchange, routing_key, body)

    async def google_generate_content(self, channel:Channel, raw:bytes, props:BasicProperties) -> None:
        request:GoogleGenContentRequest = GoogleGenContentRequest.model_validate_json(raw)

        response:GenerateContentResponse = await self._googleLLM.create_content(request)

        helper:AgentHelper = AgentHelper(appConfig=self._appConfig)
        agentResponse:AgentResponse = await helper.save_google_response(request, response)

        exchange:str = self._appConfig.rabbitmq.exchange['agent-response']
        routing_key:str = self._appConfig.rabbitmq['queue-and-binding']['agent-response'].routing_key
        publish_message(channel, exchange, routing_key, agentResponse.model_dump_json(indent=4))

    async def google_batch_job(self, channel:Channel, raw:bytes, props:BasicProperties) -> None:
        request:GoogleGenContentRequest = GoogleGenContentRequest.model_validate_json(raw)

        agentConfig:AgentConfig = AgentConfig.load(self._appConfig, request.agentId)

        batchjob:BatchJob = await self._googleLLM.create_content_batch(request)

        helper:AgentHelper = AgentHelper(appConfig=self._appConfig)
        await helper.save_google_batchjob(batchjob)

    
