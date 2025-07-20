# Service Architecture Documentation

## Overview

The Train Times application implements a service-oriented architecture where business logic is encapsulated in focused service classes. This design promotes separation of concerns, testability, and maintainability while providing a clear API for the presentation layer.

## Service Layer Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        MW[Main Window]
        UI[UI Components]
    end
    
    subgraph "Coordination Layer"
        TM[Train Manager]
        WM[Weather Manager]
        AM[Astronomy Manager]
        CM[Config Manager]
    end
    
    subgraph "Service Layer"
        subgraph "Train Services"
            RCS[Route Calculation Service]
            TDS[Train Data Service]
            CS[Configuration Service]
            TS[Timetable Service]
        end
        
        subgraph "External Services"
            WAS[Weather API Service]
            HMPAS[Hybrid Moon Phase API Service]
        end
        
        subgraph "Static Data Services"
            TDS[Train Data Service]
            AES[Astronomy Event Service]
        end
        
        subgraph "Infrastructure Services"
            CAS[Cache Service]
            LS[Logging Service]
            ES[Error Service]
        end
    end
    
    subgraph "Data Layer"
        API[External APIs]
        FS[File System]
        MEM[Memory Cache]
    end
    
    MW --> TM
    UI --> WM
    UI --> AM
    UI --> CM
    
    TM --> RCS
    TM --> TDS
    TM --> CS
    TM --> TS
    
    WM --> WAS
    AM --> HMPAS
    AM --> AES
    TM --> TDS
    
    RCS --> CAS
    TDS --> LS
    CS --> ES
    
    WAS --> API
    HMPAS --> API
    TDS --> FS
    AES --> FS
    CAS --> MEM
    CS --> FS
```

## Core Service Classes

### Train Manager (Coordinator)

The Train Manager acts as a coordinator service that orchestrates the various train-related services.

```mermaid
classDiagram
    class TrainManager {
        -route_calculation_service: RouteCalculationService
        -train_data_service: TrainDataService
        -configuration_service: ConfigurationService
        -timetable_service: TimetableService
        -config: Configuration
        -current_route: Route
        
        +__init__(config_manager)
        +set_route(from_station, to_station, via_stations)
        +refresh_trains()
        +get_train_data() List[TrainData]
        +calculate_route(from_name, to_name) Route
        +update_config(new_config)
        +cleanup()
        
        # Signals
        +trains_updated: Signal
        +route_calculated: Signal
        +error_occurred: Signal
    }
    
    class RouteCalculationService {
        +calculate_route(from_name, to_name, config) Route
        +validate_stations(stations) bool
        +find_optimal_path(route_params) List[Station]
    }
    
    class TrainDataService {
        +generate_train_data(route, config) List[TrainData]
        +filter_trains(trains, criteria) List[TrainData]
        +sort_trains(trains, sort_key) List[TrainData]
    }
    
    class ConfigurationService {
        +load_configuration() Configuration
        +save_configuration(config)
        +validate_config(config) bool
        +get_default_config() Configuration
    }
    
    class TimetableService {
        +get_timetable(station, date) Timetable
        +calculate_journey_time(route) Duration
        +get_service_patterns() List[ServicePattern]
    }
    
    TrainManager --> RouteCalculationService
    TrainManager --> TrainDataService
    TrainManager --> ConfigurationService
    TrainManager --> TimetableService
```

### Route Calculation Service

Handles all route finding and validation logic.

```mermaid
flowchart TD
    A[Route Request] --> B[Validate Stations]
    B --> C{Stations Valid?}
    C -->|No| D[Return Error]
    C -->|Yes| E[Load Station Database]
    
    E --> F[Find Direct Routes]
    F --> G{Direct Route Found?}
    G -->|Yes| H[Calculate Direct Path]
    G -->|No| I[Find Interchange Routes]
    
    I --> J[Calculate Via Routes]
    J --> K[Apply Route Preferences]
    K --> L[Optimize Path]
    
    H --> M[Validate Route]
    L --> M
    M --> N{Route Valid?}
    N -->|No| O[Return Alternative]
    N -->|Yes| P[Return Optimal Route]
    
    D --> Q[Log Error]
    O --> Q
    P --> R[Cache Result]
    Q --> S[End]
    R --> S
```

### Train Data Service

Manages train data generation, filtering, and processing.

```mermaid
sequenceDiagram
    participant TM as Train Manager
    participant TDS as Train Data Service
    participant TS as Timetable Service
    participant API as External API
    participant Cache as Cache Service
    
    TM->>TDS: generate_train_data(route, config)
    TDS->>Cache: check_cached_data(route)
    
    alt Cache Hit
        Cache-->>TDS: cached_train_data
    else Cache Miss
        TDS->>TS: get_timetable(stations)
        TS->>API: fetch_live_data()
        API-->>TS: live_timetable
        TS-->>TDS: processed_timetable
        TDS->>TDS: generate_synthetic_data()
        TDS->>Cache: store_data(train_data)
    end
    
    TDS->>TDS: apply_filters(config)
    TDS->>TDS: sort_by_departure()
    TDS-->>TM: filtered_train_data
```

## Service Communication Patterns

### Service Dependencies

```mermaid
graph LR
    subgraph "Service Dependencies"
        subgraph "Level 1 - Core Services"
            CS[Configuration Service]
            LS[Logging Service]
            ES[Error Service]
        end
        
        subgraph "Level 2 - Data Services"
            CAS[Cache Service]
            TS[Timetable Service]
            GS[Geocoding Service]
        end
        
        subgraph "Level 3 - Business Services"
            RCS[Route Calculation Service]
            TDS[Train Data Service]
            WAS[Weather API Service]
            AAS[Astronomy API Service]
        end
        
        subgraph "Level 4 - Coordination Services"
            TM[Train Manager]
            WM[Weather Manager]
            AM[Astronomy Manager]
        end
    end
    
    CS --> CAS
    CS --> TS
    LS --> RCS
    ES --> TDS
    
    CAS --> RCS
    TS --> TDS
    GS --> WAS
    
    RCS --> TM
    TDS --> TM
    WAS --> WM
    AAS --> AM
```

### Service Lifecycle Management

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> ConfigLoading: Load Configuration
    ConfigLoading --> ServiceCreation: Create Services
    ServiceCreation --> DependencyInjection: Inject Dependencies
    DependencyInjection --> ServiceValidation: Validate Services
    ServiceValidation --> Ready: All Services Valid
    
    Ready --> Processing: Handle Requests
    Processing --> Ready: Request Completed
    
    Ready --> Updating: Configuration Changed
    Updating --> ServiceReconfiguration: Update Services
    ServiceReconfiguration --> Ready: Reconfiguration Complete
    
    Ready --> Cleanup: Application Shutdown
    Processing --> Cleanup: Force Shutdown
    Cleanup --> ServiceShutdown: Stop Services
    ServiceShutdown --> ResourceCleanup: Clean Resources
    ResourceCleanup --> [*]
```

## Configuration Service Architecture

### Configuration Management Flow

```mermaid
flowchart TD
    A[Application Start] --> B[Configuration Service Init]
    B --> C[Check Config File Exists]
    C --> D{File Exists?}
    
    D -->|Yes| E[Load Config File]
    D -->|No| F[Create Default Config]
    
    E --> G[Parse JSON]
    F --> H[Generate Default Values]
    
    G --> I{Valid JSON?}
    I -->|No| J[Show Error, Use Defaults]
    I -->|Yes| K[Validate Schema]
    
    K --> L{Schema Valid?}
    L -->|No| M[Migrate/Fix Schema]
    L -->|Yes| N[Configuration Ready]
    
    H --> N
    J --> N
    M --> N
    
    N --> O[Notify Services]
    O --> P[Start Application]
    
    P --> Q[Runtime Config Changes]
    Q --> R[Validate Changes]
    R --> S[Save to File]
    S --> T[Notify Observers]
    T --> Q
```

### Configuration Schema

```mermaid
erDiagram
    Configuration {
        string version
        object display
        object stations
        object weather
        object astronomy
        object ui
        int refresh_interval_minutes
        bool avoid_walking
        float max_walking_distance_km
        bool prefer_direct
        int max_changes
        int train_lookahead_hours
    }
    
    Display {
        string theme
        int time_window_hours
        bool show_platform
        bool show_operator
    }
    
    Stations {
        string from_name
        string to_name
        array via_stations
        string from_crs
        string to_crs
    }
    
    Weather {
        bool enabled
        string api_key
        string location
        int refresh_interval
    }
    
    Astronomy {
        bool enabled
        string api_key
        float latitude
        float longitude
        array enabled_link_categories
    }
    
    UI {
        bool weather_widget_visible
        bool astronomy_widget_visible
        tuple window_size_both_visible
        tuple window_size_weather_only
        tuple window_size_astronomy_only
        tuple window_size_trains_only
    }
    
    Configuration ||--|| Display : contains
    Configuration ||--|| Stations : contains
    Configuration ||--|| Weather : contains
    Configuration ||--|| Astronomy : contains
    Configuration ||--|| UI : contains
```

## External API Integration

### API Service Pattern

```mermaid
classDiagram
    class BaseAPIService {
        <<abstract>>
        -base_url: str
        -api_key: str
        -timeout: int
        -retry_count: int
        
        +make_request(endpoint, params) Response
        +handle_error(error) None
        +validate_response(response) bool
        +parse_response(response) dict
    }
    
    class WeatherAPIService {
        -weather_endpoints: dict
        
        +get_current_weather(location) WeatherData
        +get_forecast(location, days) List[WeatherData]
        +validate_location(location) bool
    }
    
    class HybridMoonPhaseAPIService {
        -moon_phase_endpoints: dict
        
        +get_moon_phase_data(date) MoonPhaseData
        +get_lunar_events(date_range) List[LunarEvent]
        +validate_date_range(start, end) bool
    }
    
    class StaticTrainDataService {
        -timetable_data: dict
        
        +generate_departures(route, time) List[Departure]
        +calculate_journey_time(route) Duration
        +validate_route(from_station, to_station) bool
    }
    
    BaseAPIService <|-- WeatherAPIService
    BaseAPIService <|-- HybridMoonPhaseAPIService
    StaticDataService <|-- StaticTrainDataService
```

### API Error Handling

```mermaid
sequenceDiagram
    participant S as Service
    participant API as API Service
    participant EH as Error Handler
    participant Cache as Cache
    participant UI as UI Component
    
    S->>API: make_request(endpoint, params)
    API->>API: send_http_request()
    
    alt Success Response
        API-->>S: parsed_data
        S->>Cache: store_data(data)
        S-->>UI: data_updated(data)
    else HTTP Error
        API->>EH: handle_http_error(status_code)
        EH->>Cache: get_cached_data()
        Cache-->>EH: cached_data
        EH-->>S: fallback_data
        S-->>UI: data_updated(fallback_data, is_cached=True)
    else Network Error
        API->>EH: handle_network_error(error)
        EH->>EH: log_error(error)
        EH-->>S: error_response
        S-->>UI: error_occurred(error_message)
    else Timeout Error
        API->>EH: handle_timeout_error()
        EH->>API: retry_request()
        API->>API: send_http_request()
        Note over API: Retry with exponential backoff
    end
```

## Caching Strategy

### Multi-Level Caching

```mermaid
graph TD
    subgraph "Cache Hierarchy"
        subgraph "Level 1 - Memory Cache"
            MC[Memory Cache]
            RT[Recent Trains]
            RR[Recent Routes]
        end
        
        subgraph "Level 2 - Disk Cache"
            DC[Disk Cache]
            SD[Station Data]
            TD[Timetable Data]
            WD[Weather Data]
        end
        
        subgraph "Level 3 - External APIs"
            TA[Train API]
            WA[Weather API]
            AA[Astronomy API]
        end
    end
    
    Request[Data Request] --> MC
    MC --> |Cache Miss| DC
    DC --> |Cache Miss| TA
    DC --> |Cache Miss| WA
    DC --> |Cache Miss| AA
    
    TA --> |Store| DC
    WA --> |Store| DC
    AA --> |Store| DC
    
    DC --> |Store| MC
    MC --> |Return| Response[Data Response]
```

### Cache Invalidation Strategy

```mermaid
flowchart LR
    A[Data Request] --> B{Cache Valid?}
    B -->|Yes| C[Return Cached Data]
    B -->|No| D[Check TTL]
    
    D --> E{TTL Expired?}
    E -->|No| F[Extend TTL]
    E -->|Yes| G[Invalidate Cache]
    
    F --> C
    G --> H[Fetch Fresh Data]
    H --> I[Update Cache]
    I --> J[Return Fresh Data]
    
    C --> K[Log Cache Hit]
    J --> L[Log Cache Miss]
    
    K --> M[End]
    L --> M
```

## Service Testing Strategy

### Service Test Architecture

```mermaid
graph TB
    subgraph "Test Types"
        UT[Unit Tests]
        IT[Integration Tests]
        CT[Contract Tests]
        PT[Performance Tests]
    end
    
    subgraph "Test Doubles"
        M[Mocks]
        S[Stubs]
        F[Fakes]
        SP[Spies]
    end
    
    subgraph "Test Infrastructure"
        TF[Test Fixtures]
        TD[Test Data]
        TH[Test Helpers]
        TC[Test Configuration]
    end
    
    UT --> M
    IT --> S
    CT --> F
    PT --> SP
    
    M --> TF
    S --> TD
    F --> TH
    SP --> TC
```

### Service Mock Strategy

```mermaid
sequenceDiagram
    participant Test as Test Case
    participant Mock as Mock Service
    participant SUT as Service Under Test
    participant Verify as Verification
    
    Test->>Mock: setup_mock_behavior()
    Test->>SUT: inject_dependency(Mock)
    Test->>SUT: call_method_under_test()
    
    SUT->>Mock: dependency_call()
    Mock-->>SUT: mocked_response
    SUT-->>Test: method_result
    
    Test->>Verify: verify_interactions()
    Verify->>Mock: get_call_history()
    Mock-->>Verify: call_details
    Verify-->>Test: verification_result
    
    Test->>Test: assert_expected_behavior()
```

## Performance Optimization

### Service Performance Patterns

```mermaid
graph LR
    subgraph "Performance Strategies"
        A[Lazy Loading]
        B[Connection Pooling]
        C[Request Batching]
        D[Response Caching]
        E[Async Processing]
    end
    
    subgraph "Implementation"
        A1[Load services on demand]
        B1[Reuse HTTP connections]
        C1[Batch API requests]
        D1[Cache frequent responses]
        E1[Non-blocking operations]
    end
    
    subgraph "Benefits"
        R1[Faster startup]
        R2[Lower latency]
        R3[Reduced API calls]
        R4[Better responsiveness]
        R5[Improved throughput]
    end
    
    A --> A1 --> R1
    B --> B1 --> R2
    C --> C1 --> R3
    D --> D1 --> R4
    E --> E1 --> R5
```

## Future Service Enhancements

### Planned Service Improvements

1. **Microservices Architecture**: Further decomposition into independent services
2. **Event-Driven Architecture**: Asynchronous event processing
3. **Service Mesh**: Advanced service-to-service communication
4. **Circuit Breaker Pattern**: Improved fault tolerance
5. **Distributed Caching**: Shared cache across service instances

### Extension Points

- **Plugin Services**: Framework for third-party service extensions
- **Service Registry**: Dynamic service discovery and registration
- **API Gateway**: Centralized API management and routing
- **Service Monitoring**: Health checks and performance metrics
- **Configuration Service**: Centralized configuration management

---

*This service architecture documentation is maintained alongside the service codebase and updated with each service-related change.*