package com.example.test;

import java.util.List;
import java.util.ArrayList;
import java.util.concurrent.CompletableFuture;

/**
 * Sample Java class for testing JVM plugin.
 */
@Service
@Component("sampleService")
public class Sample<T extends Comparable<T>> implements Runnable {
    
    @Autowired
    private static final String CONSTANT = "Hello World";
    
    @Inject
    private List<T> items;
    
    private volatile boolean running = false;
    
    /**
     * Default constructor.
     */
    public Sample() {
        this.items = new ArrayList<>();
    }
    
    /**
     * Generic method with multiple type parameters.
     */
    public <K, V> Map<K, V> processData(K key, V value) throws Exception {
        Map<K, V> result = new HashMap<>();
        result.put(key, value);
        return result;
    }
    
    @Override
    public void run() {
        this.running = true;
        System.out.println("Running sample process...");
    }
    
    /**
     * Static factory method.
     */
    public static <T extends Comparable<T>> Sample<T> create() {
        return new Sample<T>();
    }
    
    @Deprecated
    private synchronized void legacyMethod() {
        // Legacy implementation
    }
    
    // Nested interface
    public interface SampleCallback<R> {
        R callback(String data);
        
        default void defaultMethod() {
            System.out.println("Default implementation");
        }
    }
    
    // Nested enum
    public enum Status {
        ACTIVE("active"),
        INACTIVE("inactive"),
        PENDING("pending");
        
        private final String value;
        
        Status(String value) {
            this.value = value;
        }
        
        public String getValue() {
            return value;
        }
    }
}

/**
 * Utility class with static methods.
 */
final class SampleUtils {
    
    private SampleUtils() {
        throw new UnsupportedOperationException("Utility class");
    }
    
    public static String formatString(String input) {
        return input != null ? input.trim().toLowerCase() : "";
    }
    
    public static <T> List<T> safeList(List<T> input) {
        return input != null ? new ArrayList<>(input) : new ArrayList<>();
    }
}