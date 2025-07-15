# Design Patterns Documentation

## Overview

The Train Times application implements several well-established design patterns to achieve maintainable, extensible, and testable code. This document details the patterns used, their implementation, and the benefits they provide.

## Implemented Design Patterns

### Creational Patterns

#### 1. Factory Pattern

Used for creating widgets and service instances with consistent configuration.

```mermaid
classDiagram
    class WidgetFactory {
        <<abstract>>
        +create_widget(type, config) Widget
        +configure_widget(widget, config)
        +register_widget_type(type, class)
    }
    
    class TrainWidgetFactory {
        -widget_registry: dict
        +create_train_item_widget(data) TrainItemWidget
        +create_train_list_widget(config) TrainListWidget
        +create_empty_state_widget() EmptyStateWidget
        +create_route_dialog(data) RouteDisplayDialog
    }
    
    class ServiceFactory {
        -service_registry: dict
        +create_service(type, config) Service
        +create_train_service(config) TrainDataService
        +create_route_service(config) RouteCalculationService
        +create_config_service() ConfigurationService
    }
    
    WidgetFactory <|-- TrainWidgetFactory
    WidgetFactory <|-- ServiceFactory
```

**Implementation Example:**
```python
class TrainWidgetFactory:
    @staticmethod
    def create_train_item_widget(train_data: TrainData, theme: str) -> TrainItemWidget:
        widget = TrainItemWidget(train_data)
        widget.apply_theme(theme)
        widget.setup_ui()
        return widget
    
    @staticmethod
    def create_train_list_widget(max_trains: int = 50) -> TrainListWidget:
        widget = TrainListWidget(max_trains)
        widget.setup_scroll_area()
        widget.setup_empty_state()
        return widget
```

#### 2. Singleton Pattern

Used for configuration management and theme management to ensure single instances.

```mermaid
classDiagram
    class ConfigManager {
        -_instance: ConfigManager
        -_config: Configuration
        
        +get_instance() ConfigManager
        +load_config() Configuration
        +save_config(config)
        +__new__(cls) ConfigManager
    }
    
    class ThemeManager {
        -_instance: ThemeManager
        -_current_theme: str
        -_theme_colors: dict
        
        +get_instance() ThemeManager
        +set_theme(theme_name)
        +get_theme_colors() dict
        +__new__(cls) ThemeManager
    }
```

**Implementation Example:**
```python
class ConfigManager:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_config(self) -> Configuration:
        if self._config is None:
            self._config = self._load_from_file()
        return self._config
```

### Structural Patterns

#### 3. Adapter Pattern

Used to integrate external APIs with consistent internal interfaces.

```mermaid
classDiagram
    class WeatherDataInterface {
        <<interface>>
        +get_current_weather(location) WeatherData
        +get_forecast(location, days) List[WeatherData]
    }
    
    class ExternalWeatherAPI {
        +fetch_weather(lat, lon) dict
        +fetch_forecast(lat, lon, days) dict
    }
    
    class WeatherAPIAdapter {
        -external_api: ExternalWeatherAPI
        +get_current_weather(location) WeatherData
        +get_forecast(location, days) List[WeatherData]
        -convert_to_weather_data(raw_data) WeatherData
    }
    
    WeatherDataInterface <|.. WeatherAPIAdapter
    WeatherAPIAdapter --> ExternalWeatherAPI
```

**Implementation Example:**
```python
class WeatherAPIAdapter(WeatherDataInterface):
    def __init__(self, external_api: ExternalWeatherAPI):
        self.external_api = external_api
    
    def get_current_weather(self, location: str) -> WeatherData:
        raw_data = self.external_api.fetch_weather(location)
        return self._convert_to_weather_data(raw_data)
    
    def _convert_to_weather_data(self, raw_data: dict) -> WeatherData:
        return WeatherData(
            temperature=raw_data['temp'],
            condition=raw_data['weather'][0]['main'],
            humidity=raw_data['humidity']
        )
```

#### 4. Facade Pattern

Used to provide simplified interfaces to complex subsystems.

```mermaid
classDiagram
    class TrainSystemFacade {
        -route_service: RouteCalculationService
        -data_service: TrainDataService
        -timetable_service: TimetableService
        -config_service: ConfigurationService
        
        +get_trains(from, to, via) List[TrainData]
        +calculate_journey(route) JourneyPlan
        +refresh_data()
        +update_preferences(prefs)
    }
    
    class RouteCalculationService {
        +calculate_route(from, to, via) Route
        +validate_stations(stations) bool
    }
    
    class TrainDataService {
        +generate_train_data(route) List[TrainData]
        +filter_trains(trains, criteria) List[TrainData]
    }
    
    class TimetableService {
        +get_timetable(station) Timetable
        +get_service_patterns() List[ServicePattern]
    }
    
    TrainSystemFacade --> RouteCalculationService
    TrainSystemFacade --> TrainDataService
    TrainSystemFacade --> TimetableService
```

#### 5. Decorator Pattern

Used for theme application and widget enhancement.

```mermaid
classDiagram
    class Widget {
        <<interface>>
        +render()
        +handle_event(event)
    }
    
    class BaseWidget {
        +render()
        +handle_event(event)
    }
    
    class WidgetDecorator {
        <<abstract>>
        -widget: Widget
        +render()
        +handle_event(event)
    }
    
    class ThemeDecorator {
        -theme_colors: dict
        +render()
        +apply_theme_colors()
    }
    
    class AnimationDecorator {
        -animation: QPropertyAnimation
        +render()
        +animate_transition()
    }
    
    Widget <|.. BaseWidget
    Widget <|.. WidgetDecorator
    WidgetDecorator <|-- ThemeDecorator
    WidgetDecorator <|-- AnimationDecorator
    WidgetDecorator --> Widget
```

### Behavioral Patterns

#### 6. Observer Pattern

Implemented through Qt's signal-slot mechanism for loose coupling.

```mermaid
sequenceDiagram
    participant TM as Train Manager (Subject)
    participant MW as Main Window (Observer)
    participant TLW as Train List Widget (Observer)
    participant WW as Weather Widget (Observer)
    
    Note over TM: Data updated
    TM->>MW: trains_updated.emit(data)
    TM->>TLW: trains_updated.emit(data)
    
    MW->>MW: handle_trains_updated(data)
    TLW->>TLW: update_display(data)
    
    Note over TM: Configuration changed
    TM->>MW: config_changed.emit(config)
    TM->>WW: config_changed.emit(config)
    
    MW->>MW: handle_config_change(config)
    WW->>WW: update_config(config)
```

**Implementation Example:**
```python
class TrainManager(QObject):
    trains_updated = Signal(list)
    config_changed = Signal(object)
    error_occurred = Signal(str)
    
    def refresh_trains(self):
        try:
            trains = self._fetch_train_data()
            self.trains_updated.emit(trains)
        except Exception as e:
            self.error_occurred.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.train_manager = TrainManager()
        self.train_manager.trains_updated.connect(self.update_train_display)
        self.train_manager.error_occurred.connect(self.show_error)
```

#### 7. Strategy Pattern

Used for different route calculation algorithms and theme strategies.

```mermaid
classDiagram
    class RouteCalculationStrategy {
        <<interface>>
        +calculate_route(from, to, preferences) Route
        +validate_route(route) bool
    }
    
    class DirectRouteStrategy {
        +calculate_route(from, to, preferences) Route
        +find_direct_connections(from, to) List[Connection]
    }
    
    class InterchangeRouteStrategy {
        +calculate_route(from, to, preferences) Route
        +find_interchange_points(from, to) List[Station]
        +optimize_interchanges(route) Route
    }
    
    class WalkingRouteStrategy {
        +calculate_route(from, to, preferences) Route
        +calculate_walking_distance(from, to) float
        +is_walking_acceptable(distance, prefs) bool
    }
    
    class RouteCalculationService {
        -strategy: RouteCalculationStrategy
        +set_strategy(strategy)
        +calculate_route(from, to, preferences) Route
    }
    
    RouteCalculationStrategy <|.. DirectRouteStrategy
    RouteCalculationStrategy <|.. InterchangeRouteStrategy
    RouteCalculationStrategy <|.. WalkingRouteStrategy
    RouteCalculationService --> RouteCalculationStrategy
```

**Implementation Example:**
```python
class RouteCalculationService:
    def __init__(self):
        self.strategy = DirectRouteStrategy()
    
    def set_strategy(self, strategy: RouteCalculationStrategy):
        self.strategy = strategy
    
    def calculate_route(self, from_station: str, to_station: str, 
                       preferences: RoutePreferences) -> Route:
        return self.strategy.calculate_route(from_station, to_station, preferences)

# Usage
service = RouteCalculationService()
if preferences.avoid_walking:
    service.set_strategy(DirectRouteStrategy())
elif preferences.minimize_changes:
    service.set_strategy(InterchangeRouteStrategy())
else:
    service.set_strategy(WalkingRouteStrategy())
```

#### 8. Command Pattern

Used for user actions and undo/redo functionality.

```mermaid
classDiagram
    class Command {
        <<interface>>
        +execute()
        +undo()
        +can_undo() bool
    }
    
    class RefreshTrainsCommand {
        -train_manager: TrainManager
        -previous_data: List[TrainData]
        +execute()
        +undo()
    }
    
    class ChangeThemeCommand {
        -theme_manager: ThemeManager
        -previous_theme: str
        -new_theme: str
        +execute()
        +undo()
    }
    
    class UpdateConfigCommand {
        -config_manager: ConfigManager
        -previous_config: Configuration
        -new_config: Configuration
        +execute()
        +undo()
    }
    
    class CommandInvoker {
        -command_history: List[Command]
        -current_index: int
        +execute_command(command)
        +undo_last_command()
        +redo_command()
        +can_undo() bool
        +can_redo() bool
    }
    
    Command <|.. RefreshTrainsCommand
    Command <|.. ChangeThemeCommand
    Command <|.. UpdateConfigCommand
    CommandInvoker --> Command
```

#### 9. State Pattern

Used for managing widget states and application lifecycle.

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> Loading: Start Data Fetch
    Loading --> Ready: Data Loaded
    Loading --> Error: Load Failed
    Ready --> Refreshing: Manual Refresh
    Ready --> Updating: Config Changed
    Refreshing --> Ready: Refresh Complete
    Refreshing --> Error: Refresh Failed
    Updating --> Ready: Update Complete
    Error --> Loading: Retry
    Error --> Ready: Use Cached Data
    Ready --> [*]: Application Exit
    Error --> [*]: Application Exit
```

```mermaid
classDiagram
    class ApplicationState {
        <<abstract>>
        +handle_refresh()
        +handle_config_change()
        +handle_error()
        +enter_state(context)
        +exit_state(context)
    }
    
    class InitializingState {
        +handle_refresh()
        +handle_config_change()
        +enter_state(context)
    }
    
    class LoadingState {
        +handle_refresh()
        +handle_error()
        +enter_state(context)
    }
    
    class ReadyState {
        +handle_refresh()
        +handle_config_change()
        +enter_state(context)
    }
    
    class ErrorState {
        +handle_refresh()
        +handle_error()
        +enter_state(context)
    }
    
    class ApplicationContext {
        -current_state: ApplicationState
        +set_state(state)
        +refresh()
        +change_config()
        +handle_error()
    }
    
    ApplicationState <|-- InitializingState
    ApplicationState <|-- LoadingState
    ApplicationState <|-- ReadyState
    ApplicationState <|-- ErrorState
    ApplicationContext --> ApplicationState
```

### Custom Patterns

#### 10. Manager Pattern

A custom pattern for organizing UI responsibilities.

```mermaid
classDiagram
    class UIManager {
        <<abstract>>
        #main_window: MainWindow
        +initialize()
        +cleanup()
        +handle_event(event)
    }
    
    class UILayoutManager {
        -widgets: dict
        -layout: QLayout
        +setup_ui()
        +update_layout()
        +get_widgets() dict
    }
    
    class WidgetLifecycleManager {
        -widget_states: dict
        +setup_weather_system()
        +setup_astronomy_system()
        +save_ui_state()
    }
    
    class EventHandlerManager {
        -event_handlers: dict
        +handle_close_event(event)
        +refresh_all_data()
        +setup_refresh_timer()
    }
    
    class SettingsDialogManager {
        -open_dialogs: dict
        +show_stations_settings_dialog()
        +show_astronomy_settings_dialog()
        +close_all_dialogs()
    }
    
    UIManager <|-- UILayoutManager
    UIManager <|-- WidgetLifecycleManager
    UIManager <|-- EventHandlerManager
    UIManager <|-- SettingsDialogManager
```

#### 11. Service Layer Pattern

Encapsulates business logic in focused service classes.

```mermaid
graph TB
    subgraph "Service Layer Pattern"
        subgraph "Presentation Layer"
            UI[UI Components]
            MW[Main Window]
        end
        
        subgraph "Application Layer"
            TM[Train Manager]
            WM[Weather Manager]
            AM[Astronomy Manager]
        end
        
        subgraph "Service Layer"
            RCS[Route Calculation Service]
            TDS[Train Data Service]
            CS[Configuration Service]
            TS[Timetable Service]
        end
        
        subgraph "Data Access Layer"
            API[API Services]
            Cache[Cache Services]
            FS[File System]
        end
    end
    
    UI --> MW
    MW --> TM
    MW --> WM
    MW --> AM
    
    TM --> RCS
    TM --> TDS
    TM --> CS
    TM --> TS
    
    RCS --> API
    TDS --> Cache
    CS --> FS
    TS --> API
```

## Pattern Interactions

### Pattern Collaboration Diagram

```mermaid
graph LR
    subgraph "Creational"
        F[Factory]
        S[Singleton]
    end
    
    subgraph "Structural"
        A[Adapter]
        D[Decorator]
        FA[Facade]
    end
    
    subgraph "Behavioral"
        O[Observer]
        ST[Strategy]
        C[Command]
        State[State]
    end
    
    subgraph "Custom"
        M[Manager]
        SL[Service Layer]
    end
    
    F --> |Creates| O
    S --> |Manages| ST
    A --> |Adapts| SL
    D --> |Enhances| M
    FA --> |Simplifies| SL
    O --> |Notifies| State
    ST --> |Implements| C
    C --> |Executes| M
    State --> |Controls| SL
    M --> |Coordinates| SL
```

## Pattern Benefits

### Maintainability Benefits

```mermaid
graph TD
    subgraph "Pattern Benefits"
        A[Separation of Concerns]
        B[Loose Coupling]
        C[High Cohesion]
        D[Code Reusability]
        E[Testability]
    end
    
    subgraph "Implementation Results"
        A1[Clear Responsibilities]
        B1[Independent Components]
        C1[Focused Classes]
        D1[Shared Components]
        E1[Mockable Dependencies]
    end
    
    subgraph "Development Benefits"
        R1[Easier Debugging]
        R2[Faster Development]
        R3[Better Code Quality]
        R4[Reduced Duplication]
        R5[Improved Testing]
    end
    
    A --> A1 --> R1
    B --> B1 --> R2
    C --> C1 --> R3
    D --> D1 --> R4
    E --> E1 --> R5
```

## Anti-Patterns Avoided

### Common Anti-Patterns and Solutions

```mermaid
graph LR
    subgraph "Anti-Patterns Avoided"
        AP1[God Object]
        AP2[Spaghetti Code]
        AP3[Tight Coupling]
        AP4[Code Duplication]
        AP5[Magic Numbers]
    end
    
    subgraph "Solutions Applied"
        S1[Manager Pattern]
        S2[Service Layer]
        S3[Dependency Injection]
        S4[Factory Pattern]
        S5[Configuration Pattern]
    end
    
    subgraph "Results"
        R1[Focused Classes]
        R2[Clear Structure]
        R3[Loose Coupling]
        R4[Code Reuse]
        R5[Maintainable Config]
    end
    
    AP1 --> S1 --> R1
    AP2 --> S2 --> R2
    AP3 --> S3 --> R3
    AP4 --> S4 --> R4
    AP5 --> S5 --> R5
```

## Pattern Testing Strategies

### Testing Patterns Implementation

```mermaid
classDiagram
    class PatternTestStrategy {
        <<abstract>>
        +setup_test_environment()
        +create_test_doubles()
        +verify_pattern_behavior()
        +cleanup_test_environment()
    }
    
    class FactoryPatternTest {
        +test_widget_creation()
        +test_service_creation()
        +test_configuration_injection()
    }
    
    class ObserverPatternTest {
        +test_signal_emission()
        +test_slot_connection()
        +test_event_propagation()
    }
    
    class StrategyPatternTest {
        +test_strategy_switching()
        +test_algorithm_execution()
        +test_context_behavior()
    }
    
    PatternTestStrategy <|-- FactoryPatternTest
    PatternTestStrategy <|-- ObserverPatternTest
    PatternTestStrategy <|-- StrategyPatternTest
```

## Performance Considerations

### Pattern Performance Impact

```mermaid
graph TB
    subgraph "Performance Considerations"
        subgraph "Positive Impact"
            P1[Factory: Object Pooling]
            P2[Observer: Lazy Updates]
            P3[Strategy: Algorithm Selection]
            P4[Facade: Reduced Complexity]
        end
        
        subgraph "Potential Overhead"
            O1[Decorator: Layer Overhead]
            O2[Command: Memory Usage]
            O3[State: Context Switching]
            O4[Adapter: Translation Cost]
        end
        
        subgraph "Mitigation Strategies"
            M1[Efficient Implementation]
            M2[Memory Management]
            M3[Caching Strategies]
            M4[Performance Monitoring]
        end
    end
    
    P1 --> M1
    P2 --> M3
    O1 --> M1
    O2 --> M2
    O3 --> M3
    O4 --> M4
```

## Future Pattern Enhancements

### Planned Pattern Improvements

1. **Event Sourcing Pattern**: Complete audit trail of state changes
2. **CQRS Pattern**: Separate read and write operations
3. **Circuit Breaker Pattern**: Fault tolerance for external services
4. **Bulkhead Pattern**: Isolation of critical resources
5. **Saga Pattern**: Distributed transaction management

### Extension Opportunities

- **Plugin Pattern**: Dynamic loading of functionality
- **Visitor Pattern**: Operations on complex object structures
- **Memento Pattern**: State snapshots and restoration
- **Chain of Responsibility**: Flexible request handling
- **Template Method**: Standardized algorithm frameworks

---

*This design patterns documentation is maintained alongside the codebase and updated when new patterns are introduced or existing patterns are modified.*