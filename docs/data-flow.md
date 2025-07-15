# Data Flow Documentation

## Overview

The Train Times application follows a unidirectional data flow pattern where data flows from external sources through services, managers, and finally to the UI components. This architecture ensures predictable data updates and makes debugging easier.

## Application Data Flow Architecture

```mermaid
flowchart TD
    subgraph "External Data Sources"
        API1[Train API]
        API2[Weather API]
        API3[Astronomy API]
        FS[File System]
        Cache[Local Cache]
    end
    
    subgraph "Data Access Layer"
        TAS[Train API Service]
        WAS[Weather API Service]
        AAS[Astronomy API Service]
        CS[Configuration Service]
        CacheS[Cache Service]
    end
    
    subgraph "Business Logic Layer"
        RCS[Route Calculation Service]
        TDS[Train Data Service]
        TS[Timetable Service]
        TM[Train Manager]
        WM[Weather Manager]
        AM[Astronomy Manager]
    end
    
    subgraph "Presentation Layer"
        MW[Main Window]
        TLW[Train List Widget]
        WW[Weather Widget]
        AW[Astronomy Widget]
    end
    
    API1 --> TAS
    API2 --> WAS
    API3 --> AAS
    FS --> CS
    Cache --> CacheS
    
    TAS --> RCS
    TAS --> TDS
    WAS --> WM
    AAS --> AM
    CS --> TM
    CacheS --> TDS
    
    RCS --> TM
    TDS --> TM
    TS --> TM
    
    TM --> MW
    WM --> MW
    AM --> MW
    
    MW --> TLW
    MW --> WW
    MW --> AW
```

## Train Data Flow

### Complete Train Data Journey

```mermaid
sequenceDiagram
    participant U as User
    participant MW as Main Window
    participant TM as Train Manager
    participant RCS as Route Calculation Service
    participant TDS as Train Data Service
    participant TS as Timetable Service
    participant API as Train API
    participant Cache as Cache Service
    participant TLW as Train List Widget
    participant TIW as Train Item Widget
    
    U->>MW: Request train refresh
    MW->>TM: refresh_trains()
    
    TM->>RCS: calculate_route(from, to, via)
    RCS->>RCS: validate_stations()
    RCS->>RCS: find_optimal_path()
    RCS-->>TM: calculated_route
    
    TM->>TDS: generate_train_data(route, config)
    TDS->>Cache: check_cached_data(route_key)
    
    alt Cache Hit
        Cache-->>TDS: cached_train_data
    else Cache Miss
        TDS->>TS: get_timetable(stations, time_window)
        TS->>API: fetch_live_departures()
        API-->>TS: departure_data
        TS->>TS: process_timetable_data()
        TS-->>TDS: processed_timetable
        
        TDS->>TDS: generate_synthetic_trains()
        TDS->>TDS: apply_filters(config)
        TDS->>TDS: sort_by_departure()
        TDS->>Cache: store_data(route_key, train_data)
    end
    
    TDS-->>TM: filtered_train_data
    TM->>MW: trains_updated.emit(train_data)
    MW->>TLW: update_trains(train_data)
    
    TLW->>TLW: clear_existing_widgets()
    loop For each train
        TLW->>TIW: create/update TrainItemWidget(train)
        TIW->>TIW: update_display_elements()
        TIW-->>TLW: widget_ready
    end
    
    TLW-->>MW: display_updated
    MW-->>U: Updated train display
```

### Route Calculation Data Flow

```mermaid
flowchart TD
    A[Route Request] --> B[Station Validation]
    B --> C{Stations Valid?}
    C -->|No| D[Return Error]
    C -->|Yes| E[Load Station Database]
    
    E --> F[Find Direct Routes]
    F --> G{Direct Route Available?}
    G -->|Yes| H[Calculate Direct Path]
    G -->|No| I[Find Interchange Routes]
    
    I --> J[Calculate Via Routes]
    J --> K[Apply Route Preferences]
    K --> L{Avoid Walking?}
    L -->|Yes| M[Filter Walking Routes]
    L -->|No| N[Include All Routes]
    
    M --> O[Check Walking Distance]
    N --> P[Apply Max Changes Filter]
    O --> P
    P --> Q[Optimize Route Selection]
    
    H --> R[Validate Final Route]
    Q --> R
    R --> S{Route Valid?}
    S -->|No| T[Return Fallback Route]
    S -->|Yes| U[Return Optimal Route]
    
    D --> V[Log Error]
    T --> W[Cache Result]
    U --> W
    V --> X[End]
    W --> X
```

## Configuration Data Flow

### Configuration Loading and Updates

```mermaid
sequenceDiagram
    participant App as Application
    participant CM as Config Manager
    participant CS as Configuration Service
    participant FS as File System
    participant Val as Validator
    participant Obs as Observers
    
    App->>CM: initialize()
    CM->>CS: load_config()
    CS->>FS: read_config_file()
    
    alt Config File Exists
        FS-->>CS: config_json
        CS->>Val: validate_schema(config)
        Val-->>CS: validation_result
        
        alt Valid Config
            CS->>CS: parse_configuration()
            CS-->>CM: loaded_config
        else Invalid Config
            CS->>CS: create_default_config()
            CS->>FS: save_default_config()
            CS-->>CM: default_config
        end
    else No Config File
        CS->>CS: create_default_config()
        CS->>FS: save_default_config()
        CS-->>CM: default_config
    end
    
    CM-->>App: configuration_ready
    
    Note over App: Runtime config change
    App->>CM: update_config(changes)
    CM->>Val: validate_changes(changes)
    Val-->>CM: validation_result
    
    alt Valid Changes
        CM->>CS: save_config(updated_config)
        CS->>FS: write_config_file()
        CM->>Obs: notify_config_changed()
        Obs-->>App: config_updated
    else Invalid Changes
        CM-->>App: validation_error
    end
```

### Configuration Propagation

```mermaid
graph TB
    subgraph "Configuration Sources"
        CF[Config File]
        UD[User Dialogs]
        CL[Command Line]
        ENV[Environment]
    end
    
    subgraph "Configuration Manager"
        CM[Config Manager]
        Val[Validator]
        Mer[Merger]
    end
    
    subgraph "Configuration Consumers"
        TM[Train Manager]
        WM[Weather Manager]
        AM[Astronomy Manager]
        UI[UI Components]
        TH[Theme Manager]
    end
    
    CF --> CM
    UD --> CM
    CL --> CM
    ENV --> CM
    
    CM --> Val
    Val --> Mer
    Mer --> TM
    Mer --> WM
    Mer --> AM
    Mer --> UI
    Mer --> TH
    
    TM --> |Config Changes| CM
    WM --> |Config Changes| CM
    AM --> |Config Changes| CM
    UI --> |Config Changes| CM
```

## Weather Data Flow

### Weather Information Pipeline

```mermaid
flowchart LR
    subgraph "Weather Data Sources"
        WA[Weather API]
        GS[Geocoding Service]
        Cache[Weather Cache]
    end
    
    subgraph "Weather Processing"
        WM[Weather Manager]
        WAS[Weather API Service]
        WP[Weather Processor]
    end
    
    subgraph "Weather Display"
        WW[Weather Widget]
        WD[Weather Display]
        WI[Weather Icons]
    end
    
    WM --> |Location Query| GS
    GS --> |Coordinates| WAS
    WAS --> |API Request| WA
    WA --> |Weather Data| WAS
    WAS --> |Raw Data| WP
    WP --> |Processed Data| WM
    
    WM --> |Check Cache| Cache
    Cache --> |Cached Data| WM
    WM --> |Store Data| Cache
    
    WM --> |Weather Update| WW
    WW --> |Display Data| WD
    WW --> |Show Icons| WI
```

### Weather Update Cycle

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Fetching: Refresh Timer / Manual Refresh
    Fetching --> Processing: Data Received
    Fetching --> Error: API Error
    Processing --> Caching: Data Processed
    Caching --> Displaying: Data Cached
    Displaying --> Idle: Display Updated
    Error --> Retry: Retry Logic
    Error --> Fallback: Max Retries Reached
    Retry --> Fetching: Retry Attempt
    Fallback --> Displaying: Show Cached/Default
    Displaying --> [*]: Widget Destroyed
    Error --> [*]: Widget Destroyed
```

## Astronomy Data Flow

### Astronomy Information Pipeline

```mermaid
sequenceDiagram
    participant Timer as Refresh Timer
    participant AM as Astronomy Manager
    participant AAS as Astronomy API Service
    participant NASA as NASA API
    participant Proc as Data Processor
    participant Cache as Astronomy Cache
    participant AW as Astronomy Widget
    participant UI as UI Display
    
    Timer->>AM: refresh_trigger()
    AM->>Cache: check_cached_data()
    
    alt Cache Valid
        Cache-->>AM: cached_astronomy_data
    else Cache Expired/Missing
        AM->>AAS: fetch_astronomy_data(lat, lon)
        AAS->>NASA: get_space_events()
        NASA-->>AAS: space_events_json
        AAS->>AAS: parse_api_response()
        AAS-->>AM: parsed_astronomy_data
        
        AM->>Proc: process_astronomy_data(raw_data)
        Proc->>Proc: filter_relevant_events()
        Proc->>Proc: format_display_data()
        Proc-->>AM: processed_data
        
        AM->>Cache: store_data(processed_data)
    end
    
    AM->>AW: astronomy_updated.emit(data)
    AW->>AW: update_display_elements()
    AW->>UI: refresh_astronomy_display()
    UI-->>Timer: display_updated
```

## Error Data Flow

### Error Handling and Recovery

```mermaid
flowchart TD
    A[Error Occurs] --> B[Error Detection]
    B --> C[Error Classification]
    C --> D{Error Type}
    
    D -->|Network Error| E[Network Error Handler]
    D -->|API Error| F[API Error Handler]
    D -->|Data Error| G[Data Error Handler]
    D -->|UI Error| H[UI Error Handler]
    
    E --> I[Check Network Status]
    F --> J[Check API Status]
    G --> K[Validate Data]
    H --> L[Reset UI State]
    
    I --> M{Network Available?}
    J --> N{API Accessible?}
    K --> O{Data Recoverable?}
    L --> P[UI Reset Complete]
    
    M -->|Yes| Q[Retry Operation]
    M -->|No| R[Show Offline Mode]
    N -->|Yes| Q
    N -->|No| S[Use Cached Data]
    O -->|Yes| T[Repair Data]
    O -->|No| U[Use Default Data]
    
    Q --> V[Operation Retry]
    R --> W[Offline Display]
    S --> X[Cached Display]
    T --> Y[Repaired Display]
    U --> Z[Default Display]
    P --> AA[Normal Display]
    
    V --> BB{Retry Successful?}
    BB -->|Yes| CC[Normal Operation]
    BB -->|No| DD[Escalate Error]
    
    W --> EE[Log Error]
    X --> EE
    Y --> EE
    Z --> EE
    AA --> EE
    CC --> EE
    DD --> EE
    
    EE --> FF[Error Logged]
    FF --> GG[User Notification]
    GG --> HH[Continue Operation]
```

## Cache Data Flow

### Multi-Level Caching Strategy

```mermaid
graph TB
    subgraph "Data Request Flow"
        DR[Data Request] --> L1[Level 1: Memory Cache]
        L1 --> |Cache Miss| L2[Level 2: Disk Cache]
        L2 --> |Cache Miss| L3[Level 3: External API]
    end
    
    subgraph "Cache Population"
        L3 --> |Store| L2
        L2 --> |Store| L1
        L1 --> |Return| Response[Data Response]
    end
    
    subgraph "Cache Invalidation"
        TTL[TTL Expiry] --> INV[Invalidate Cache]
        UC[User Clear] --> INV
        UPD[Data Update] --> INV
        INV --> L1
        INV --> L2
    end
    
    subgraph "Cache Metrics"
        L1 --> |Hit/Miss| M1[Memory Metrics]
        L2 --> |Hit/Miss| M2[Disk Metrics]
        L3 --> |Success/Fail| M3[API Metrics]
    end
```

### Cache Lifecycle Management

```mermaid
stateDiagram-v2
    [*] --> Empty
    Empty --> Populating: First Request
    Populating --> Fresh: Data Loaded
    Fresh --> Stale: TTL Expired
    Fresh --> Invalid: Data Changed
    Stale --> Refreshing: Background Refresh
    Invalid --> Populating: Force Refresh
    Refreshing --> Fresh: Refresh Complete
    Refreshing --> Stale: Refresh Failed
    Fresh --> [*]: Cache Cleared
    Stale --> [*]: Cache Cleared
    Invalid --> [*]: Cache Cleared
```

## Performance Data Flow

### Data Flow Optimization

```mermaid
graph LR
    subgraph "Optimization Strategies"
        A[Request Batching]
        B[Data Compression]
        C[Lazy Loading]
        D[Prefetching]
        E[Connection Pooling]
    end
    
    subgraph "Implementation"
        A1[Batch API calls]
        B1[Compress responses]
        C1[Load on demand]
        D1[Predict next requests]
        E1[Reuse connections]
    end
    
    subgraph "Performance Benefits"
        R1[Reduced API calls]
        R2[Lower bandwidth]
        R3[Faster startup]
        R4[Better responsiveness]
        R5[Lower latency]
    end
    
    A --> A1 --> R1
    B --> B1 --> R2
    C --> C1 --> R3
    D --> D1 --> R4
    E --> E1 --> R5
```

## Data Validation Flow

### Input Validation Pipeline

```mermaid
flowchart TD
    A[Data Input] --> B[Schema Validation]
    B --> C{Schema Valid?}
    C -->|No| D[Schema Error]
    C -->|Yes| E[Type Validation]
    
    E --> F{Types Valid?}
    F -->|No| G[Type Error]
    F -->|Yes| H[Range Validation]
    
    H --> I{Values in Range?}
    I -->|No| J[Range Error]
    I -->|Yes| K[Business Logic Validation]
    
    K --> L{Business Rules Valid?}
    L -->|No| M[Business Error]
    L -->|Yes| N[Data Sanitization]
    
    N --> O[Sanitized Data]
    O --> P[Data Processing]
    
    D --> Q[Error Handler]
    G --> Q
    J --> Q
    M --> Q
    
    Q --> R[Log Error]
    R --> S[Return Error Response]
    
    P --> T[Processed Data]
    T --> U[Success Response]
```

## Future Data Flow Enhancements

### Planned Improvements

1. **Event Sourcing**: Complete audit trail of data changes
2. **Real-time Updates**: WebSocket-based live data updates
3. **Data Streaming**: Continuous data flow for large datasets
4. **Distributed Caching**: Shared cache across multiple instances
5. **Data Analytics**: Usage patterns and performance metrics

### Extension Points

- **Custom Data Sources**: Plugin architecture for new data providers
- **Data Transformation**: Configurable data processing pipelines
- **Advanced Caching**: Intelligent cache warming and eviction
- **Data Synchronization**: Multi-device data consistency
- **Offline Support**: Comprehensive offline data management

---

*This data flow documentation is maintained alongside the application codebase and updated with each data-related change.*