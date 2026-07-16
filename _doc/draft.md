I have implemented a agentic flow example that using RabbitMQ as the messaging backbone and Google Gen AI Batch Job.

The GitHub repo: https://github.com/kwonghung-YIP/storyteller

Based on that, I would like to publish a article to Medium to discribe my implementation.

Focus on the points and diagram provided for each section, please draft article with a simple and straightforward tone.


# Storyteller Agentic Workflow

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/01-storyteller-agentic-flow.jpg

- The agentic flow implements a storyteller scenario, it has two agents, the writer agent draft the manuscript based on the story idea provided by user, or the feedback from editor, and the editor agent reviews the manuscript and provide feedback.

- The flow starting from a story idea provided by user, base on that, writer agent write the first draft and pass it to editor agent for review, and the feedback pass back to writer agent to revise the manuscript and will reivew by editor agent again.

- The flow stop and publish the story when: 1) the manuscript has been review twice, or 2) editor has no further feedback.

# Loop to event driven design (Sequence Diagram)

- The storytelling agentic flow is a toy example shows how multiple agents are cooperated, instead of  agent framework, we are looking for an alternative to implement the flow. 

- For most of agent frameworks, they facilitates how to model the direct interaction between agents, they support patterns such as chain-of-agent, looping, and conditional branching to construct a complex agentic flow. These terms sound familiar day back to when Business Process Management (BPM) and Workflow Modeling still a hot topic in the field, with the Event Driven Architecture, it encourage loose coupling between business processes.

- From this aspect, what if we treat an agent as a business process which implements the request-response pattern, it extracts the user input from Agent Request, then call the LLM Model with its own configuration, finally returns the model out as the Agent Response. And the interactions between agents are centralized and proceed by an Event Broker, it receives an Agent Response as an incoming event, retrieve the current state of the agentic flow, decide the next agent should be called, and construct the Agent Request. That is alternative way to build the agentic flow also we can leverage the rich features that were already well developed and available in different eco systems.

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/02-storyteller-sequence-diagram.jpg

- In the sequence diagram above, it shows how's the Event Broker - Response Dispatcher coordinating the writer and editor agent. Response Dispatcher is specified for handling Agent Response and determines the next step defined in the agentic flow, in order to allow Response Dispatcher identifies the incomeing event, all Agent Request and Response are labelled with Request or Response type. And according to the flow exit conditions, Response Dispatcher terminate the flow and publish the story when the manuscript was reviewed twice, or the editor agent has no more feedback. 

# State Diagram

- Because the Response Dispatcher is stateless and loosely coupling with the flow, the Agent Response has to contain the flow instance identity. It allows the Response Dispatcher load the current state of the flow from persistent storage, such as the manuscript and feedback history in our case, determine the next step, transform the flow to new state, and save it back to storage.   

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/03-storyteller-state-diagram.jpg

- In the state diagram above, it shows how's a storytelling flow instance state change accordind to different Agent Request and Response.

# The Agent Config Yaml

- It is not ideal to find role description or task objective hardcode in the python source file, to avoid that, we aim to separate the Agent Configuration into a independ YAML file.

- YAML file actually is a good option, for unstructural long prompt message, it is readable and natively support multiple line text, unlike JSON and XML, it keeps you away from escape character; for structural properties, it has better support than markdown file.

- On top of YAML, we also applied Jinja2 template and Hydra Config to enrich the configuration file features, which support in-file text substitution, conditional content, list processing, dynamic import, and configuration inheritance. Imagine that saving tokens by customizing the System Instruction based on the incoming Agent Request instead of one big lenghtly instuction including everything.

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/04-storyteller-agent-config-yaml.jpg

- The Writer Agent config file above defines:
- it calls Google gemini-25.flash-lite model with Google Gen AI SDK in batch model.
- a simple mapping from Agent Request type to Agent Response type.
- System Instruction template, which substituted with Role, Goal, and list of Rules defined in the same file.
- Agent Response template, an alternative for instructing the model having structured output, the template form the JSON output from the text return from the model.
- templates for different Agent Request type, which transform the userInput JSON into user prompt message.   

# Implement the Agentic Loops with RabbitMQ and Response Dispatcher

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/05-storyteller-request-response.jpg

# Extends to Batch Mode

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/06-storyteller-batch-job.jpg

# Retry with Dead Letter Queue

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/07-storyteller-dead-letter-queue.jpg

# Overall architecture

https://raw.githubusercontent.com/kwonghung-YIP/storyteller/refs/heads/main/_doc/08-storyteller-architecture.jpg


# Further extension

