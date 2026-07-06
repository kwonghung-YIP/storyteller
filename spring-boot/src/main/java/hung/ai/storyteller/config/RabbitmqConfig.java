package hung.ai.storyteller.config;

import org.springframework.amqp.core.AmqpTemplate;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.amqp.dsl.Amqp;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.dsl.Transformers;
import org.springframework.messaging.MessageChannel;

import hung.ai.storyteller.pojo.AgentRequest;
import hung.ai.storyteller.pojo.AgentResponse;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Configuration
public class RabbitmqConfig {

    @Value("${messaging.rabbitmq.outbound.agent-request.exchange}")
    private String requestOutFlowExchange;

    @Value("${messaging.rabbitmq.outbound.agent-request.routing-key}")
    private String requestOutFlowRoutingKey;

    @Value("${messaging.rabbitmq.inbound.agent-response.queue}")
    private String responseInFlowQueue;


    @Bean
    public MessageChannel requestOutChannel() {
        var channel = new DirectChannel();
        return channel;
    }

    @Bean
    public IntegrationFlow requestOutFlow(AmqpTemplate amqpTemplate) {
        return IntegrationFlow
            .from(requestOutChannel())
            //.log()
            .log(msg -> {
                AgentRequest request = (AgentRequest)msg.getPayload();
                return "Send request %s[%s]".formatted(request.getFlowId(),request.getType());
            })
            //.transform(new ObjectToJsonTransformer())
            .transform(Transformers.toJson())
            //.log()
            .handle(Amqp.outboundAdapter(amqpTemplate)
                .exchangeName(requestOutFlowExchange)
                .routingKey(requestOutFlowRoutingKey))
            .get();
    }

    @Bean
    public IntegrationFlow responseInFlow(ConnectionFactory connectionFactory) {
        return IntegrationFlow
            .from(Amqp.inboundAdapter(connectionFactory, responseInFlowQueue))
            .transform(Transformers.fromJson(AgentResponse.class))
            .log(msg -> {
                AgentResponse response = (AgentResponse)msg.getPayload();
                return "Recevied Response %s[%s]".formatted(response.getFlowId(),response.getType());
            })
            //.log()
            //.handle((p,h) -> {
            //    log.info("here!");
            //    return "";
            //})
            //.nullChannel();
            .channel("response-in-channel")
            .get();
    }
}
