import org.apache.activemq.broker.ConnectionContext;
import org.apache.activemq.broker.region.PrefetchSubscription;
import org.apache.activemq.command.MessageAck;
import org.apache.activemq.command.MessageDispatchNotification;
import org.apache.activemq.command.MessageId;
import org.apache.activemq.command.MessageReference;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import java.util.Iterator;
import java.util.LinkedList;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class ReproductionTest {

    private PrefetchSubscription prefetchSubscription;
    private ConnectionContext context;
    private MessageAck ack;
    private MessageReference messageReference;
    private MessageId messageId;

    @Before
    public void setUp() throws Exception {
        prefetchSubscription = Mockito.mock(PrefetchSubscription.class, Mockito.CALLS_REAL_METHODS);
        LinkedList<MessageReference> dispatched = new LinkedList<>();
        LinkedList<MessageReference> matched = new LinkedList<>();
        Mockito.when(prefetchSubscription.getDispatched()).thenReturn(dispatched);
        Mockito.when(prefetchSubscription.getMatched()).thenReturn(matched);

        context = Mockito.mock(ConnectionContext.class);
        Mockito.when(context.isInTransaction()).thenReturn(true);

        messageId = new MessageId("test:1:1");
        messageReference = Mockito.mock(MessageReference.class);
        Mockito.when(messageReference.getMessageId()).thenReturn(messageId);

        ack = new MessageAck();
        ack.setFirstMessageId(messageId);
        ack.setLastMessageId(messageId);
        ack.setStandardAck(true);

        dispatched.add(messageReference);
    }

    @Test
    public void testInvalidAcknowledgementInTransaction() throws Throwable {
        prefetchSubscription.acknowledge(context, ack);
        assertTrue(prefetchSubscription.getDispatched().contains(messageReference));
    }
}