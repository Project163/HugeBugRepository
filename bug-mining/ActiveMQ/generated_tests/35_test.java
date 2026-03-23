import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.transport.Transport;
import org.apache.activemq.transport.vm.VMTransportFactory;
import org.apache.activemq.util.URISupport;
import org.junit.Test;

import java.net.URI;
import java.util.HashMap;
import java.util.Map;

public class ReproductionTest {

    @Test
    public void testTaskRunnerFactoryNotCarriedAlong() throws Exception {
        VMTransportFactory factory = new VMTransportFactory();
        URI brokerURI = new URI("broker://()/localhost?broker.persistent=false");
        URI location = new URI("vm://localhost?brokerConfig=" + brokerURI.toString());

        Transport transport = factory.createTransport(location);

        BrokerService broker = BrokerRegistry.getInstance().lookup("localhost");
        assert broker != null : "Broker should not be null";

        // Assuming TaskRunnerFactory is a property that should be set and checked
        // This is a placeholder for the actual property check
        // Replace with actual property access if available
        assert broker.getTaskRunnerFactory() != null : "TaskRunnerFactory should be carried along to Broker-to-Broker connections";
    }
}