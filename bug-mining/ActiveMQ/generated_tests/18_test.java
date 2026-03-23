import org.apache.activemq.store.jdbc.TransactionContext;
import org.apache.activemq.util.IOExceptionSupport;
import org.junit.Test;
import org.mockito.Mockito;

import javax.sql.DataSource;
import java.io.IOException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;

public class ReproductionTest {

    @Test(expected = IOException.class)
    public void testDeadlockInCloseMethod() throws IOException, SQLException {
        DataSource dataSource = Mockito.mock(DataSource.class);
        Connection connection = Mockito.mock(Connection.class);
        PreparedStatement addMessageStatement = Mockito.mock(PreparedStatement.class);
        PreparedStatement removedMessageStatement = Mockito.mock(PreparedStatement.class);
        PreparedStatement updateLastAckStatement = Mockito.mock(PreparedStatement.class);

        Mockito.when(dataSource.getConnection()).thenReturn(connection);
        Mockito.when(connection.prepareStatement(Mockito.anyString())).thenReturn(addMessageStatement, removedMessageStatement, updateLastAckStatement);

        TransactionContext transactionContext = new TransactionContext(dataSource);
        transactionContext.addMessageStatement = addMessageStatement;
        transactionContext.removedMessageStatement = removedMessageStatement;
        transactionContext.updateLastAckStatement = updateLastAckStatement;

        transactionContext.begin();
        transactionContext.commit();

        transactionContext.close();
    }
}