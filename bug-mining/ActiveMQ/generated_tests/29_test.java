import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.broker.jmx.ManagedRegionBroker;
import org.apache.activemq.broker.region.RegionBroker;
import org.apache.activemq.command.ActiveMQDestination;
import org.apache.activemq.command.ActiveMQQueue;
import org.apache.activemq.command.ActiveMQTopic;
import org.apache.activemq.command.ConsumerInfo;
import org.apache.activemq.command.ConnectionContext;
import org.apache.activemq.command.ProducerInfo;
import org.apache.activemq.command.SessionInfo;
import org.apache.activemq.store.PersistenceAdapter;
import org.apache.activemq.store.memory.MemoryPersistenceAdapter;
import org.apache.activemq.thread.TaskRunnerFactory;
import org.apache.activemq.usage.UsageManager;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import javax.management.InstanceAlreadyExistsException;
import java.util.concurrent.ConcurrentHashMap;

import static org.junit.Assert.fail;
import static org.mockito.Mockito.*;

public class ReproductionTest {

    private BrokerService brokerService;
    private MBeanServer mbeanServer;
    private ObjectName brokerObjectName;
    private ManagedRegionBroker managedRegionBroker;
    private ConnectionContext connectionContext;
    private SessionInfo sessionInfo;
    private ConsumerInfo consumerInfo;

    @Before
    public void setUp() throws Exception {
        brokerService = mock(BrokerService.class);
        mbeanServer = mock(MBeanServer.class);
        brokerObjectName = new ObjectName("org.apache.activemq:type=Broker,brokerName=localhost");
        TaskRunnerFactory taskRunnerFactory = mock(TaskRunnerFactory.class);
        UsageManager memoryManager = mock(UsageManager.class);
        PersistenceAdapter adapter = new MemoryPersistenceAdapter();

        managedRegionBroker = new ManagedRegionBroker(brokerService, mbeanServer, brokerObjectName, taskRunnerFactory, memoryManager, adapter);
        managedRegionBroker.start();

        connectionContext = new ConnectionContext();
        sessionInfo = new SessionInfo(connectionContext.getConnectionId(), 1);
        consumerInfo = new ConsumerInfo(sessionInfo, 1);
        consumerInfo.setDestination(new ActiveMQTopic("testTopic"));
    }

    @After
    public void tearDown() throws Exception {
        managedRegionBroker.stop();
    }

    @Test
    public void testInstanceAlreadyExistsExceptionOnRedeployWithJMXEnabled() throws Exception {
        // Register a subscription
        managedRegionBroker.registerSubscription(connectionContext, mock(Subscription.class));

        // Attempt to register the same subscription again, which should throw InstanceAlreadyExistsException
        try {
            managedRegionBroker.registerSubscription(connectionContext, mock(Subscription.class));
            fail("Expected InstanceAlreadyExistsException to be thrown");
        } catch (Exception e) {
            if (!(e instanceof InstanceAlreadyExistsException)) {
                fail("Expected InstanceAlreadyExistsException but got " + e.getClass().getName());
            }
        }
    }
}