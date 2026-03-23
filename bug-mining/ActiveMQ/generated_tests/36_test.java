import org.apache.activemq.transport.InactivityMonitor;
import org.apache.activemq.transport.Transport;
import org.apache.activemq.transport.TransportFilter;
import org.apache.activemq.transport.TransportListener;
import org.apache.activemq.command.Command;
import org.apache.activemq.command.KeepAliveInfo;
import org.junit.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.Assert.fail;
import static org.mockito.Mockito.*;

public class ReproductionTest {

    @Test
    public void testMaxInactivityDuration() throws Exception {
        long maxInactivityDuration = 1000; // 1 second
        Transport next = Mockito.mock(Transport.class);
        TransportListener listener = Mockito.mock(TransportListener.class);
        InactivityMonitor monitor = new InactivityMonitor(next, maxInactivityDuration);

        monitor.setTransportListener(listener);
        monitor.start();

        // Simulate no activity for more than maxInactivityDuration
        Thread.sleep(maxInactivityDuration + 100);

        // Verify that an exception is thrown due to inactivity
        verify(listener, timeout(maxInactivityDuration + 200)).onException(any(IOException.class));
    }
}