package hung.ai.storyteller.pojo;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Transient;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.extern.slf4j.Slf4j;
import tools.jackson.databind.ObjectMapper;

@Slf4j
@Data
@EqualsAndHashCode(callSuper = true)
@Entity
public class Story extends Flow {

    public enum State {
        INIT,
        EDITING,
        REVIEW,
        PUBLISHED
    }

    public Story() {
        super(Flow.Type.STORY);
    }

    private UUID writerChatId;

    private UUID editorChatId;

    private String idea;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "writer_manuscript", joinColumns = @JoinColumn(name = "flow_id"))
    @Column(columnDefinition = "TEXT")
    private List<String> manuscripts = new ArrayList<>();

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "editor_feedback", joinColumns = @JoinColumn(name = "flow_id"))
    @Column(columnDefinition = "TEXT")
    private List<String> feedbacks = new ArrayList<>();

    @Enumerated(EnumType.STRING)
    private State state = State.INIT;

    @Transient
    private ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public Type getType() {
        return Flow.Type.STORY;
    }
    
    public int getNumOfReview() {
        return this.feedbacks.size();
    }

}