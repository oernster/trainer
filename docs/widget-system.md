# Widget System Documentation

## Overview

The Train Times application widget system is built on a modular, object-oriented architecture that promotes reusability, maintainability, and consistent theming. Each widget has a specific responsibility and can be used independently or as part of larger composite widgets.

## Widget Hierarchy

```mermaid
classDiagram
    class QWidget {
        <<Qt Framework>>
        +show()
        +hide()
        +setVisible(bool)
        +paintEvent(event)
        +mousePressEvent(event)
    }
    
    class BaseTrainWidget {
        <<abstract>>
        #theme_colors: dict
        #scale_factor: float
        
        +apply_theme(theme_name)*
        +get_theme_colors() dict*
        +update_theme(theme_colors)
        +setup_ui()*
    }
    
    class TrainListWidget {
        -scroll_area: QScrollArea
        -container_widget: QWidget
        -layout: QVBoxLayout
        -train_widgets: List[TrainItemWidget]
        -custom_scroll_bar: CustomScrollBar
        -empty_state_widget: EmptyStateWidget
        -max_trains: int
        
        +update_trains(trains: List[TrainData])
        +clear_trains()
        +add_train_widget(widget: TrainItemWidget)
        +remove_train_widget(widget: TrainItemWidget)
        +show_empty_state()
        +hide_empty_state()
        +get_selected_train() TrainData
        
        # Signals
        +train_selected: Signal
        +route_selected: Signal
    }
    
    class TrainItemWidget {
        -train_data: TrainData
        -departure_time_label: QLabel
        -destination_label: QLabel
        -platform_label: QLabel
        -status_label: QLabel
        -operator_label: QLabel
        -duration_label: QLabel
        -changes_label: QLabel
        -is_selected: bool
        
        +update_train_data(data: TrainData)
        +set_selected(selected: bool)
        +get_train_data() TrainData
        +format_time(time: datetime) str
        +format_duration(minutes: int) str
        
        # Events
        +mousePressEvent(event)
        +mouseDoubleClickEvent(event)
        +paintEvent(event)
    }
    
    class CustomScrollBar {
        -orientation: Qt.Orientation
        -smooth_scroll_enabled: bool
        -scroll_animation: QPropertyAnimation
        
        +smooth_scroll_to(value: int)
        +set_smooth_scroll_enabled(enabled: bool)
        +get_scroll_position() int
        
        # Events
        +paintEvent(event)
        +mousePressEvent(event)
        +mouseMoveEvent(event)
        +wheelEvent(event)
    }
    
    class EmptyStateWidget {
        -message_label: QLabel
        -icon_label: QLabel
        -action_button: QPushButton
        
        +set_message(message: str)
        +set_icon(icon: QIcon)
        +set_action_button(text: str, callback)
        +show_loading_state()
        +show_error_state(error: str)
        +show_empty_state()
    }
    
    class RouteDisplayDialog {
        -train_data: TrainData
        -route_tree: QTreeWidget
        -close_button: QPushButton
        -refresh_button: QPushButton
        -train_manager: TrainManager
        
        +populate_route_data()
        +show_calling_points()
        +refresh_route_data()
        +format_calling_point(station: Station) str
        
        # Events
        +closeEvent(event)
        +keyPressEvent(event)
    }
    
    QWidget <|-- BaseTrainWidget
    BaseTrainWidget <|-- TrainListWidget
    BaseTrainWidget <|-- TrainItemWidget
    BaseTrainWidget <|-- CustomScrollBar
    BaseTrainWidget <|-- EmptyStateWidget
    BaseTrainWidget <|-- RouteDisplayDialog
    
    TrainListWidget --> TrainItemWidget : contains
    TrainListWidget --> CustomScrollBar : uses
    TrainListWidget --> EmptyStateWidget : shows
    TrainItemWidget --> RouteDisplayDialog : opens
```

## Widget Composition Architecture

### Train List Widget Composition

```mermaid
graph TB
    subgraph "TrainListWidget"
        subgraph "Scroll Area"
            SA[QScrollArea]
            CSB[CustomScrollBar]
        end
        
        subgraph "Container Widget"
            CW[QWidget]
            VL[QVBoxLayout]
        end
        
        subgraph "Content Widgets"
            TIW1[TrainItemWidget 1]
            TIW2[TrainItemWidget 2]
            TIWn[TrainItemWidget n]
            ESW[EmptyStateWidget]
        end
    end
    
    SA --> CSB
    SA --> CW
    CW --> VL
    VL --> TIW1
    VL --> TIW2
    VL --> TIWn
    VL --> ESW
    
    TIW1 -.-> RDD[RouteDisplayDialog]
    TIW2 -.-> RDD
    TIWn -.-> RDD
```

### Widget State Management

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> Empty: No Train Data
    Initializing --> Loading: Fetching Data
    
    Empty --> Loading: Refresh Requested
    Loading --> Populated: Data Received
    Loading --> Error: Data Fetch Failed
    Loading --> Empty: No Data Available
    
    Populated --> Loading: Refresh Requested
    Populated --> Selected: Train Selected
    Populated --> Empty: Data Cleared
    
    Selected --> Populated: Selection Cleared
    Selected --> RouteDialog: Show Route Details
    
    RouteDialog --> Selected: Dialog Closed
    
    Error --> Loading: Retry Requested
    Error --> Empty: Clear Error
    
    Empty --> [*]: Widget Destroyed
    Populated --> [*]: Widget Destroyed
    Selected --> [*]: Widget Destroyed
    Error --> [*]: Widget Destroyed
```

## Theme System Integration

### Theme Application Flow

```mermaid
sequenceDiagram
    participant TM as Theme Manager
    participant MW as Main Window
    participant TLW as Train List Widget
    participant TIW as Train Item Widget
    participant CSB as Custom Scroll Bar
    participant ESW as Empty State Widget
    
    TM->>MW: theme_changed(theme_name)
    MW->>TLW: apply_theme(theme_name)
    
    TLW->>TLW: get_theme_colors(theme_name)
    TLW->>TLW: update_stylesheet()
    
    TLW->>TIW: apply_theme(theme_name)
    TLW->>CSB: apply_theme(theme_name)
    TLW->>ESW: apply_theme(theme_name)
    
    TIW->>TIW: update_colors()
    CSB->>CSB: update_colors()
    ESW->>ESW: update_colors()
    
    TIW-->>TLW: theme_applied
    CSB-->>TLW: theme_applied
    ESW-->>TLW: theme_applied
    
    TLW-->>MW: theme_applied
    MW-->>TM: theme_application_complete
```

### Theme Color Mapping

```mermaid
graph LR
    subgraph "Theme Colors"
        TC[Theme Colors Dict]
        
        subgraph "Color Categories"
            BG[Background Colors]
            TX[Text Colors]
            AC[Accent Colors]
            BR[Border Colors]
            ST[State Colors]
        end
    end
    
    subgraph "Widget Applications"
        subgraph "Train Item Widget"
            TIB[Item Background]
            TIT[Item Text]
            TIS[Selection State]
        end
        
        subgraph "Scroll Bar"
            SBB[Bar Background]
            SBH[Handle Color]
            SBT[Track Color]
        end
        
        subgraph "Empty State"
            ESB[Empty Background]
            EST[Empty Text]
            ESI[Empty Icon]
        end
    end
    
    TC --> BG
    TC --> TX
    TC --> AC
    TC --> BR
    TC --> ST
    
    BG --> TIB
    TX --> TIT
    ST --> TIS
    
    BG --> SBB
    AC --> SBH
    BR --> SBT
    
    BG --> ESB
    TX --> EST
    AC --> ESI
```

## Widget Communication Patterns

### Signal-Slot Communication

```mermaid
graph TB
    subgraph "Signal Sources"
        TIW[TrainItemWidget]
        CSB[CustomScrollBar]
        ESW[EmptyStateWidget]
        RDD[RouteDisplayDialog]
    end
    
    subgraph "Signal Types"
        TS[train_selected]
        RS[route_selected]
        SS[scroll_changed]
        AS[action_requested]
        DC[dialog_closed]
    end
    
    subgraph "Signal Handlers"
        TLW[TrainListWidget]
        MW[Main Window]
        TM[Train Manager]
    end
    
    TIW --> TS
    TIW --> RS
    CSB --> SS
    ESW --> AS
    RDD --> DC
    
    TS --> TLW
    RS --> MW
    SS --> TLW
    AS --> MW
    DC --> MW
    
    TLW --> TM
    MW --> TM
```

### Event Propagation

```mermaid
sequenceDiagram
    participant U as User
    participant TIW as Train Item Widget
    participant TLW as Train List Widget
    participant MW as Main Window
    participant TM as Train Manager
    
    U->>TIW: Click Train Item
    TIW->>TIW: mousePressEvent()
    TIW->>TIW: set_selected(True)
    TIW->>TLW: train_selected.emit(train_data)
    
    TLW->>TLW: handle_train_selection()
    TLW->>TLW: update_selection_state()
    TLW->>MW: train_selected.emit(train_data)
    
    MW->>MW: show_train_details()
    
    alt Double Click
        U->>TIW: Double Click Train Item
        TIW->>MW: route_selected.emit(train_data)
        MW->>TM: get_route_details(train_data)
        TM-->>MW: route_details
        MW->>MW: show_route_dialog(route_details)
    end
```

## Custom Widget Implementation

### Train Item Widget Details

```mermaid
graph TB
    subgraph "TrainItemWidget Layout"
        subgraph "Main Container"
            MC[QWidget Container]
            HL[QHBoxLayout]
        end
        
        subgraph "Time Section"
            TS[Time Container]
            DT[Departure Time]
            AR[Arrival Time]
        end
        
        subgraph "Route Section"
            RS[Route Container]
            DS[Destination]
            OP[Operator]
            PL[Platform]
        end
        
        subgraph "Status Section"
            SS[Status Container]
            ST[Status Text]
            DU[Duration]
            CH[Changes]
        end
        
        subgraph "Selection Indicator"
            SI[Selection Border]
            SH[Selection Highlight]
        end
    end
    
    MC --> HL
    HL --> TS
    HL --> RS
    HL --> SS
    
    TS --> DT
    TS --> AR
    
    RS --> DS
    RS --> OP
    RS --> PL
    
    SS --> ST
    SS --> DU
    SS --> CH
    
    MC --> SI
    MC --> SH
```

### Custom Scroll Bar Implementation

```mermaid
flowchart TD
    A[Scroll Event] --> B{Event Type}
    B -->|Mouse Wheel| C[Calculate Scroll Delta]
    B -->|Mouse Press| D[Handle Bar Click]
    B -->|Mouse Drag| E[Handle Bar Drag]
    
    C --> F[Apply Smooth Scrolling]
    D --> G[Jump to Position]
    E --> H[Update Position]
    
    F --> I[Start Animation]
    G --> J[Update Scroll Value]
    H --> J
    
    I --> K[Animate to Target]
    K --> L{Animation Complete?}
    L -->|No| K
    L -->|Yes| M[Update UI]
    
    J --> M
    M --> N[Emit Scroll Signal]
    N --> O[Update Content Position]
```

## Widget Performance Optimization

### Efficient Widget Updates

```mermaid
graph LR
    subgraph "Update Strategies"
        A[Batch Updates]
        B[Lazy Rendering]
        C[Widget Pooling]
        D[Selective Updates]
    end
    
    subgraph "Implementation"
        A1[Group multiple changes]
        B1[Render only visible items]
        C1[Reuse widget instances]
        D1[Update only changed properties]
    end
    
    subgraph "Benefits"
        R1[Reduced redraws]
        R2[Lower memory usage]
        R3[Faster scrolling]
        R4[Smoother animations]
    end
    
    A --> A1 --> R1
    B --> B1 --> R2
    C --> C1 --> R3
    D --> D1 --> R4
```

### Memory Management

```mermaid
sequenceDiagram
    participant TLW as Train List Widget
    participant Pool as Widget Pool
    participant TIW as Train Item Widget
    participant GC as Garbage Collector
    
    TLW->>Pool: request_widget()
    
    alt Widget Available
        Pool-->>TLW: reused_widget
        TLW->>TIW: update_train_data(new_data)
    else No Widget Available
        TLW->>TIW: create TrainItemWidget()
        TLW->>Pool: register_widget(widget)
    end
    
    Note over TLW: Widget no longer needed
    TLW->>TIW: clear_data()
    TLW->>Pool: return_widget(widget)
    Pool->>Pool: reset_widget_state()
    
    Note over Pool: Pool cleanup
    Pool->>GC: release_excess_widgets()
    GC->>GC: cleanup_memory()
```

## Widget Testing Strategy

### Widget Test Architecture

```mermaid
graph TB
    subgraph "Test Types"
        UT[Unit Tests]
        IT[Integration Tests]
        VT[Visual Tests]
        PT[Performance Tests]
    end
    
    subgraph "Test Tools"
        QT[Qt Test Framework]
        MT[Mock Objects]
        VR[Visual Regression]
        BT[Benchmark Tools]
    end
    
    subgraph "Test Scenarios"
        TS1[Widget Creation]
        TS2[Theme Application]
        TS3[User Interaction]
        TS4[Data Updates]
        TS5[Error Handling]
    end
    
    UT --> QT
    IT --> MT
    VT --> VR
    PT --> BT
    
    QT --> TS1
    MT --> TS2
    VR --> TS3
    BT --> TS4
    QT --> TS5
```

### Widget Test Examples

```mermaid
sequenceDiagram
    participant Test as Test Case
    participant TIW as Train Item Widget
    participant Mock as Mock Data
    participant Assert as Assertions
    
    Test->>Mock: create_test_train_data()
    Mock-->>Test: train_data
    
    Test->>TIW: TrainItemWidget(train_data)
    TIW-->>Test: widget_instance
    
    Test->>TIW: update_train_data(new_data)
    Test->>Assert: verify_labels_updated()
    
    Test->>TIW: apply_theme("dark")
    Test->>Assert: verify_colors_changed()
    
    Test->>TIW: simulate_click()
    Test->>Assert: verify_signal_emitted()
    
    Test->>TIW: set_selected(True)
    Test->>Assert: verify_selection_style()
```

## Accessibility Features

### Accessibility Implementation

```mermaid
graph TD
    subgraph "Accessibility Features"
        A[Keyboard Navigation]
        B[Screen Reader Support]
        C[High Contrast Mode]
        D[Focus Indicators]
        E[Accessible Labels]
    end
    
    subgraph "Implementation Methods"
        A1[Tab Order Management]
        B1[Accessible Names/Descriptions]
        C1[Color Contrast Ratios]
        D1[Focus Rectangle Styling]
        E1[ARIA-like Properties]
    end
    
    subgraph "Qt Accessibility"
        Q1[QAccessible Interface]
        Q2[Accessible Events]
        Q3[Role Definitions]
        Q4[State Information]
    end
    
    A --> A1 --> Q1
    B --> B1 --> Q2
    C --> C1 --> Q3
    D --> D1 --> Q4
    E --> E1 --> Q1
```

## Future Widget Enhancements

### Planned Widget Improvements

1. **Advanced Animations**: Smooth transitions and micro-interactions
2. **Touch Support**: Multi-touch gestures and touch-friendly sizing
3. **Virtualization**: Efficient handling of large datasets
4. **Custom Styling**: CSS-like styling system for widgets
5. **Responsive Design**: Adaptive layouts for different screen sizes

### Extension Points

- **Custom Widget Framework**: API for creating custom display components
- **Widget Marketplace**: Shareable widget components
- **Advanced Theming**: User-customizable widget appearances
- **Widget Analytics**: Usage tracking and performance metrics
- **Internationalization**: Multi-language widget support

## Widget Best Practices

### Design Guidelines

1. **Single Responsibility**: Each widget should have one clear purpose
2. **Consistent Theming**: All widgets should support the theme system
3. **Responsive Design**: Widgets should adapt to different screen sizes
4. **Performance Conscious**: Minimize redraws and memory usage
5. **Accessible**: Support keyboard navigation and screen readers

### Implementation Standards

1. **Signal-Slot Pattern**: Use Qt's signal-slot mechanism for communication
2. **Proper Cleanup**: Implement proper resource cleanup in destructors
3. **Error Handling**: Gracefully handle invalid data and edge cases
4. **Documentation**: Comprehensive docstrings and usage examples
5. **Testing**: Unit tests for all public methods and interactions

---

*This widget system documentation is maintained alongside the widget codebase and updated with each widget-related change.*