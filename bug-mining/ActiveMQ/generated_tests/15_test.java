import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.broker.TransportConnector;
import org.apache.activemq.transport.TransportServer;
import org.apache.activemq.transport.vm.VMTransportFactory;
import org.apache.activemq.transport.vm.VMTransportServer;
import org.junit.Test;
import java.net.URI;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertNotNull;

public class ReproductionTest {

    @Test
    public void testTaskRunnerFactoryNotSetWhenUseJmxIsTrue() throws Exception {
        BrokerService brokerService = new BrokerService();
        brokerService.setUseJmx(true);

        URI bindAddress = new URI("vm://localhost");
        TransportServer transportServer = new VMTransportFactory().doBind(bindAddress);
        TransportConnector connector = new TransportConnector();
        connector.setTransportServer(transportServer);

        TransportConnector addedConnector = brokerService.addConnector(connector);

        assertNull("TaskRunnerFactory should not be set when JMX is used and connector is managed", addedConnector.getTaskRunnerFactory());
    }
}