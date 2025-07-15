# Train Times Application - Architecture Overview

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Detailed Documentation](#detailed-documentation)
5. [Design Patterns](#design-patterns)
6. [Data Flow](#data-flow)
7. [Deployment Architecture](#deployment-architecture)

## System Overview

The Train Times application is a desktop application built with PySide6 (Qt for Python) that provides real-time train schedule information with integrated weather and astronomy data. The application follows a modular, object-oriented architecture based on SOLID principles and established design patterns.

### High-Level Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[Main Window]
        W[Widgets]
        D[Dialogs]
    end
    
    subgraph "Application Layer"
        M[UI Managers]
        H[Event Handlers]
        S[State Management]
    end
    
    subgraph "Business Layer"
        TM[Train Manager]
        WM[Weather Manager]
        AM[Astronomy Manager]
        CM[Config Manager]
    end
    
    subgraph "Service Layer"
        TS[Train Services]
        AS[API Services]
        CS[Cache Services]
    end
    
    subgraph "Data Layer"
        DB[Local Data]
        API[External APIs]
        CF[Config Files]
    end
    
    UI --> M
    W --> H
    D --> S
    M --> TM
    H --> WM
    S --> AM
    TM --> TS
    WM --> AS
    AM --> CS
    TS --> DB
    AS --> API
    CS --> CF
```

### Key Architectural Decisions

- **Layered Architecture**: Clear separation between presentation, application, business, service, and data layers
- **Service-Oriented Design**: Business logic encapsulated in focused service classes
- **Manager Pattern**: UI complexity managed through specialized manager classes
- **Observer Pattern**: Loose coupling through Qt's signal/slot mechanism
- **Dependency Injection**: Services receive dependencies through constructors

## Architecture Principles

### SOLID Principles Implementation

1. **Single Responsibility Principle (SRP)**
   - Each class has one reason to change
   - UI managers handle specific aspects of window functionality
   - Services focus on single business domains

2. **Open/Closed Principle (OCP)**
   - New features added through extension, not modification
   - Plugin-ready architecture for future enhancements

3. **Liskov Substitution Principle (LSP)**
   - Proper inheritance hierarchies
   - Interface-based design for interchangeable components

4. **Interface Segregation Principle (ISP)**
   - Focused interfaces for specific functionality
   - No forced dependencies on unused methods

5. **Dependency Inversion Principle (DIP)**
   - High-level modules depend on abstractions
   - Dependency injection throughout the application

### Design Quality Attributes

- **Maintainability**: Modular design with clear boundaries
- **Testability**: Isolated components with mockable dependencies
- **Scalability**: Service-oriented architecture supports growth
- **Reliability**: Error handling and graceful degradation
- **Performance**: Efficient resource management and caching

## Component Architecture

### Core Components Overview

```mermaid
graph LR
    subgraph "UI Components"
        MW[Main Window]
        UIM[UI Layout Manager]
        WLM[Widget Lifecycle Manager]
        EHM[Event Handler Manager]
        SDM[Settings Dialog Manager]
    end
    
    subgraph "Widget System"
        TLW[Train List Widget]
        TIW[Train Item Widget]
        CSB[Custom Scroll Bar]
        RDD[Route Display Dialog]
        ESW[Empty State Widget]
    end
    
    subgraph "Business Services"
        TM[Train Manager]
        RCS[Route Calculation Service]
        TDS[Train Data Service]
        CS[Configuration Service]
        TS[Timetable Service]
    end
    
    MW --> UIM
    MW --> WLM
    MW --> EHM
    MW --> SDM
    
    UIM --> TLW
    TLW --> TIW
    TLW --> CSB
    TIW --> RDD
    TLW --> ESW
    
    MW --> TM
    TM --> RCS
    TM --> TDS
    TM --> CS
    TM --> TS
```

## Detailed Documentation

### Component Documentation

- **[UI Architecture](ui-architecture.md)** - Detailed UI component structure and interactions
- **[Service Architecture](service-architecture.md)** - Business logic and service layer design
- **[Widget System](widget-system.md)** - Widget hierarchy and component relationships
- **[Data Flow](data-flow.md)** - Information flow through the application
- **[API Integration](api-integration.md)** - External service integration patterns

### Technical Documentation

- **[Design Patterns](design-patterns.md)** - Implemented patterns and their usage
- **[Configuration Management](configuration.md)** - Settings and configuration handling
- **[Error Handling](error-handling.md)** - Error management and recovery strategies
- **[Performance Optimization](performance.md)** - Performance considerations and optimizations
- **[Testing Strategy](testing-strategy.md)** - Testing approach and guidelines

## Design Patterns

### Primary Patterns Used

```mermaid
graph TD
    subgraph "Creational Patterns"
        F[Factory Pattern]
        S[Singleton Pattern]
    end
    
    subgraph "Structural Patterns"
        A[Adapter Pattern]
        D[Decorator Pattern]
        FA[Facade Pattern]
    end
    
    subgraph "Behavioral Patterns"
        O[Observer Pattern]
        ST[Strategy Pattern]
        C[Command Pattern]
        M[Manager Pattern]
    end
    
    F --> |Widget Creation| UI
    S --> |Config Management| Config
    A --> |API Integration| Services
    D --> |Theme System| Widgets
    FA --> |Service Layer| Business
    O --> |Event System| Events
    ST --> |Route Calculation| Algorithms
    C --> |User Actions| Commands
    M --> |UI Management| Managers
```

## Data Flow

### Application Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant MW as Main Window
    participant TM as Train Manager
    participant RCS as Route Calc Service
    participant API as External API
    participant W as Widgets
    
    U->>MW: Request train data
    MW->>TM: refresh_trains()
    TM->>RCS: calculate_route()
    RCS->>API: fetch_train_data()
    API-->>RCS: train_schedule
    RCS-->>TM: processed_routes
    TM-->>MW: train_data_updated
    MW->>W: update_display()
    W-->>U: Display trains
```

### Configuration Flow

```mermaid
flowchart TD
    A[Application Start] --> B[Load Config]
    B --> C{Config Exists?}
    C -->|Yes| D[Parse Config]
    C -->|No| E[Create Default]
    D --> F[Validate Settings]
    E --> F
    F --> G{Valid?}
    G -->|Yes| H[Initialize Services]
    G -->|No| I[Show Error]
    H --> J[Start Application]
    I --> K[Use Defaults]
    K --> H
```

## Deployment Architecture

### Application Structure

```mermaid
graph TB
    subgraph "Application Bundle"
        subgraph "Core Application"
            M[main.py]
            UI[UI Layer]
            BL[Business Layer]
            SL[Service Layer]
        end
        
        subgraph "Resources"
            C[Configuration]
            A[Assets]
            D[Data Files]
        end
        
        subgraph "Dependencies"
            P[PySide6]
            R[Requests]
            O[Other Libs]
        end
    end
    
    subgraph "External Services"
        TA[Train API]
        WA[Weather API]
        AA[Astronomy API]
    end
    
    subgraph "Local Storage"
        CF[Config Files]
        CA[Cache]
        L[Logs]
    end
    
    M --> UI
    UI --> BL
    BL --> SL
    SL --> TA
    SL --> WA
    SL --> AA
    C --> CF
    SL --> CA
    M --> L
```

### Runtime Environment

```mermaid
graph LR
    subgraph "User Environment"
        OS[Operating System]
        PY[Python Runtime]
        QT[Qt Framework]
    end
    
    subgraph "Application Process"
        MT[Main Thread]
        WT[Worker Threads]
        ET[Event Loop]
    end
    
    subgraph "System Resources"
        MEM[Memory]
        FS[File System]
        NET[Network]
    end
    
    OS --> PY
    PY --> QT
    QT --> MT
    MT --> WT
    MT --> ET
    ET --> MEM
    WT --> FS
    WT --> NET
```

## Architecture Benefits

### Achieved Goals

1. **Modularity**: Clear component boundaries and responsibilities
2. **Maintainability**: Easy to understand, modify, and extend
3. **Testability**: Isolated components with mockable dependencies
4. **Scalability**: Service-oriented design supports feature growth
5. **Reliability**: Robust error handling and graceful degradation
6. **Performance**: Efficient resource usage and responsive UI

### Quality Metrics

- **Code Coverage**: Comprehensive test coverage across all layers
- **Cyclomatic Complexity**: Low complexity through focused classes
- **Coupling**: Loose coupling through dependency injection
- **Cohesion**: High cohesion within individual components
- **Documentation**: Complete architectural and API documentation

## Future Enhancements

### Planned Improvements

1. **Plugin Architecture**: Support for third-party extensions
2. **Microservices**: Further service decomposition
3. **Event Sourcing**: Enhanced state management and debugging
4. **Containerization**: Docker-based deployment options
5. **Cloud Integration**: Cloud-based configuration and data sync

### Extension Points

- **New Data Sources**: Additional transport and weather providers
- **Custom Themes**: User-defined appearance customization
- **Advanced Analytics**: Journey planning and optimization
- **Mobile Companion**: Cross-platform synchronization
- **API Gateway**: Centralized external service management

---

*This architecture documentation is maintained alongside the codebase and updated with each significant architectural change.*