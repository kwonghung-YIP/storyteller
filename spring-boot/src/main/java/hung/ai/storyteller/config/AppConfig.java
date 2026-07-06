package hung.ai.storyteller.config;

import java.util.HashMap;
import java.util.Map;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import hung.ai.storyteller.pojo.Flow;
import hung.ai.storyteller.service.FlowService;
import hung.ai.storyteller.service.StoryService;
import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
@Configuration
public class AppConfig {

    final private StoryService storyService;

    @Bean
    public Map<Flow.Type, FlowService> flowTypeToServiceMapping() {
        var mapping = new HashMap<Flow.Type, FlowService>();
        mapping.put(Flow.Type.STORY, storyService);
        return mapping;
    }
}
