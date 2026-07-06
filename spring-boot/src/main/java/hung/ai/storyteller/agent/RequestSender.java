package hung.ai.storyteller.agent;

import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Component;

import hung.ai.storyteller.pojo.AgentRequest;
import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
@Component
public class RequestSender {

    final private MessageChannel requestOutChannel;

    public void sendRequest(AgentRequest request) {
        var message = MessageBuilder
            .withPayload(request)
            //.setHeader("content-type", "application/json")
            .build();
        requestOutChannel.send(message);
    }
}
