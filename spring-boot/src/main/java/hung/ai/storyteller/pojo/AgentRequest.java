package hung.ai.storyteller.pojo;

import java.util.UUID;

import lombok.Data;
import tools.jackson.databind.JsonNode;

@Data
public class AgentRequest {

    public enum Type {
        WRITER_FIRST_DRAFT,
        WRITER_REVISE_MANUSCRIPT,
        EDITOR_REVIEW_MANUSCRIPT
    }

    final private Flow.Type flowType;
    final private UUID flowId;
    final private String agentId;
    private UUID chatId;
    final private UUID requestId = UUID.randomUUID();
    final private Type type;
    
    private JsonNode userInput;

}