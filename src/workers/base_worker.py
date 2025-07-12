"""
Base worker class for all worker threads.

This module provides the foundation for all worker threads with common functionality
including thread management, cancellation support, and performance monitoring.
"""

from PySide6.QtCore import QObject, QThread, Signal, QMutex, QTimer
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import time


class BaseWorker(QObject):
    """Base class for all worker threads with common functionality."""
    
    # Common signals
    started = Signal()
    finished = Signal()
    error = Signal(str)
    progress = Signal(int)  # Progress percentage (0-100)
    status_changed = Signal(str)  # Status message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker_thread = QThread()
        self.moveToThread(self.worker_thread)
        
        # Thread management
        self.worker_thread.started.connect(self.on_thread_started)
        self.worker_thread.finished.connect(self.on_thread_finished)
        
        # Cancellation support
        self._cancel_requested = False
        self._mutex = QMutex()
        
        # Performance monitoring
        self._operation_times = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def start_thread(self):
        """Start the worker thread."""
        if not self.worker_thread.isRunning():
            self.worker_thread.start()
            self.logger.info(f"{self.__class__.__name__} thread starting")
            
    def stop_thread(self):
        """Stop the worker thread gracefully."""
        self.logger.info(f"{self.__class__.__name__} thread stopping")
        self.request_cancellation()
        self.worker_thread.quit()
        if not self.worker_thread.wait(5000):  # Wait up to 5 seconds
            self.logger.warning(f"{self.__class__.__name__} thread did not stop gracefully")
            self.worker_thread.terminate()
            
    def request_cancellation(self):
        """Request cancellation of current operation."""
        self._mutex.lock()
        try:
            self._cancel_requested = True
            self.logger.debug(f"{self.__class__.__name__} cancellation requested")
        finally:
            self._mutex.unlock()
            
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        self._mutex.lock()
        try:
            return self._cancel_requested
        finally:
            self._mutex.unlock()
            
    def reset_cancellation(self):
        """Reset cancellation flag for new operation."""
        self._mutex.lock()
        try:
            self._cancel_requested = False
        finally:
            self._mutex.unlock()
            
    def emit_progress(self, percentage: int, message: str = ""):
        """Emit progress update."""
        self.progress.emit(percentage)
        if message:
            self.status_changed.emit(message)
            
    def measure_operation(self, operation_name: str):
        """Context manager for measuring operation performance."""
        return OperationTimer(self, operation_name)
        
    def record_operation_time(self, operation_name: str, duration: float):
        """Record operation timing for performance monitoring."""
        if operation_name not in self._operation_times:
            self._operation_times[operation_name] = []
        self._operation_times[operation_name].append({
            'duration': duration,
            'timestamp': time.time()
        })
        
        # Keep only last 100 measurements per operation
        if len(self._operation_times[operation_name]) > 100:
            self._operation_times[operation_name] = self._operation_times[operation_name][-100:]
            
    def get_performance_stats(self) -> Dict[str, Dict]:
        """Get performance statistics for this worker."""
        stats = {}
        for operation, measurements in self._operation_times.items():
            if measurements:
                durations = [m['duration'] for m in measurements]
                stats[operation] = {
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'total_operations': len(measurements),
                    'recent_operations': len([m for m in measurements if time.time() - m['timestamp'] < 300])  # Last 5 minutes
                }
        return stats
        
    @abstractmethod
    def on_thread_started(self):
        """Called when thread starts."""
        pass
        
    @abstractmethod
    def on_thread_finished(self):
        """Called when thread finishes."""
        pass


class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, worker: BaseWorker, operation_name: str):
        self.worker = worker
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.worker.record_operation_time(self.operation_name, duration)
            self.worker.logger.debug(f"{self.operation_name} completed in {duration:.3f}s")