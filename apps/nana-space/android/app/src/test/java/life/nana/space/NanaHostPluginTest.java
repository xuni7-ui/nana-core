package life.nana.space;
import org.junit.Test;
import static org.junit.Assert.*;
public class NanaHostPluginTest {
    @Test public void httpsOriginIsFixedAndCredentialFree() throws Exception {
        assertEquals("https://space.test:8443",NanaHostPlugin.origin("https://space.test:8443/"));
        for(String value:new String[]{"http://space.test","file:///tmp/x","https://user:pass@space.test","https://space.test/v1","https://space.test/#x","https://space.test/?token=x","https://space.test\\@evil.test","https://space.test:0"}) {
            try {NanaHostPlugin.origin(value);fail("unsafe origin accepted");}
            catch(Exception expected){assertEquals("HTTPS_ORIGIN_REQUIRED",expected.getMessage());}
        }
    }
    @Test public void sessionCacheIsBoundToHostDeviceSubjectAndLineage() throws Exception {
        String device="a".repeat(32),lineage="b".repeat(64);
        String initial=NanaHostPlugin.sessionBinding("https://space.test",device,"subject",lineage);
        assertNotEquals(initial,NanaHostPlugin.sessionBinding("https://other.test",device,"subject",lineage));
        assertNotEquals(initial,NanaHostPlugin.sessionBinding("https://space.test","c".repeat(32),"subject",lineage));
        assertNotEquals(initial,NanaHostPlugin.sessionBinding("https://space.test",device,"another",lineage));
        assertNotEquals(initial,NanaHostPlugin.sessionBinding("https://space.test",device,"subject","d".repeat(64)));
    }
}
