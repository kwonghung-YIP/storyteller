package hung.ai.storyteller.pojo;

import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;
import tools.jackson.databind.JsonNode;

@Data
public class AgentResponse {

    public enum Type {
        WRITER_MANUSCRIPT,
        EDITOR_FEEDBACK
    }

    final private Flow.Type flowType;
    final private UUID flowId;
    final private String agentId;
    private UUID chatId;
    final private UUID requestId;
    final private UUID responseId;
    final private Type type;
    
    private JsonNode modelOutput;

    @JsonCreator
    public AgentResponse(
        @JsonProperty("flowType")   Flow.Type flowType,
        @JsonProperty("flowId")     UUID flowId,
        @JsonProperty("agentId")    String agentId,
        @JsonProperty("chatId")     UUID chatId,
        @JsonProperty("requestId")  UUID requestId,
        @JsonProperty("responseId") UUID responseId,
        @JsonProperty("type")       Type type
    ) {
        this.flowType = flowType;
        this.flowId = flowId;
        this.agentId = agentId;
        this.chatId = chatId;
        this.requestId = requestId;
        this.responseId = responseId;
        this.type = type;
    }

    public AgentResponse(AgentRequest request, Type type) {
        this.flowType = request.getFlowType();
        this.flowId = request.getFlowId();
        this.agentId = request.getAgentId();
        this.chatId = request.getChatId();
        this.requestId = request.getRequestId();
        this.responseId = UUID.randomUUID();
        this.type = type;
    }

}