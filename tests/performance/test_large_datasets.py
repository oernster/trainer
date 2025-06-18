"""
Performance tests for large datasets.

Tests application performance with large datasets to ensure
the application can handle 50+ trains efficiently.
"""

import pytest
import time
import psutil
import os
from datetime import datetime, timedelta
from src.models.train_data import TrainData, TrainStatus, ServiceType


class TestPerformance:
    """Test application performance with large datasets."""

    def generate_large_train_dataset(self, count=100):
        """Generate large dataset of train data."""
        trains = []
        base_time = datetime.now().replace(second=0, microsecond=0)

        for i in range(count):
            train = TrainData(
                departure_time=base_time + timedelta(minutes=i * 10),
                scheduled_departure=base_time + timedelta(minutes=i * 10),
                destination="London Waterloo",
                platform=str((i % 10) + 1),
                operator="South Western Railway",
                service_type=ServiceType.FAST if i % 2 == 0 else ServiceType.STOPPING,
                status=TrainStatus.ON_TIME if i % 3 == 0 else TrainStatus.DELAYED,
                delay_minutes=i % 5,
                estimated_arrival=base_time + timedelta(minutes=i * 10 + 47),
                journey_duration=timedelta(minutes=47),
                current_location="Fleet",
                train_uid=f"W{12345 + i}",
                service_id=f"2467300{i}",
            )
            trains.append(train)

        return trains

    @pytest.mark.performance
    def test_train_data_creation_performance(self):
        """Test performance of creating many TrainData objects."""
        start_time = time.time()

        trains = self.generate_large_train_dataset(1000)

        end_time = time.time()
        creation_time = end_time - start_time

        # Should create 1000 trains in under 1 second
        assert (
            creation_time < 1.0
        ), f"Train creation took {creation_time:.2f}s, expected < 1.0s"
        assert len(trains) == 1000

        # Verify all trains are valid
        for train in trains[:10]:  # Check first 10 for validity
            assert isinstance(train, TrainData)
            assert train.destination == "London Waterloo"
            assert train.operator == "South Western Railway"

    @pytest.mark.performance
    def test_train_data_property_access_performance(self):
        """Test performance of accessing train data properties."""
        trains = self.generate_large_train_dataset(1000)

        start_time = time.time()

        # Access various properties for all trains
        for train in trains:
            _ = train.is_delayed
            _ = train.is_cancelled
            _ = train.status_color
            _ = train.format_departure_time()
            _ = train.format_delay()
            _ = train.get_service_icon()
            _ = train.get_status_icon()

        end_time = time.time()
        access_time = end_time - start_time

        # Should access properties for 1000 trains in under 0.5 seconds
        assert (
            access_time < 0.5
        ), f"Property access took {access_time:.2f}s, expected < 0.5s"

    @pytest.mark.performance
    def test_train_data_display_dict_performance(self):
        """Test performance of converting trains to display dictionaries."""
        trains = self.generate_large_train_dataset(500)

        start_time = time.time()

        display_dicts = [train.to_display_dict() for train in trains]

        end_time = time.time()
        conversion_time = end_time - start_time

        # Should convert 500 trains in under 0.5 seconds
        assert (
            conversion_time < 0.5
        ), f"Display dict conversion took {conversion_time:.2f}s, expected < 0.5s"
        assert len(display_dicts) == 500

        # Verify conversion quality
        for display_dict in display_dicts[:5]:  # Check first 5
            assert "departure_time" in display_dict
            assert "destination" in display_dict
            assert "status_color" in display_dict

    @pytest.mark.performance
    def test_train_sorting_performance(self):
        """Test performance of sorting large train datasets."""
        trains = self.generate_large_train_dataset(1000)

        # Shuffle the trains to make sorting more realistic
        import random

        random.shuffle(trains)

        start_time = time.time()

        sorted_trains = sorted(trains, key=lambda t: t.departure_time)

        end_time = time.time()
        sort_time = end_time - start_time

        # Should sort 1000 trains in under 0.1 seconds
        assert sort_time < 0.1, f"Sorting took {sort_time:.2f}s, expected < 0.1s"
        assert len(sorted_trains) == 1000

        # Verify sorting correctness
        for i in range(len(sorted_trains) - 1):
            assert (
                sorted_trains[i].departure_time <= sorted_trains[i + 1].departure_time
            )

    @pytest.mark.performance
    def test_train_filtering_performance(self):
        """Test performance of filtering large train datasets."""
        trains = self.generate_large_train_dataset(1000)

        start_time = time.time()

        # Filter for delayed trains
        delayed_trains = [train for train in trains if train.is_delayed]

        # Filter for cancelled trains
        cancelled_trains = [train for train in trains if train.is_cancelled]

        # Filter for fast services
        fast_trains = [
            train for train in trains if train.service_type == ServiceType.FAST
        ]

        end_time = time.time()
        filter_time = end_time - start_time

        # Should filter 1000 trains multiple ways in under 0.1 seconds
        assert filter_time < 0.1, f"Filtering took {filter_time:.2f}s, expected < 0.1s"

        # Verify filtering results
        assert len(delayed_trains) > 0
        assert len(fast_trains) > 0
        assert all(train.is_delayed for train in delayed_trains)
        assert all(train.service_type == ServiceType.FAST for train in fast_trains)

    @pytest.mark.performance
    def test_memory_usage_with_large_datasets(self):
        """Test memory usage doesn't grow excessively."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create and destroy large datasets multiple times
        for iteration in range(10):
            trains = self.generate_large_train_dataset(200)

            # Do some operations on the trains
            _ = [train.to_display_dict() for train in trains]
            _ = sorted(trains, key=lambda t: t.departure_time)
            _ = [train for train in trains if train.is_delayed]

            del trains

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (less than 50MB)
        memory_growth_mb = memory_growth / (1024 * 1024)
        assert (
            memory_growth_mb < 50
        ), f"Memory grew by {memory_growth_mb:.1f}MB, expected < 50MB"

    @pytest.mark.performance
    def test_concurrent_train_operations(self):
        """Test performance of concurrent operations on train data."""
        trains = self.generate_large_train_dataset(500)

        start_time = time.time()

        # Simulate concurrent operations that might happen in the UI
        results = []

        # Multiple operations happening "simultaneously"
        for _ in range(5):
            # Sort trains
            sorted_trains = sorted(trains, key=lambda t: t.departure_time)
            results.append(len(sorted_trains))

            # Filter trains
            delayed = [t for t in trains if t.is_delayed]
            results.append(len(delayed))

            # Convert to display format
            display_data = [t.to_display_dict() for t in trains[:50]]  # First 50 only
            results.append(len(display_data))

        end_time = time.time()
        concurrent_time = end_time - start_time

        # Should complete all operations in under 1 second
        assert (
            concurrent_time < 1.0
        ), f"Concurrent operations took {concurrent_time:.2f}s, expected < 1.0s"
        assert len(results) == 15  # 5 iterations × 3 operations each

    @pytest.mark.performance
    def test_train_data_serialization_performance(self):
        """Test performance of train data serialization operations."""
        trains = self.generate_large_train_dataset(200)

        start_time = time.time()

        # Convert all trains to dictionaries (simulating JSON serialization)
        serialized_data = []
        for train in trains:
            train_dict = {
                "departure_time": train.departure_time.isoformat(),
                "scheduled_departure": train.scheduled_departure.isoformat(),
                "destination": train.destination,
                "platform": train.platform,
                "operator": train.operator,
                "service_type": train.service_type.value,
                "status": train.status.value,
                "delay_minutes": train.delay_minutes,
                "train_uid": train.train_uid,
                "service_id": train.service_id,
            }
            serialized_data.append(train_dict)

        end_time = time.time()
        serialization_time = end_time - start_time

        # Should serialize 200 trains in under 0.2 seconds
        assert (
            serialization_time < 0.2
        ), f"Serialization took {serialization_time:.2f}s, expected < 0.2s"
        assert len(serialized_data) == 200

        # Verify serialization quality
        for item in serialized_data[:5]:
            assert "departure_time" in item
            assert "destination" in item
            assert "status" in item

    @pytest.mark.performance
    def test_train_data_bulk_operations_scaling(self):
        """Test how operations scale with dataset size."""
        dataset_sizes = [100, 500, 1000, 2000]
        times = []

        for size in dataset_sizes:
            trains = self.generate_large_train_dataset(size)

            start_time = time.time()

            # Perform standard operations
            _ = sorted(trains, key=lambda t: t.departure_time)
            _ = [train.to_display_dict() for train in trains]
            _ = [train for train in trains if train.is_delayed]

            end_time = time.time()
            operation_time = end_time - start_time
            times.append(operation_time)

        # Verify that time scales reasonably (not exponentially)
        # Time for 2000 items should be less than 8x time for 500 items
        time_500 = times[1]  # 500 items
        time_2000 = times[3]  # 2000 items

        scaling_factor = time_2000 / time_500 if time_500 > 0 else 0
        assert (
            scaling_factor < 8
        ), f"Operations scale poorly: {scaling_factor:.1f}x slower for 4x data"

        # All operations should complete in reasonable time
        for i, (size, time_taken) in enumerate(zip(dataset_sizes, times)):
            max_expected_time = size / 1000.0  # 1 second per 1000 items
            assert (
                time_taken < max_expected_time
            ), f"Size {size} took {time_taken:.2f}s, expected < {max_expected_time:.2f}s"


class TestMemoryEfficiency:
    """Test memory efficiency of train data operations."""

    @pytest.mark.performance
    def test_train_data_memory_footprint(self):
        """Test memory footprint of individual train data objects."""
        import sys

        # Create a single train
        train = TrainData(
            departure_time=datetime.now(),
            scheduled_departure=datetime.now(),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
        )

        # Get approximate size
        train_size = sys.getsizeof(train)

        # Should be reasonably small (less than 1KB per train)
        assert (
            train_size < 1024
        ), f"Train object size {train_size} bytes, expected < 1024 bytes"

    @pytest.mark.performance
    def test_large_dataset_memory_efficiency(self):
        """Test memory efficiency with large datasets."""
        process = psutil.Process(os.getpid())

        # Measure baseline memory
        baseline_memory = process.memory_info().rss

        # Create large dataset
        trains = []
        for i in range(1000):
            train = TrainData(
                departure_time=datetime.now() + timedelta(minutes=i),
                scheduled_departure=datetime.now() + timedelta(minutes=i),
                destination="London Waterloo",
                platform=str(i % 10),
                operator="South Western Railway",
                service_type=ServiceType.FAST,
                status=TrainStatus.ON_TIME,
                delay_minutes=0,
                estimated_arrival=None,
                journey_duration=None,
                current_location="Fleet",
                train_uid=f"W{i}",
                service_id=f"S{i}",
            )
            trains.append(train)

        # Measure memory after creating trains
        after_creation_memory = process.memory_info().rss
        memory_used = after_creation_memory - baseline_memory
        memory_per_train = memory_used / 1000

        # Should use less than 2KB per train on average
        assert (
            memory_per_train < 2048
        ), f"Memory per train: {memory_per_train:.0f} bytes, expected < 2048 bytes"

        # Clean up
        del trains
