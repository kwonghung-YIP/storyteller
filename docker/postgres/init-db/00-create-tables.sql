CREATE TABLE IF NOT EXISTS chat (
    id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_id VARCHAR(30) NOT NULL,
    created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_message (
    id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    chat_id UUID REFERENCES chat(id),
    seq INT2 NOT NULL,
    role VARCHAR(10) NOT NULL,
    request_id UUID,
    response_id UUID,
    text TEXT,
    created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_response (
    agent_id VARCHAR(30) NOT NULL,
    request_id UUID NOT NULL,
    response_id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    model_resp_id VARCHAR(255) NOT NULL,
    response_json JSONB NOT NULL,
    created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS google_genai_batch_job (
    name VARCHAR(255) NOT NULL PRIMARY KEY,
    request_id UUID,
    response_id UUID REFERENCES model_response(response_id),
    display_name VARCHAR(255) NOT NULL,
    state VARCHAR(30) NOT NULL,
    create_time TIMESTAMP,
    start_time TIMESTAMP,
    update_time TIMESTAMP,
    end_time TIMESTAMP,
    error JSONB,
    batchjob_json JSONB NOT NULL
)