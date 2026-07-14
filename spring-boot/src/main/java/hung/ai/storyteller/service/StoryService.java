package hung.ai.storyteller.service;

import java.util.Map;

import org.springframework.stereotype.Service;

import hung.ai.storyteller.agent.RequestSender;
import hung.ai.storyteller.pojo.AgentRequest;
import hung.ai.storyteller.pojo.AgentResponse;
import hung.ai.storyteller.pojo.Flow;
import hung.ai.storyteller.pojo.Story;
import hung.ai.storyteller.repo.FlowRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@Slf4j
@RequiredArgsConstructor
@Service
public class StoryService implements FlowService {

    final private ObjectMapper objectMapper;
    final private FlowRepository repository;
    final private RequestSender sender;

    final private Map<AgentResponse.Type, ResponseHandler> handlers = Map.of(
        AgentResponse.Type.WRITER_MANUSCRIPT, this::handleWriterResponse,
        AgentResponse.Type.EDITOR_FEEDBACK, this::handleEditorResponse
    );

    public Story requestFirstDraft(String idea) {
        Story story = new Story();
        story.setIdea(idea);
        story.setState(Story.State.INIT);
        //story.getStories().add("edition#1");
        //story.getComments().add("comment#1");
        repository.save(story);

        AgentRequest writerRequest = new AgentRequest(
            story.getType(), story.getFlowId(),"writer#1",
            AgentRequest.Type.WRITER_FIRST_DRAFT);
        
        writerRequest.setChatId(story.getWriterChatId());
        
        var userInput = objectMapper.createObjectNode();
        userInput.put("idea",idea);
        writerRequest.setUserInput(userInput);

        sender.sendRequest(writerRequest);

        return story;
    }

    @Override
    public void handleResponse(Flow flow, AgentResponse response) {
        if (flow instanceof Story story) {
            var handler = handlers.get(response.getType());
            if (handler != null) {
                handler.handle(story, response);
                return;
            }
        }
    }

    @FunctionalInterface
    public interface ResponseHandler {
        void handle(Story story, AgentResponse resp);
    }

    public void handleWriterResponse(Story story, AgentResponse response) {
        JsonNode output = response.getModelOutput();
        String manuscript = output.get("manuscript").stringValue();
        story.setWriterChatId(response.getChatId());
        story.getManuscripts().add(manuscript);

        //log.info("Received {} edition story {}.", story.getStories().size(), draft);

        if (story.getNumOfReview() < 2) {
            story.setState(Story.State.REVIEW);

            AgentRequest editorRequest = new AgentRequest(
                story.getType(), story.getFlowId(), "editor#1", 
                AgentRequest.Type.EDITOR_REVIEW_MANUSCRIPT);

            editorRequest.setChatId(story.getEditorChatId());

            var input = objectMapper.createObjectNode();
            input.put("idea", story.getIdea());
            input.put("manuscript", manuscript);
            editorRequest.setUserInput(input);

            sender.sendRequest(editorRequest);     
        } else {
            story.setState(Story.State.PUBLISHED);
        }
    }

    public void handleEditorResponse(Story story, AgentResponse response) {
        JsonNode output = response.getModelOutput();
        boolean hasFeedback = output.get("hasFeedback").booleanValue();
        story.setEditorChatId(response.getChatId());
        
        if (hasFeedback) {
            story.setState(Story.State.EDITING);

            String feedback = output.get("feedback").stringValue();
            //log.info("Editor has comment on the latest edition :[%s].".formatted(comment));

            story.getFeedbacks().add(feedback);

            AgentRequest writerRequest = new AgentRequest(
                story.getType(), story.getFlowId(), "writer#1", 
                AgentRequest.Type.WRITER_REVISE_MANUSCRIPT);

            writerRequest.setChatId(story.getWriterChatId());

            var input = objectMapper.createObjectNode();
            input.put("feedback", feedback);
            writerRequest.setUserInput(input);

            sender.sendRequest(writerRequest);
        } else {
            log.info("Editor has no futher feedback on the story.");
            
            story.setState(Story.State.PUBLISHED);
        }
    }
}
