package hung.ai.storyteller.service;

import hung.ai.storyteller.pojo.AgentResponse;
import hung.ai.storyteller.pojo.Flow;

public interface FlowService {

    void handleResponse(Flow flow, AgentResponse response);

}
