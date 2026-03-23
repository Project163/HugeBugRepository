import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.broker.TransportConnector;
import org.apache.activemq.thread.TaskRunnerFactory;
import org.junit.Test;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.net.URI;
import java.util.HashMap;

import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertNotNull;

public class ReproductionTest {

    @Test
    public void testTaskRunnerFactoryNotSetWhenJmxEnabled() throws Exception {
        BrokerService brokerService = new BrokerService();
        brokerService.setUseJmx(true);
        MBeanServer mbeanServer = Mockito.mock(MBeanServer.class);
        ObjectName connectorName = new ObjectName("test:name=connector");

        TransportConnector connector = new TransportConnector();
        TaskRunnerFactory taskRunnerFactory = new TaskRunnerFactory();
        connector.setTaskRunnerFactory(taskRunnerFactory);

        brokerService.setManagementContext(new ManagementContext() {
            @Override
            public MBeanServer getMBeanServer() {
                return mbeanServer;
            }

            @Override
            public ObjectName getBrokerObjectName() {
                return new ObjectName("test:name=broker");
            }
        });

        TransportConnector addedConnector = brokerService.addConnector(connector);

        assertNotNull("TaskRunnerFactory should be set", addedConnector.getTaskRunnerFactory());
    }
}