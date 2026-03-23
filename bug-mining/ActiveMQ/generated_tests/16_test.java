import org.apache.activemq.store.jdbc.TransactionContext;
import org.apache.activemq.store.jdbc.adapter.OracleJDBCAdapter;
import org.apache.activemq.store.jdbc.Statements;
import org.apache.activemq.util.IOExceptionSupport;
import org.junit.Test;
import org.mockito.Mockito;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;

public class ReproductionTest {

    @Test(expected = IOException.class)
    public void testCloseWithoutBegin() throws IOException {
        DataSource dataSource = Mockito.mock(DataSource.class);
        Connection connection = Mockito.mock(Connection.class);
        PreparedStatement preparedStatement = Mockito.mock(PreparedStatement.class);

        Mockito.when(dataSource.getConnection()).thenReturn(connection);
        Mockito.when(connection.prepareStatement(Mockito.anyString())).thenReturn(preparedStatement);

        TransactionContext transactionContext = new TransactionContext(dataSource);
        transactionContext.close();
    }
}