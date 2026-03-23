import org.apache.activemq.network.DemandForwardingBridge;
import org.apache.activemq.command.Message;
import org.apache.activemq.command.MessageDispatch;
import org.apache.activemq.command.ConsumerInfo;
import org.apache.activemq.command.BrokerInfo;
import org.apache.activemq.command.BrokerId;
import org.apache.activemq.command.Command;
import org.apache.activemq.command.CommandTypes;
import org.apache.activemq.network.DemandSubscription;
import org.apache.activemq.util.ServiceSupport;
import org.junit.Test;
import org.mockito.Mockito;

import java.lang.reflect.Field;

public class ReproductionTest {

    @Test
    public void testMessageLossInTwoBrokerNetwork() throws Exception {
        DemandForwardingBridge bridge = Mockito.mock(DemandForwardingBridge.class, Mockito.CALLS_REAL_METHODS);

        // Mock dependencies
        Command command = Mockito.mock(MessageDispatch.class);
        MessageDispatch md = Mockito.mock(MessageDispatch.class);
        Message message = Mockito.mock(Message.class);
        DemandSubscription sub = Mockito.mock(DemandSubscription.class);
        ConsumerInfo info = Mockito.mock(ConsumerInfo.class);
        BrokerInfo brokerInfo = Mockito.mock(BrokerInfo.class);
        BrokerId brokerId = Mockito.mock(BrokerId.class);

        // Set up expectations
        Mockito.when(command.isMessageDispatch()).thenReturn(true);
        Mockito.when(((MessageDispatch) command).getMessage()).thenReturn(message);
        Mockito.when(bridge.subscriptionMapByLocalId.get(((MessageDispatch) command).getConsumerId())).thenReturn(sub);
        Mockito.when(message.isRecievedByDFBridge()).thenReturn(false);
        Mockito.when(message.getBrokerPath()).thenReturn(new BrokerId[]{brokerId});
        Mockito.when(bridge.remoteBrokerPath).thenReturn(new BrokerId[]{brokerId});
        Mockito.when(message.isAdvisory()).thenReturn(true);
        Mockito.when(message.getDataStructure()).thenReturn(info);
        Mockito.when(info.getDataStructureType()).thenReturn(CommandTypes.CONSUMER_INFO);
        Mockito.when(info.isNetworkSubscription()).thenReturn(true);

        // Inject necessary fields
        Field localBrokerPathField = DemandForwardingBridge.class.getDeclaredField("localBrokerPath");
        localBrokerPathField.setAccessible(true);
        localBrokerPathField.set(bridge, new BrokerId[]{brokerId});

        Field remoteBrokerPathField = DemandForwardingBridge.class.getDeclaredField("remoteBrokerPath");
        remoteBrokerPathField.setAccessible(true);
        remoteBrokerPathField.set(bridge, new BrokerId[]{brokerId});

        // Call the method under test
        bridge.serviceLocalCommand(command);
    }
}