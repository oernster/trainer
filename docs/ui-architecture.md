# UI Architecture Documentation

## Overview

The Train Times application UI follows a manager-based architecture pattern where the main window delegates specific responsibilities to specialized manager classes. This approach ensures clean separation of concerns and improved maintainability.

## UI Component Hierarchy

```mermaid
graph TD
    subgraph "Main Application"
        MA[main.py]
        SS[Splash Screen]
    end
    
    subgraph "Main Window System"
        MW[Main Window]
        ULM[UI Layout Manager]
        WLM[Widget Lifecycle Manager]
        EHM[Event Handler Manager]
        SDM[Settings Dialog Manager]
    end
    
    subgraph "Widget Layer"
        TLW[Train List Widget]
        TIW[Train Item Widget]
        CSB[Custom Scroll Bar]
        WW[Weather Widget]
        AW[Astronomy Widget]
        RDD[Route Display Dialog]
        ESW[Empty State Widget]
    end
    
    subgraph "Dialog System"
        SSD[Stations Settings Dialog]
        ASD[Astronomy Settings Dialog]
        TD[Train Detail Dialog]
        AD[About Dialog]
    end
    
    MA --> SS
    SS --> MW
    MW --> ULM
    MW --> WLM
    MW --> EHM
    MW --> SDM
    
    ULM --> TLW
    ULM --> WW
    ULM --> AW
    TLW --> TIW
    TLW --> CSB
    TLW --> ESW
    
    SDM --> SSD
    SDM --> ASD
    EHM --> TD
    EHM --> AD
    TIW --> RDD
```

## Manager Architecture

### UI Layout Manager

The UI Layout Manager handles all aspects of window layout, widget positioning, and responsive design.

```mermaid
classDiagram
    class UILayoutManager {
        -main_window: MainWindow
        -ui_scale_factor: float
        -is_small_screen: bool
        -train_list_widget: TrainListWidget
        -weather_widget: WeatherWidget
        -astronomy_widget: AstronomyWidget
        
        +setup_ui()
        +setup_responsive_sizing()
        +setup_main_layout() QWidget
        +setup_window_sizing()
        +setup_application_icon()
        +setup_menu_bar()
        +setup_header_buttons()
        +update_window_size_for_widgets()
        +get_widgets() dict
        +handle_resize_event(event)
        +apply_theme_elements(theme_name)
    }
    
    class MainWindow {
        +ui_layout_manager: UILayoutManager
    }
    
    class TrainListWidget {
        +max_trains: int
        +update_trains(trains)
    }
    
    class WeatherWidget {
        +scale_factor: float
        +update_config(config)
    }
    
    class AstronomyWidget {
        +scale_factor: float
        +update_config(config)
    }
    
    UILayoutManager --> MainWindow
    UILayoutManager --> TrainListWidget
    UILayoutManager --> WeatherWidget
    UILayoutManager --> AstronomyWidget
```

### Widget Lifecycle Manager

Manages widget visibility, initialization, and cleanup throughout the application lifecycle.

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> WeatherSetup: Setup Weather System
    Initializing --> AstronomySetup: Setup Astronomy System
    
    WeatherSetup --> WeatherEnabled: Weather Config Found
    WeatherSetup --> WeatherDisabled: No Weather Config
    
    AstronomySetup --> AstronomyEnabled: Astronomy Config Found
    AstronomySetup --> AstronomyDisabled: No Astronomy Config
    
    WeatherEnabled --> WidgetVisible: Show Widget
    WeatherDisabled --> WidgetHidden: Hide Widget
    
    AstronomyEnabled --> WidgetVisible: Show Widget
    AstronomyDisabled --> WidgetHidden: Hide Widget
    
    WidgetVisible --> WidgetHidden: User Hides
    WidgetHidden --> WidgetVisible: User Shows
    
    WidgetVisible --> Cleanup: Application Exit
    WidgetHidden --> Cleanup: Application Exit
    Cleanup --> [*]
```

### Event Handler Manager

Coordinates all window events, user interactions, and system signals.

```mermaid
sequenceDiagram
    participant U as User
    participant EHM as Event Handler Manager
    participant MW as Main Window
    participant TM as Train Manager
    participant WM as Weather Manager
    participant AM as Astronomy Manager
    
    U->>EHM: User Action (Click/Key)
    EHM->>EHM: handle_keyboard_shortcuts()
    
    alt Refresh Request
        EHM->>TM: refresh_trains()
        EHM->>WM: refresh_weather()
        EHM->>AM: refresh_astronomy()
    else Settings Request
        EHM->>MW: show_settings_dialog()
    else Close Request
        EHM->>EHM: handle_close_event()
        EHM->>EHM: _cleanup_managers()
        EHM->>MW: Accept Close
    end
    
    TM-->>EHM: Data Updated
    WM-->>EHM: Weather Updated
    AM-->>EHM: Astronomy Updated
    EHM-->>MW: Update UI
```

### Settings Dialog Manager

Handles all configuration dialogs and settings management.

```mermaid
graph LR
    subgraph "Settings Dialog Manager"
        SDM[Settings Dialog Manager]
        
        subgraph "Dialog Types"
            SSD[Stations Settings]
            WSD[Weather Settings]
            ASD[Astronomy Settings]
            GSD[General Settings]
            AD[About Dialog]
        end
        
        subgraph "Dialog State"
            OD[Open Dialogs]
            DS[Dialog Signals]
            SC[Settings Changes]
        end
    end
    
    SDM --> SSD
    SDM --> WSD
    SDM --> ASD
    SDM --> GSD
    SDM --> AD
    
    SSD --> OD
    WSD --> DS
    ASD --> SC
    GSD --> OD
    AD --> DS
```

## Widget System Architecture

### Train Widget Hierarchy

```mermaid
classDiagram
    class BaseTrainWidget {
        <<abstract>>
        +theme_colors: dict
        +apply_theme(theme_name)
        +get_theme_colors() dict
    }
    
    class TrainListWidget {
        -scroll_area: QScrollArea
        -container_widget: QWidget
        -train_widgets: List[TrainItemWidget]
        -custom_scroll_bar: CustomScrollBar
        -empty_state_widget: EmptyStateWidget
        
        +update_trains(trains)
        +clear_trains()
        +add_train_widget(widget)
        +show_empty_state()
        +hide_empty_state()
    }
    
    class TrainItemWidget {
        -train_data: TrainData
        -departure_label: QLabel
        -destination_label: QLabel
        -platform_label: QLabel
        -status_label: QLabel
        
        +update_train_data(data)
        +set_selected(selected)
        +mousePressEvent(event)
    }
    
    class CustomScrollBar {
        -orientation: Qt.Orientation
        -smooth_scroll: bool
        
        +smooth_scroll_to(value)
        +paintEvent(event)
        +mousePressEvent(event)
    }
    
    class EmptyStateWidget {
        -message_label: QLabel
        -icon_label: QLabel
        
        +set_message(message)
        +set_icon(icon)
    }
    
    class RouteDisplayDialog {
        -train_data: TrainData
        -route_tree: QTreeWidget
        -close_button: QPushButton
        
        +populate_route_data()
        +show_calling_points()
    }
    
    BaseTrainWidget <|-- TrainListWidget
    BaseTrainWidget <|-- TrainItemWidget
    BaseTrainWidget <|-- CustomScrollBar
    BaseTrainWidget <|-- EmptyStateWidget
    BaseTrainWidget <|-- RouteDisplayDialog
    
    TrainListWidget --> TrainItemWidget
    TrainListWidget --> CustomScrollBar
    TrainListWidget --> EmptyStateWidget
    TrainItemWidget --> RouteDisplayDialog
```

### Widget Communication Flow

```mermaid
sequenceDiagram
    participant MW as Main Window
    participant TLW as Train List Widget
    participant TIW as Train Item Widget
    participant RDD as Route Display Dialog
    participant TM as Train Manager
    
    MW->>TLW: update_trains(train_data)
    TLW->>TLW: clear_existing_widgets()
    
    loop For each train
        TLW->>TIW: create TrainItemWidget(train)
        TIW->>TIW: setup_ui_elements()
        TIW->>TLW: widget_created
        TLW->>TLW: add_to_layout(widget)
    end
    
    TLW-->>MW: trains_displayed
    
    Note over TIW: User clicks train item
    TIW->>MW: train_selected(train_data)
    MW->>RDD: show_route_details(train_data)
    RDD->>TM: get_calling_points(train_id)
    TM-->>RDD: calling_points_data
    RDD->>RDD: populate_route_tree()
    RDD-->>MW: dialog_shown
```

## Theme System Architecture

### Theme Management Flow

```mermaid
flowchart TD
    A[Theme Manager] --> B{Current Theme}
    B -->|Dark| C[Dark Theme Colors]
    B -->|Light| D[Light Theme Colors]
    
    C --> E[Apply to Main Window]
    D --> E
    
    E --> F[Apply to Widgets]
    F --> G[Train List Widget]
    F --> H[Weather Widget]
    F --> I[Astronomy Widget]
    F --> J[Dialog Components]
    
    G --> K[Update Train Items]
    G --> L[Update Scroll Bar]
    
    H --> M[Update Weather Display]
    I --> N[Update Astronomy Display]
    J --> O[Update Dialog Styling]
    
    K --> P[Refresh UI]
    L --> P
    M --> P
    N --> P
    O --> P
```

### Theme Color Mapping

```mermaid
graph LR
    subgraph "Theme Colors"
        subgraph "Dark Theme"
            D1[background_primary: #1a1a1a]
            D2[background_secondary: #2d2d2d]
            D3[text_primary: #ffffff]
            D4[primary_accent: #1976d2]
            D5[border_primary: #404040]
        end
        
        subgraph "Light Theme"
            L1[background_primary: #ffffff]
            L2[background_secondary: #f5f5f5]
            L3[text_primary: #000000]
            L4[primary_accent: #1976d2]
            L5[border_primary: #cccccc]
        end
    end
    
    subgraph "Widget Applications"
        W1[Main Window Background]
        W2[Widget Backgrounds]
        W3[Text Colors]
        W4[Button Accents]
        W5[Border Colors]
    end
    
    D1 --> W1
    D2 --> W2
    D3 --> W3
    D4 --> W4
    D5 --> W5
    
    L1 --> W1
    L2 --> W2
    L3 --> W3
    L4 --> W4
    L5 --> W5
```

## Responsive Design System

### Screen Size Adaptation

```mermaid
graph TD
    A[Screen Detection] --> B{Screen Size}
    B -->|<= 1440x900| C[Small Screen Mode]
    B -->|> 1440x900| D[Large Screen Mode]
    
    C --> E[Scale Factor: 0.8]
    D --> F[Scale Factor: 1.0]
    
    E --> G[Adjust Widget Sizes]
    F --> G
    
    G --> H[Adjust Margins]
    G --> I[Adjust Spacing]
    G --> J[Adjust Font Sizes]
    
    H --> K[Update Layout]
    I --> K
    J --> K
    
    K --> L[Center Window]
    L --> M[Apply Constraints]
```

### Window Sizing Strategy

```mermaid
stateDiagram-v2
    [*] --> DetectWidgets
    DetectWidgets --> WeatherVisible: Weather Widget Shown
    DetectWidgets --> WeatherHidden: Weather Widget Hidden
    
    WeatherVisible --> BothVisible: Astronomy Widget Shown
    WeatherVisible --> WeatherOnly: Astronomy Widget Hidden
    
    WeatherHidden --> AstronomyOnly: Astronomy Widget Shown
    WeatherHidden --> TrainsOnly: Astronomy Widget Hidden
    
    BothVisible --> Size1200: Set Height 1200px
    WeatherOnly --> Size800: Set Height 800px
    AstronomyOnly --> Size900: Set Height 900px
    TrainsOnly --> Size600: Set Height 600px
    
    Size1200 --> ApplyScale
    Size800 --> ApplyScale
    Size900 --> ApplyScale
    Size600 --> ApplyScale
    
    ApplyScale --> CenterWindow
    CenterWindow --> [*]
```

## Error Handling in UI

### UI Error Management Flow

```mermaid
sequenceDiagram
    participant UI as UI Component
    participant EH as Error Handler
    participant MW as Main Window
    participant U as User
    
    UI->>UI: Operation Fails
    UI->>EH: handle_error(error)
    EH->>EH: log_error(error)
    EH->>EH: determine_severity()
    
    alt Critical Error
        EH->>MW: show_error_dialog()
        MW->>U: Display Error Dialog
    else Warning
        EH->>MW: show_status_message()
        MW->>U: Display Status Message
    else Info
        EH->>EH: log_only()
    end
    
    U->>MW: Acknowledge Error
    MW->>EH: error_acknowledged()
    EH->>UI: continue_operation()
```

## Performance Considerations

### UI Performance Optimization

```mermaid
graph LR
    subgraph "Performance Strategies"
        A[Lazy Loading]
        B[Widget Pooling]
        C[Efficient Updates]
        D[Memory Management]
    end
    
    subgraph "Implementation"
        A1[Load widgets on demand]
        B1[Reuse train item widgets]
        C1[Batch UI updates]
        D1[Cleanup on close]
    end
    
    subgraph "Benefits"
        R1[Faster startup]
        R2[Lower memory usage]
        R3[Smooth scrolling]
        R4[No memory leaks]
    end
    
    A --> A1 --> R1
    B --> B1 --> R2
    C --> C1 --> R3
    D --> D1 --> R4
```

## Future UI Enhancements

### Planned UI Improvements

1. **Advanced Theming**: Custom user themes and color schemes
2. **Accessibility**: Screen reader support and keyboard navigation
3. **Animations**: Smooth transitions and micro-interactions
4. **Customizable Layout**: User-configurable widget arrangements
5. **Mobile-Responsive**: Adaptive UI for different screen sizes

### Extension Points

- **Plugin UI**: Framework for third-party UI extensions
- **Custom Widgets**: API for creating custom display components
- **Theme Engine**: Advanced theming with CSS-like styling
- **Layout Engine**: Flexible layout system for different use cases

---

*This UI architecture documentation is maintained alongside the UI codebase and updated with each UI-related change.*