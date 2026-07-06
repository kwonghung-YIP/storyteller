package hung.ai.storyteller.repo;

import java.util.UUID;

import org.springframework.data.repository.CrudRepository;
import org.springframework.stereotype.Repository;

import hung.ai.storyteller.pojo.Flow;

@Repository
public interface FlowRepository extends CrudRepository<Flow, UUID> {

}
