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
    batchjob_json JSONB NOT NULL,
    ver SMALLINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS google_genai_batch_job_audit (
    name VARCHAR(255) NOT NULL,
    request_id UUID,
    response_id UUID REFERENCES model_response(response_id),
    display_name VARCHAR(255) NOT NULL,
    state VARCHAR(30) NOT NULL,
    create_time TIMESTAMP,
    start_time TIMESTAMP,
    update_time TIMESTAMP,
    end_time TIMESTAMP,
    error JSONB,
    batchjob_json JSONB NOT NULL,
    ver SMALLINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NULL,
    PRIMARY KEY(name, ver)
);

CREATE OR REPLACE FUNCTION google_genai_batch_job_audit() 
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        new.ver = 1;
        new.created_at = CURRENT_TIMESTAMP;
    ELSIF TG_OP = 'UPDATE' THEN
        new.ver = old.ver + 1;
        new.updated_at = CURRENT_TIMESTAMP;

        INSERT INTO google_genai_batch_job_audit
        VALUES (
            old.name, old.request_id, old.response_id, old.display_name, old.state,
            old.create_time, old.start_time, old.update_time, old.end_time,
            old.error, old.batchjob_json,
            old.ver, old.created_at, old.updated_at
        );
    END IF;

    RETURN new;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER google_genai_batch_job_audit
BEFORE INSERT OR UPDATE ON google_genai_batch_job
FOR EACH ROW
EXECUTE FUNCTION google_genai_batch_job_audit();