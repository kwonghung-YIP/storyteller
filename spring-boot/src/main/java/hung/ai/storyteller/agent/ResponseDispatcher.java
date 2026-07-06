package hung.ai.storyteller.agent;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.repository.CrudRepository;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.stereotype.Component;

import hung.ai.storyteller.pojo.AgentResponse;
import hung.ai.storyteller.pojo.Flow;
import hung.ai.storyteller.service.FlowService;
import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
@Component
public class ResponseDispatcher {

    final private CrudRepository<Flow, UUID> flowRepo;
    final private Map<Flow.Type, FlowService> services; 

    @ServiceActivator(inputChannel = "response-in-channel")
    public void dispatchResponse(AgentResponse response) {
        // 1. Search the flow instance by flow type and Id in the response.
        Optional<Flow> result = flowRepo.findById(response.getFlowId());
        result.ifPresent(flow -> {
            // 2. Identify the handler function by flow type and response type.
            FlowService service = services.get(flow.getType());
            // 3. Pass the response and this agent proxy to the handler function.
            service.handleResponse(flow, response);
            // 4. Save any change on flow after invoke the handler
            flowRepo.save(flow);
        });
    }
    
}
