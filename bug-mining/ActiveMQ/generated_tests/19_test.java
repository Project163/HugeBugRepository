import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.broker.TransportConnector;
import org.apache.activemq.thread.TaskRunnerFactory;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

public class ReproductionTest {

    @Test
    public void testTaskRunnerFactoryNotSetWhenUseJmxIsTrue() throws Exception {
        BrokerService brokerService = new BrokerService();
        brokerService.setUseJmx(true);
        TaskRunnerFactory taskRunnerFactory = new TaskRunnerFactory();
        brokerService.setTaskRunnerFactory(taskRunnerFactory);

        TransportConnector connector = new TransportConnector();
        TransportConnector addedConnector = brokerService.addConnector(connector);

        assertNull(addedConnector.getTaskRunnerFactory());
    }
}