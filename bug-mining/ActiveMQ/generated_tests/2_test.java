import org.apache.activemq.ActiveMQMessageConsumer;
import org.apache.activemq.ActiveMQSession;
import org.apache.activemq.command.MessageAck;
import org.apache.activemq.command.MessageDispatch;
import org.apache.activemq.command.MessageId;
import org.apache.activemq.command.ConsumerId;
import org.apache.activemq.RedeliveryPolicy;
import org.apache.activemq.util.Scheduler;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import javax.jms.JMSException;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;

public class ReproductionTest {

    private ActiveMQMessageConsumer consumer;
    private ActiveMQSession session;
    private RedeliveryPolicy redeliveryPolicy;
    private Scheduler scheduler;

    @Before
    public void setUp() throws Exception {
        session = Mockito.mock(ActiveMQSession.class);
        redeliveryPolicy = Mockito.mock(RedeliveryPolicy.class);
        scheduler = Mockito.mock(Scheduler.class);

        consumer = Mockito.mock(ActiveMQMessageConsumer.class, Mockito.CALLS_REAL_METHODS);
        Field sessionField = ActiveMQMessageConsumer.class.getDeclaredField("session");
        sessionField.setAccessible(true);
        sessionField.set(consumer, session);

        Field redeliveryPolicyField = ActiveMQMessageConsumer.class.getDeclaredField("redeliveryPolicy");
        redeliveryPolicyField.setAccessible(true);
        redeliveryPolicyField.set(consumer, redeliveryPolicy);

        Field schedulerField = ActiveMQMessageConsumer.class.getDeclaredField("scheduler");
        schedulerField.setAccessible(true);
        schedulerField.set(consumer, scheduler);

        Field deliveredMessagesField = ActiveMQMessageConsumer.class.getDeclaredField("deliveredMessages");
        deliveredMessagesField.setAccessible(true);
        deliveredMessagesField.set(consumer, new ArrayList<>());

        Field unconsumedMessagesField = ActiveMQMessageConsumer.class.getDeclaredField("unconsumedMessages");
        unconsumedMessagesField.setAccessible(true);
        unconsumedMessagesField.set(consumer, new org.apache.activemq.util.LinkedListMessageDispatchChannel());

        Field startedField = ActiveMQMessageConsumer.class.getDeclaredField("started");
        startedField.setAccessible(true);
        startedField.set(consumer, true);

        Mockito.when(session.isTransacted()).thenReturn(false);
        Mockito.when(redeliveryPolicy.getMaximumRedeliveries()).thenReturn(3);
        Mockito.when(redeliveryPolicy.getInitialRedeliveryDelay()).thenReturn(1000);
        Mockito.when(redeliveryPolicy.isUseExponentialBackOff()).thenReturn(false);
        Mockito.when(redeliveryPolicy.getBackOffMultiplier()).thenReturn(2);
    }

    @Test
    public void testRedeliveryLogicBug() throws JMSException {
        MessageDispatch md = new MessageDispatch();
        md.setMessageId(new MessageId("ID:localhost-56789-12345-1:1:1:1"));
        md.setConsumerId(new ConsumerId("ID:localhost-56789-12345-1:1:1"));
        md.setMessage(new org.apache.activemq.command.ActiveMQTextMessage());

        List<MessageDispatch> deliveredMessages = new ArrayList<>();
        deliveredMessages.add(md);

        Field deliveredMessagesField = ActiveMQMessageConsumer.class.getDeclaredField("deliveredMessages");
        deliveredMessagesField.setAccessible(true);
        deliveredMessagesField.set(consumer, deliveredMessages);

        consumer.rollback();
        consumer.rollback();
        consumer.rollback();

        // After 4th rollback, messages should be sent to DLQ
        consumer.rollback();

        // Verify that the message was NACKed and sent to DLQ
        Mockito.verify(session).asyncSendPacket(Mockito.argThat(ack -> ack.getAckType() == MessageAck.POSION_ACK_TYPE));
    }
}