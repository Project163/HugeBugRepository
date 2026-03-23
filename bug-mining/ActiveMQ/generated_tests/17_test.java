import org.apache.activemq.broker.ConnectionContext;
import org.apache.activemq.broker.region.Queue;
import org.apache.activemq.broker.region.Subscription;
import org.apache.activemq.command.ConsumerId;
import org.apache.activemq.command.Message;
import org.apache.activemq.command.MessageEvaluationContext;
import org.apache.activemq.store.MessageStore;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;

public class ReproductionTest {

    private Queue queue;
    private ConnectionContext context;
    private Subscription sub;
    private Message message;
    private MessageStore store;
    private MessageEvaluationContext msgContext;

    @Before
    public void setUp() throws Exception {
        queue = Mockito.mock(Queue.class, Mockito.CALLS_REAL_METHODS);
        Field messagesField = Queue.class.getDeclaredField("messages");
        messagesField.setAccessible(true);
        messagesField.set(queue, new ArrayList<>());

        context = Mockito.mock(ConnectionContext.class);
        sub = Mockito.mock(Subscription.class);
        message = Mockito.mock(Message.class);
        store = Mockito.mock(MessageStore.class);
        msgContext = Mockito.mock(MessageEvaluationContext.class);

        Mockito.when(context.getMessageEvaluationContext()).thenReturn(msgContext);
        Mockito.when(message.isPersistent()).thenReturn(true);
        Mockito.when(message.getRegionDestination()).thenReturn(queue);
        Mockito.when(queue.getStore()).thenReturn(store);
    }

    @Test
    public void testDeadlockInQueueClusterTest() throws Exception {
        queue.send(context, message);
        queue.removeSubscription(context, sub);
    }
}