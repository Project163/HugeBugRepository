import org.apache.activemq.command.ActiveMQDestination;
import org.apache.activemq.command.ActiveMQQueue;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class ReproductionTest {

    @Test
    public void testDemandBasedPublishing() {
        ActiveMQDestination queue1 = new ActiveMQQueue("queue1");
        ActiveMQDestination queue2 = new ActiveMQQueue("queue2");
        ActiveMQDestination[] destinations = {queue1, queue2};
        ActiveMQDestination compositeDestination = new ActiveMQQueue("compositeQueue");
        compositeDestination.setCompositeDestinations(destinations);

        int result = compositeDestination.compareTo(queue1);
        assertEquals(1, result);
    }
}