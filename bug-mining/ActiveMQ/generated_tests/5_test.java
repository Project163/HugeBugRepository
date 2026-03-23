import org.apache.activemq.network.DemandForwardingBridge;
import org.apache.activemq.command.ConsumerId;
import org.apache.activemq.command.ConsumerInfo;
import org.apache.activemq.command.Message;
import org.apache.activemq.command.MessageDispatch;
import org.apache.activemq.command.MessageEvaluationContext;
import org.apache.activemq.command.RemoveInfo;
import org.apache.activemq.command.BrokerId;
import org.apache.activemq.command.BrokerInfo;
import org.apache.activemq.command.Command;
import org.apache.activemq.command.CommandTypes;
import org.apache.activemq.command.MessageAck;
import org.apache.activemq.command.ProducerId;
import org.apache.activemq.command.ActiveMQDestination;
import org.apache.activemq.command.ActiveMQTopic;
import org.apache.activemq.command.TransactionId;
import org.apache.activemq.command.WireFormatInfo;
import org.apache.activemq.util.ServiceSupport;
import org.apache.activemq.util.JMSExceptionSupport;
import org.junit.Test;
import org.mockito.Mockito;

import javax.jms.JMSException;
import java.io.IOException;

public class ReproductionTest {

    @Test
    public void testMessageLossInTwoBrokerNetwork() throws Exception {
        DemandForwardingBridge bridge = Mockito.mock(DemandForwardingBridge.class, Mockito.CALLS_REAL_METHODS);
        ConsumerInfo consumerInfo = new ConsumerInfo();
        consumerInfo.setConsumerId(new ConsumerId("consumer:1"));
        consumerInfo.setNetworkSubscription(true);

        DemandForwardingBridge.DemandSubscription subscription = bridge.new DemandSubscription(consumerInfo, null);
        subscription.localInfo = consumerInfo;
        subscription.remoteInfo = consumerInfo;

        Mockito.when(bridge.localBroker.oneway(Mockito.any())).thenReturn(null);
        Mockito.when(bridge.remoteBroker.oneway(Mockito.any())).thenReturn(null);

        bridge.subscriptionMapByRemoteId.put(consumerInfo.getConsumerId(), subscription);
        bridge.subscriptionMapByLocalId.put(consumerInfo.getConsumerId(), subscription);

        MessageDispatch messageDispatch = new MessageDispatch();
        messageDispatch.setConsumerId(consumerInfo.getConsumerId());
        Message message = new Message();
        message.setBrokerPath(new BrokerId[]{new BrokerId("broker:1")});
        messageDispatch.setMessage(message);

        bridge.serviceLocalCommand(messageDispatch);

        RemoveInfo removeInfo = new RemoveInfo();
        removeInfo.setObjectId(consumerInfo.getConsumerId());
        bridge.serviceLocalCommand(removeInfo);

        // This test should fail if messages are lost
        Mockito.verify(bridge.remoteBroker, Mockito.times(1)).oneway(message);
    }
}