import org.apache.activemq.broker.Broker;
import org.apache.activemq.broker.BrokerFilter;
import org.apache.activemq.broker.ConnectionContext;
import org.apache.activemq.command.ConsumerInfo;
import org.apache.activemq.security.AuthorizationBroker;
import org.apache.activemq.security.AuthorizationMap;
import org.apache.activemq.security.SecurityContext;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import javax.jms.JMSException;

public class ReproductionTest {

    @Test
    public void testClassCastExceptionWithJaasAuthenticationPlugin() throws Exception {
        Broker next = Mockito.mock(Broker.class);
        AuthorizationMap authorizationMap = Mockito.mock(AuthorizationMap.class);
        AuthorizationBroker authorizationBroker = new AuthorizationBroker(next, authorizationMap);

        ConnectionContext context = Mockito.mock(ConnectionContext.class);
        SecurityContext securityContext = Mockito.mock(SecurityContext.class);
        Mockito.when(context.getSecurityContext()).thenReturn(securityContext);

        ConsumerInfo info = new ConsumerInfo();
        info.setDestination(new org.apache.activemq.command.ActiveMQQueue("testQueue"));

        authorizationBroker.addConsumer(context, info);
    }
}