import pytest
import pytest_asyncio

from hydra import initialize, compose
from omegaconf import DictConfig, OmegaConf
from hydra.utils import instantiate

from model import AgentConfig
from messaging import QueueConfig

@pytest.fixture(scope="session")
def load_hydra_config():
    with initialize(version_base=None, config_path="../../resources"):
        config = compose(config_name="config")
        yield config

def test_load_writer_agent_config(load_hydra_config):
    config:DictConfig = load_hydra_config

    agent_config:AgentConfig = AgentConfig.load(config, "writer#1")

    assert agent_config.model=="gemini-2.5-flash-lite"

def test_load_queue_bind_config(load_hydra_config):
    config:DictConfig = load_hydra_config

    config1:QueueConfig = instantiate(config.rabbitmq['queue-and-binding']['agent-request'])

    assert config1.queue=="abc"

