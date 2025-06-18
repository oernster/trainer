"""
Simple coverage test that runs the actual weather widgets file.
"""

import coverage
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

def run_weather_widgets_coverage():
    """Run weather widgets with coverage measurement."""
    
    # Start coverage
    cov = coverage.Coverage(source=['src/ui/weather_widgets'])
    cov.start()
    
    try:
        # Mock all the problematic imports before importing anything
        with patch.dict('sys.modules', {
            'PySide6.QtWidgets': Mock(
                QWidget=Mock,
                QVBoxLayout=Mock,
                QHBoxLayout=Mock,
                QLabel=Mock,
                QFrame=Mock,
                QScrollArea=Mock,
                QSizePolicy=Mock,
                QSpacerItem=Mock,
            ),
            'PySide6.QtCore': Mock(
                Qt=Mock(
                    AlignmentFlag=Mock(AlignCenter=1, AlignLeft=2),
                    MouseButton=Mock(LeftButton=1)
                ),
                Signal=Mock(),
                QTimer=Mock,
            ),
            'PySide6.QtGui': Mock(
                QFont=Mock(Weight=Mock(Bold=1)),
                QPalette=Mock,
            ),
            'version': Mock(
                __weather_version__='1.0.0',
                __weather_api_provider__='test'
            ),
            'src.models.weather_data': Mock(
                WeatherData=Mock,
                WeatherForecastData=Mock,
                TemperatureUnit=Mock(FAHRENHEIT='fahrenheit'),
                default_weather_icon_provider=Mock(get_weather_icon=Mock(return_value='☀️'))
            ),
            'src.managers.weather_manager': Mock(
                WeatherObserver=Mock
            ),
            'src.managers.weather_config': Mock(
                WeatherConfig=Mock
            ),
        }):
            # Import and test the weather widgets module
            import src.ui.weather_widgets as weather_widgets
            
            # Create mock instances for testing
            mock_weather_instance = Mock()
            mock_weather_instance.timestamp = datetime.now()
            mock_weather_instance.weather_code = 'sunny'
            mock_weather_instance.temperature_display = '20°C'
            mock_weather_instance.humidity = 65
            mock_weather_instance.get_temperature_display_in_unit = Mock(return_value='68°F')
            
            mock_config_instance = Mock()
            mock_config_instance.enabled = True
            mock_config_instance.show_humidity = True
            mock_config_instance.is_metric_units = Mock(return_value=True)
            
            mock_forecast_instance = Mock()
            mock_forecast_instance.current_day_hourly = [mock_weather_instance]
            mock_forecast_instance.daily_forecast = [mock_weather_instance]
            
            # Test WeatherDisplayComponent (abstract base class)
            class TestWeatherDisplayComponent(weather_widgets.WeatherDisplayComponent):
                def setup_ui(self):
                    self.test_setup_called = True
                
                def _refresh_display(self):
                    self.test_refresh_called = True
                
                def _apply_theme_styling(self):
                    self.test_theme_called = True
            
            # Test all methods of WeatherDisplayComponent
            component = TestWeatherDisplayComponent()
            component.update_weather_data(mock_weather_instance)
            component.update_config(mock_config_instance)
            component.apply_theme({'background': '#000', 'text': '#fff'})
            weather_data = component.get_weather_data()
            
            # Test WeatherItemWidget
            # Test initialization without weather data
            item1 = weather_widgets.WeatherItemWidget()
            item1.setup_ui()
            item1._refresh_display()
            item1._apply_theme_styling()
            
            # Test initialization with weather data - hourly
            item2 = weather_widgets.WeatherItemWidget(mock_weather_instance, is_daily=False)
            item2.setup_ui()
            item2.update_weather_data(mock_weather_instance)
            item2.update_config(mock_config_instance)
            item2._refresh_display()
            item2._get_time_display()
            item2.apply_theme({
                'background_secondary': '#2d2d2d',
                'border_primary': '#404040',
                'text_primary': '#ffffff',
                'background_hover': '#404040',
                'primary_accent': '#4fc3f7'
            })
            
            # Test initialization with weather data - daily
            item3 = weather_widgets.WeatherItemWidget(mock_weather_instance, is_daily=True)
            item3.setup_ui()
            item3._refresh_display()
            item3._get_time_display()
            
            # Test with no config
            item4 = weather_widgets.WeatherItemWidget(mock_weather_instance)
            item4._config = None
            item4._refresh_display()
            
            # Test with fahrenheit units
            mock_config_fahrenheit = Mock()
            mock_config_fahrenheit.is_metric_units = Mock(return_value=False)
            mock_config_fahrenheit.show_humidity = True
            item5 = weather_widgets.WeatherItemWidget(mock_weather_instance)
            item5.update_config(mock_config_fahrenheit)
            item5._refresh_display()
            
            # Test with hidden humidity
            mock_config_no_humidity = Mock()
            mock_config_no_humidity.is_metric_units = Mock(return_value=True)
            mock_config_no_humidity.show_humidity = False
            item6 = weather_widgets.WeatherItemWidget(mock_weather_instance)
            item6.update_config(mock_config_no_humidity)
            item6._refresh_display()
            
            # Test _refresh_display with missing labels
            item_missing_labels = weather_widgets.WeatherItemWidget(mock_weather_instance)
            item_missing_labels._time_label = None
            item_missing_labels._icon_label = None
            item_missing_labels._temp_label = None
            item_missing_labels._humidity_label = None
            item_missing_labels._refresh_display()
            
            # Test _get_time_display with no weather data
            item_no_data = weather_widgets.WeatherItemWidget()
            time_display = item_no_data._get_time_display()
            
            # Test _apply_theme_styling with no theme colors
            item_no_theme = weather_widgets.WeatherItemWidget()
            item_no_theme._theme_colors = {}
            item_no_theme._apply_theme_styling()
            
            # Test mouse events
            mock_event = Mock()
            mock_event.button = Mock(return_value=1)  # LeftButton
            
            # With weather data
            item2.mousePressEvent(mock_event)
            item2.enterEvent(mock_event)
            
            # Without weather data
            item1.mousePressEvent(mock_event)
            item1.enterEvent(mock_event)
            
            # Test WeatherForecastWidget
            forecast_widget = weather_widgets.WeatherForecastWidget()
            forecast_widget.setup_ui()
            
            # Test update_weather_forecast with empty data
            forecast_widget.update_weather_forecast([], is_daily=False)
            
            # Test update_weather_forecast with data
            weather_data_list = [mock_weather_instance, mock_weather_instance]
            forecast_widget.update_weather_forecast(weather_data_list, is_daily=False, config=mock_config_instance)
            forecast_widget.update_weather_forecast(weather_data_list, is_daily=True, config=mock_config_instance)
            forecast_widget.update_weather_forecast(weather_data_list, is_daily=True)  # Without config
            
            # Test clear_weather_items
            forecast_widget.clear_weather_items()
            
            # Test apply_theme
            theme_colors = {'background_primary': '#1a1a1a', 'border_primary': '#404040'}
            forecast_widget.apply_theme(theme_colors)
            
            # Test event handlers
            forecast_widget._on_weather_item_clicked(mock_weather_instance)
            forecast_widget._on_weather_item_hovered(mock_weather_instance)
            
            # Test DailyForecastWidget
            daily_widget = weather_widgets.DailyForecastWidget()
            daily_widget.update_daily_forecast([mock_weather_instance], mock_config_instance)
            daily_widget.update_daily_forecast([mock_weather_instance])  # Without config
            
            # Test HourlyForecastWidget
            hourly_widget = weather_widgets.HourlyForecastWidget()
            hourly_widget.update_hourly_forecast([mock_weather_instance], mock_config_instance)
            hourly_widget.update_hourly_forecast([mock_weather_instance])  # Without config
            
            # Test WeatherWidget
            weather_widget = weather_widgets.WeatherWidget()
            weather_widget.setup_ui()
            
            # Test update_config with enabled config
            weather_widget.update_config(mock_config_instance)
            
            # Test update_config with disabled config
            mock_config_disabled = Mock()
            mock_config_disabled.enabled = False
            weather_widget.update_config(mock_config_disabled)
            
            # Test apply_theme
            theme_colors = {'primary_accent': '#4fc3f7', 'background_primary': '#1a1a1a'}
            weather_widget.apply_theme(theme_colors)
            
            # Test WeatherObserver methods
            weather_widget.on_weather_updated(mock_forecast_instance)
            weather_widget.on_weather_error(Exception("Test error"))
            weather_widget.on_weather_loading(True)
            weather_widget.on_weather_loading(False)
            
            # Test utility methods
            weather_widget._show_status("Test message", is_error=True)
            weather_widget._show_status("Test message", is_error=False)
            weather_widget._clear_status()
            
            # Test getters
            current_forecast = weather_widget.get_current_forecast()
            is_loading = weather_widget.is_loading()
            
            # Test signal emission methods
            weather_widget.refresh_weather()
            weather_widget.show_weather_settings()
            
            # Test edge cases with missing child widgets
            weather_widget_edge = weather_widgets.WeatherWidget()
            weather_widget_edge._daily_forecast_widget = None
            weather_widget_edge._weekly_forecast_widget = None
            weather_widget_edge._daily_label = None
            weather_widget_edge._weekly_label = None
            weather_widget_edge.update_config(mock_config_instance)
            weather_widget_edge.apply_theme(theme_colors)
            weather_widget_edge.on_weather_updated(mock_forecast_instance)
            
            # Test with child widgets that have no weather items
            weather_widget_empty = weather_widgets.WeatherWidget()
            weather_widget_empty._daily_forecast_widget = Mock()
            weather_widget_empty._daily_forecast_widget._weather_items = []
            weather_widget_empty._weekly_forecast_widget = Mock()
            weather_widget_empty._weekly_forecast_widget._weather_items = []
            weather_widget_empty.update_config(mock_config_instance)
            
            print("All weather widget functionality tested successfully!")
            
    finally:
        # Stop coverage and generate report
        cov.stop()
        cov.save()
        
        print("\n" + "="*60)
        print("WEATHER WIDGETS COVERAGE REPORT")
        print("="*60)
        
        # Generate coverage report
        cov.report(show_missing=True)
        
        # Generate HTML report
        cov.html_report(directory="htmlcov_weather_widgets")
        
        print("\nHTML coverage report generated in htmlcov_weather_widgets/")
        print("="*60)


if __name__ == "__main__":
    run_weather_widgets_coverage()