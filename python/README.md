## Initiate the project
```bash
uv init python
uv add pytest pytest-asyncio
uv add hydra-core --prerelease allow
uv add google-genai
uv add SQLAlchemy psycopg2-binary asyncpg
uv add Jinja2
uv add pika
```

## Request Sample
```json
{
    "requestId": "dad08660-dcce-480c-bb81-8a71876522a8",
    "type": "WRITER_FIRST_DRAFT",
    "agentId": "writer#1",
    "chatId": null,
    "flowId": "cb329f7a-dd27-41bd-af66-b493cfcf84f1",
    "flowType": "STORY",
    "userInput": {
        "idea": "Tell me a story about how Sponge learn self-aware!"
    }
}
```