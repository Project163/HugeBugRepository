import org.apache.activemq.store.jdbc.adapter.DefaultJDBCAdapter;
import org.apache.activemq.store.jdbc.TransactionContext;
import org.apache.activemq.store.jdbc.JDBCMessageRecoveryListener;
import org.apache.activemq.command.ActiveMQDestination;
import org.junit.Test;
import org.mockito.Mockito;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class ReproductionTest {

    @Test
    public void testAckedPersistentMessagesRedeliveredAfterBrokerRestart() throws Exception {
        DefaultJDBCAdapter adapter = new DefaultJDBCAdapter();

        TransactionContext transactionContext = Mockito.mock(TransactionContext.class);
        Connection connection = Mockito.mock(Connection.class);
        PreparedStatement preparedStatement = Mockito.mock(PreparedStatement.class);
        ResultSet resultSet = Mockito.mock(ResultSet.class);

        Mockito.when(transactionContext.getConnection()).thenReturn(connection);
        Mockito.when(connection.prepareStatement(Mockito.anyString())).thenReturn(preparedStatement);
        Mockito.when(preparedStatement.executeQuery()).thenReturn(resultSet);
        Mockito.when(resultSet.next()).thenReturn(true, false);
        Mockito.when(resultSet.getLong(1)).thenReturn(1L);
        Mockito.when(resultSet.getString(2)).thenReturn("messageReference");

        ActiveMQDestination destination = Mockito.mock(ActiveMQDestination.class);
        Mockito.when(destination.getQualifiedName()).thenReturn("destinationName");

        JDBCMessageRecoveryListener listener = Mockito.mock(JDBCMessageRecoveryListener.class);

        adapter.doRecover(transactionContext, destination, listener);

        Mockito.verify(listener).recoverMessageReference("messageReference");
    }
}