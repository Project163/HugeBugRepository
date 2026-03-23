import org.junit.Test;
import org.junit.Assert;
import org.mockito.Mockito;
import java.lang.reflect.Field;

public class ReproductionTest {

    @Test
    public void testExcludedTests() throws Exception {
        // Mocking the build configuration class
        BuildConfiguration buildConfig = Mockito.mock(BuildConfiguration.class, Mockito.CALLS_REAL_METHODS);

        // Injecting the excluded tests into the mock object
        Field excludesField = BuildConfiguration.class.getDeclaredField("excludes");
        excludesField.setAccessible(true);
        excludesField.set(buildConfig, new String[]{
            "**/ChangeSessionDeliveryModeTest.*",
            "**/DeadLetterTest.*",
            "**/TwoMulticastDiscoveryBrokerTopicSendReceiveTest.*",
            "**/TwoBrokerTopicSendReceiveUsingHttpTest.*",
            "**/TopicClusterTest.*",
            "**/MultiBrokersMultiClientsTest.*",
            "**/MultiBrokersMultiClientsUsingTcpTest.*",
            "**/ThreeBrokerQueueNetworkTest.*",
            "**/ThreeBrokerTopicNetworkTest.*",
            "**/ThreeBrokerTopicNetworkUsingTcpTest.*",
            "**/TwoBrokerTopicSendReceiveUsingTcpTest.*",
            "**/TwoBrokerQueueClientsReconnectTest.*",
            "**/TwoBrokerMulticastQueueTest.*",
            "**/PublishOnQueueConsumedMessageUsingActivemqXMLTest.*",
            "**/PublishOnTopicConsumerMessageUsingActivemqXMLTest.*",
            "**/ThreeBrokerQueueNetworkUsingTcpTest.*",
            "**/TwoBrokerMessageNotSentToRemoteWhenNoConsumerTest.*"
        });

        // Verifying that the specific test is excluded
        Assert.assertTrue(buildConfig.isTestExcluded("ChangeSessionDeliveryModeTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("DeadLetterTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("TwoMulticastDiscoveryBrokerTopicSendReceiveTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("TwoBrokerTopicSendReceiveUsingHttpTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("TopicClusterTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("MultiBrokersMultiClientsTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("MultiBrokersMultiClientsUsingTcpTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("ThreeBrokerQueueNetworkTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("ThreeBrokerTopicNetworkTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("ThreeBrokerTopicNetworkUsingTcpTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("TwoBrokerTopicSendReceiveUsingTcpTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("TwoBrokerQueueClientsReconnectTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("TwoBrokerMulticastQueueTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("PublishOnQueueConsumedMessageUsingActivemqXMLTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("PublishOnTopicConsumerMessageUsingActivemqXMLTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("ThreeBrokerQueueNetworkUsingTcpTest.java"));
        Assert.assertTrue(buildConfig.isTestExcluded("TwoBrokerMessageNotSentToRemoteWhenNoConsumerTest.java"));
    }
}

class BuildConfiguration {
    private String[] excludes;

    public boolean isTestExcluded(String testClassName) {
        for (String exclude : excludes) {
            if (testClassName.matches(exclude.replace("*", ".*"))) {
                return true;
            }
        }
        return false;
    }
}