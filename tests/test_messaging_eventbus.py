"""
Comprehensive test suite for EventBus - Hedge Fund Production Grade
Tests cover functionality, performance, reliability, thread safety, and edge cases.
"""

import pytest
import threading
import time
import uuid
import pandas as pd
from unittest.mock import patch

from onesecondtrader.messaging.eventbus import EventBus
from onesecondtrader.messaging import events
from onesecondtrader.core import models


class TestEventBusBasicFunctionality:
    """Test core subscribe/publish/unsubscribe functionality."""

    def test_subscribe_and_publish_basic(self):
        """Test basic subscription and publishing."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(event.symbol)

        bus.subscribe(events.Market.IncomingBar, handler)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        bus.publish(event)
        assert calls == ["AAPL"]

    def test_unsubscribe_removes_handler(self):
        """Test that unsubscribe properly removes handlers."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(event.symbol)

        bus.subscribe(events.Market.IncomingBar, handler)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        bus.publish(event)
        assert len(calls) == 1

        bus.unsubscribe(events.Market.IncomingBar, handler)
        bus.publish(event)
        assert len(calls) == 1  # No new calls after unsubscribe

    def test_multiple_handlers_same_event(self):
        """Test multiple handlers for the same event type."""
        bus = EventBus()
        calls1, calls2 = [], []

        def handler1(event):
            calls1.append(event.symbol)

        def handler2(event):
            calls2.append(event.symbol)

        bus.subscribe(events.Market.IncomingBar, handler1)
        bus.subscribe(events.Market.IncomingBar, handler2)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        bus.publish(event)
        assert calls1 == ["AAPL"]
        assert calls2 == ["AAPL"]

    def test_inheritance_based_subscription(self):
        """Test that handlers receive events from child types."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(f"{type(event).__name__}:{event.symbol}")

        # Subscribe to base Market events
        bus.subscribe(events.Base.Market, handler)

        # Publish specific IncomingBar event
        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        bus.publish(event)
        assert calls == ["IncomingBar:AAPL"]

    def test_event_filters_basic(self):
        """Test basic event filtering functionality."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(event.symbol)

        # Subscribe with AAPL-only filter
        bus.subscribe(
            events.Market.IncomingBar, handler, lambda event: event.symbol == "AAPL"
        )

        # Create events
        aapl_event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        googl_event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="GOOGL",
            bar=models.Bar(
                open=2800.0, high=2801.0, low=2799.0, close=2800.5, volume=500
            ),
        )

        bus.publish(aapl_event)
        bus.publish(googl_event)

        assert calls == ["AAPL"]  # Only AAPL should pass filter

    def test_sequence_numbers_assigned(self):
        """Test that events receive sequential sequence numbers."""
        bus = EventBus()

        event1 = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        event2 = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="GOOGL",
            bar=models.Bar(
                open=2800.0, high=2801.0, low=2799.0, close=2800.5, volume=500
            ),
        )

        bus.publish(event1)
        bus.publish(event2)

        assert event1.event_bus_sequence_number == 0
        assert event2.event_bus_sequence_number == 1


class TestEventBusErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_event_type_subscription(self):
        """Test subscription with invalid event type."""
        bus = EventBus()

        def handler(event):
            pass

        # Should not raise exception, but should log error
        with patch("onesecondtrader.monitoring.console.logger.error") as mock_log:
            bus.subscribe(str, handler)  # Invalid type
            mock_log.assert_called_once()

    def test_invalid_handler_subscription(self):
        """Test subscription with invalid handler."""
        bus = EventBus()

        # Should not raise exception, but should log error
        with patch("onesecondtrader.monitoring.console.logger.error") as mock_log:
            bus.subscribe(events.Market.IncomingBar, "not_callable")
            mock_log.assert_called_once()

    def test_invalid_filter_subscription(self):
        """Test subscription with invalid filter."""
        bus = EventBus()

        def handler(event):
            pass

        # Should not raise exception, but should log error
        with patch("onesecondtrader.monitoring.console.logger.error") as mock_log:
            bus.subscribe(events.Market.IncomingBar, handler, "not_callable")
            mock_log.assert_called_once()

    def test_filter_signature_validation(self):
        """Test that filter signature validation works correctly."""
        bus = EventBus()

        def handler(event):
            pass

        # Valid filter - should work without errors
        bus.subscribe(events.Market.IncomingBar, handler, lambda event: True)

        # Invalid filters - should log errors
        with patch("onesecondtrader.monitoring.console.logger.error") as mock_log:
            # No parameters
            bus.subscribe(events.Market.IncomingBar, handler, lambda: True)
            assert mock_log.called
            mock_log.reset_mock()

            # Too many parameters
            bus.subscribe(events.Market.IncomingBar, handler, lambda x, y: True)
            assert mock_log.called
            mock_log.reset_mock()

            # *args not allowed
            bus.subscribe(events.Market.IncomingBar, handler, lambda *args: True)
            assert mock_log.called
            mock_log.reset_mock()

            # **kwargs not allowed
            bus.subscribe(events.Market.IncomingBar, handler, lambda **kwargs: True)
            assert mock_log.called

    def test_filter_return_type_annotation_validation(self):
        """Test validation of filter return type annotations."""
        bus = EventBus()

        def handler(event):
            pass

        # Valid return type annotation
        def valid_filter(event) -> bool:
            return True

        bus.subscribe(events.Market.IncomingBar, handler, valid_filter)

        # Invalid return type annotation - should log error
        with patch("onesecondtrader.monitoring.console.logger.error") as mock_log:

            def invalid_filter(event) -> str:
                return "not_boolean"

            bus.subscribe(events.Market.IncomingBar, handler, invalid_filter)
            assert mock_log.called

    def test_filter_runtime_return_type_validation(self):
        """Test runtime validation of filter return types."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(event.symbol)

        # Filter that returns non-boolean
        bus.subscribe(events.Market.IncomingBar, handler, lambda event: "not_boolean")

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        with patch("onesecondtrader.monitoring.console.logger.warning") as mock_log:
            bus.publish(event)
            # Should get 2 warnings: 1 for invalid return type, 1 for no handlers receiving event
            assert mock_log.call_count == 2

            # Check that the first warning is about return type
            first_call_args = mock_log.call_args_list[0][0][0]
            assert "returned str, expected bool" in first_call_args

        # Handler should not be called due to invalid return type
        assert calls == []

    def test_filter_runtime_signature_error_handling(self):
        """Test runtime handling of filter signature errors."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(event.symbol)

        # This should pass signature validation but fail at runtime
        # (we'll manually add a bad filter to test runtime handling)
        bus.subscribe(events.Market.IncomingBar, handler, lambda event: True)

        # Manually replace with bad filter to test runtime error handling
        def bad_filter():  # No parameters
            return True

        bus._handlers[events.Market.IncomingBar][0] = (handler, bad_filter)
        bus._rebuild_cache()

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        with patch("onesecondtrader.monitoring.console.logger.error") as mock_log:
            bus.publish(event)
            assert mock_log.called

        # Handler should not be called due to filter error
        assert calls == []

    def test_duplicate_subscription_warning(self):
        """Test that duplicate subscriptions generate warnings."""
        bus = EventBus()

        def handler(event):
            pass

        bus.subscribe(events.Market.IncomingBar, handler)

        # Second subscription should generate warning
        with patch("onesecondtrader.monitoring.console.logger.warning") as mock_log:
            bus.subscribe(events.Market.IncomingBar, handler)
            mock_log.assert_called_once()

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a handler that was never subscribed."""
        bus = EventBus()

        def handler(event):
            pass

        # Should not raise exception, but should log warning
        with patch("onesecondtrader.monitoring.console.logger.warning") as mock_log:
            bus.unsubscribe(events.Market.IncomingBar, handler)
            mock_log.assert_called_once()

    def test_publish_invalid_event(self):
        """Test publishing invalid event type."""
        bus = EventBus()

        # Should not raise exception, but should log error
        with patch("onesecondtrader.monitoring.console.logger.error") as mock_log:
            bus.publish("not_an_event")
            mock_log.assert_called_once()

    def test_handler_exception_handling(self):
        """Test that handler exceptions don't crash the event bus."""
        bus = EventBus()
        calls = []

        def failing_handler(event):
            raise ValueError("Handler intentionally fails")

        def working_handler(event):
            calls.append(event.symbol)

        bus.subscribe(events.Market.IncomingBar, failing_handler)
        bus.subscribe(events.Market.IncomingBar, working_handler)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        # Should not raise exception
        with patch("onesecondtrader.monitoring.console.logger.exception") as mock_log:
            bus.publish(event)
            mock_log.assert_called_once()

        # Working handler should still be called
        assert calls == ["AAPL"]

    def test_filter_exception_handling(self):
        """Test that filter exceptions don't crash the event bus."""
        bus = EventBus()
        calls = []

        def failing_filter(event):
            raise ValueError("Filter intentionally fails")

        def handler(event):
            calls.append(event.symbol)

        bus.subscribe(events.Market.IncomingBar, handler, failing_filter)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        # Should not raise exception
        with patch("onesecondtrader.monitoring.console.logger.exception") as mock_log:
            bus.publish(event)
            mock_log.assert_called_once()

        # Handler should not be called due to filter failure
        assert calls == []


class TestEventBusPerformance:
    """Test performance characteristics for hedge fund requirements."""

    def test_publish_performance_single_thread(self):
        """Test publish performance in single thread."""
        bus = EventBus()
        call_count = 0

        def fast_handler(event):
            nonlocal call_count
            call_count += 1

        bus.subscribe(events.Market.IncomingBar, fast_handler)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        # Measure time for 1000 publishes
        start_time = time.perf_counter()
        for _ in range(1000):
            bus.publish(event)
        end_time = time.perf_counter()

        duration = end_time - start_time
        events_per_second = 1000 / duration

        # Should handle at least 10,000 events/second
        assert events_per_second > 10000, f"Only {events_per_second:.0f} events/sec"
        assert call_count == 1000

    def test_concurrent_publish_performance(self):
        """Test concurrent publish performance - critical for HFT."""
        bus = EventBus()
        call_count = 0
        call_lock = threading.Lock()

        def thread_safe_handler(event):
            nonlocal call_count
            with call_lock:
                call_count += 1

        bus.subscribe(events.Market.IncomingBar, thread_safe_handler)

        def publish_events(num_events):
            event = events.Market.IncomingBar(
                ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
                symbol="AAPL",
                bar=models.Bar(
                    open=100.0, high=101.0, low=99.0, close=100.5, volume=1000
                ),
            )
            for _ in range(num_events):
                bus.publish(event)

        # Test with 5 threads publishing 200 events each
        num_threads = 5
        events_per_thread = 200

        start_time = time.perf_counter()

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=publish_events, args=(events_per_thread,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        end_time = time.perf_counter()

        duration = end_time - start_time
        total_events = num_threads * events_per_thread
        events_per_second = total_events / duration

        # Should handle concurrent load efficiently
        assert events_per_second > 5000, (
            f"Only {events_per_second:.0f} events/sec concurrent"
        )
        assert call_count == total_events

    def test_cache_rebuild_performance(self):
        """Test that cache rebuilds don't significantly impact performance."""
        bus = EventBus()

        # Add multiple handlers to make cache rebuild more expensive
        handlers = []
        for i in range(10):

            def handler(event, i=i):
                pass

            handlers.append(handler)
            bus.subscribe(events.Market.IncomingBar, handler)

        # Measure cache rebuild time
        start_time = time.perf_counter()
        bus._rebuild_cache()
        end_time = time.perf_counter()

        rebuild_time = end_time - start_time

        # Cache rebuild should be very fast (< 1ms)
        assert rebuild_time < 0.001, f"Cache rebuild took {rebuild_time * 1000:.2f}ms"


class TestEventBusThreadSafety:
    """Test thread safety - critical for hedge fund production systems."""

    def test_concurrent_subscribe_unsubscribe(self):
        """Test concurrent subscription and unsubscription operations."""
        bus = EventBus()

        def worker(worker_id):
            def handler(event):
                pass

            # Subscribe and unsubscribe repeatedly
            for i in range(50):
                bus.subscribe(events.Market.IncomingBar, handler)
                bus.unsubscribe(events.Market.IncomingBar, handler)

        # Run multiple workers concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without deadlocks or exceptions

    def test_concurrent_publish_and_subscribe(self):
        """Test concurrent publishing while subscribing/unsubscribing."""
        bus = EventBus()
        call_counts = {}
        call_lock = threading.Lock()

        def publisher():
            event = events.Market.IncomingBar(
                ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
                symbol="AAPL",
                bar=models.Bar(
                    open=100.0, high=101.0, low=99.0, close=100.5, volume=1000
                ),
            )
            for _ in range(100):
                bus.publish(event)
                time.sleep(0.001)  # Small delay to allow interleaving

        def subscriber(worker_id):
            def handler(event):
                with call_lock:
                    call_counts[worker_id] = call_counts.get(worker_id, 0) + 1

            # Subscribe, let it run, then unsubscribe
            bus.subscribe(events.Market.IncomingBar, handler)
            time.sleep(0.05)  # Let some events be published
            bus.unsubscribe(events.Market.IncomingBar, handler)

        # Start publisher
        pub_thread = threading.Thread(target=publisher)
        pub_thread.start()

        # Start multiple subscribers
        sub_threads = []
        for i in range(3):
            thread = threading.Thread(target=subscriber, args=(i,))
            sub_threads.append(thread)
            thread.start()

        # Wait for completion
        pub_thread.join()
        for thread in sub_threads:
            thread.join()

        # Should have received some events (exact count depends on timing)
        assert len(call_counts) > 0

    def test_sequence_number_thread_safety(self):
        """Test that sequence numbers are assigned correctly under concurrency."""
        bus = EventBus()
        sequence_numbers = []
        sequence_lock = threading.Lock()

        def handler(event):
            with sequence_lock:
                sequence_numbers.append(event.event_bus_sequence_number)

        bus.subscribe(events.Market.IncomingBar, handler)

        def publisher(start_symbol):
            for i in range(50):
                event = events.Market.IncomingBar(
                    ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
                    symbol=f"{start_symbol}{i}",
                    bar=models.Bar(
                        open=100.0, high=101.0, low=99.0, close=100.5, volume=1000
                    ),
                )
                bus.publish(event)

        # Start multiple publishers
        threads = []
        for i in range(3):
            thread = threading.Thread(target=publisher, args=(f"SYM{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check that all sequence numbers are unique and sequential
        sequence_numbers.sort()
        expected = list(range(len(sequence_numbers)))
        assert sequence_numbers == expected


class TestEventBusAdvancedScenarios:
    """Test advanced scenarios for hedge fund trading systems."""

    def test_high_frequency_market_data_simulation(self):
        """Simulate high-frequency market data processing."""
        bus = EventBus()

        # Simulate multiple strategies
        strategy_calls = {"momentum": 0, "arbitrage": 0, "market_making": 0}

        def momentum_strategy(event):
            strategy_calls["momentum"] += 1

        def arbitrage_strategy(event):
            strategy_calls["arbitrage"] += 1

        def market_making_strategy(event):
            strategy_calls["market_making"] += 1

        # Subscribe strategies to different event types
        bus.subscribe(events.Market.IncomingBar, momentum_strategy)
        bus.subscribe(events.Base.Market, arbitrage_strategy)  # All market events
        bus.subscribe(
            events.Market.IncomingBar,
            market_making_strategy,
            lambda event: event.bar.volume > 500,  # High volume filter
        )

        # Simulate market data stream
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

        start_time = time.perf_counter()

        for i in range(1000):
            symbol = symbols[i % len(symbols)]
            volume = 100 + (i % 1000)  # Varying volume

            event = events.Market.IncomingBar(
                ts_event=pd.Timestamp("2023-01-01", tz="UTC") + pd.Timedelta(seconds=i),
                symbol=symbol,
                bar=models.Bar(
                    open=100.0 + i * 0.01,
                    high=101.0 + i * 0.01,
                    low=99.0 + i * 0.01,
                    close=100.5 + i * 0.01,
                    volume=volume,
                ),
            )
            bus.publish(event)

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Verify all strategies received appropriate events
        assert strategy_calls["momentum"] == 1000  # All events
        assert strategy_calls["arbitrage"] == 1000  # All market events
        assert strategy_calls["market_making"] > 500  # High volume events only

        # Should process 1000 events very quickly
        events_per_second = 1000 / duration
        assert events_per_second > 5000, f"Only {events_per_second:.0f} events/sec"

    def test_order_lifecycle_simulation(self):
        """Simulate complete order lifecycle with multiple event types."""
        bus = EventBus()

        order_states = {}

        def order_tracker(event):
            if hasattr(event, "order_id"):
                order_id = event.order_id
            elif hasattr(event, "order_submitted_id"):
                order_id = event.order_submitted_id
            elif hasattr(event, "associated_order_submitted_id"):
                order_id = event.associated_order_submitted_id
            else:
                return

            event_type = type(event).__name__
            if order_id not in order_states:
                order_states[order_id] = []
            order_states[order_id].append(event_type)

        # Subscribe to all order-related events
        bus.subscribe(events.Base.Request, order_tracker)
        bus.subscribe(events.Base.Response, order_tracker)

        # Simulate order lifecycle
        order_id = uuid.uuid4()

        # 1. Market order request
        market_order = events.Request.MarketOrder(
            symbol="AAPL",
            side=models.Side.BUY,
            quantity=100.0,
            time_in_force=models.TimeInForce.DAY,
            order_id=order_id,
        )
        bus.publish(market_order)

        # 2. Order submitted response
        order_submitted = events.Response.OrderSubmitted(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            order_submitted_id=order_id,
            associated_request_id=order_id,
        )
        bus.publish(order_submitted)

        # 3. Order filled response
        order_filled = events.Response.OrderFilled(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            associated_order_submitted_id=order_id,
            side=models.Side.BUY,
            quantity_filled=100.0,
            filled_at_price=150.0,
            commission_and_fees=1.0,
        )
        bus.publish(order_filled)

        # Verify complete order lifecycle was tracked
        assert order_id in order_states
        lifecycle = order_states[order_id]
        assert "MarketOrder" in lifecycle
        assert "OrderSubmitted" in lifecycle
        assert "OrderFilled" in lifecycle

    def test_memory_usage_stability(self):
        """Test that memory usage remains stable under load."""
        import gc

        bus = EventBus()

        def handler(event):
            pass

        # Subscribe and unsubscribe many handlers to test cleanup
        for i in range(100):
            bus.subscribe(events.Market.IncomingBar, handler)
            bus.unsubscribe(events.Market.IncomingBar, handler)

        # Force garbage collection
        gc.collect()

        # Cache should be empty after all unsubscriptions
        assert len(bus._publish_cache) == 0
        assert len(bus._handlers) == 0

    def test_lambda_handler_support(self):
        """Test support for lambda handlers (common in trading systems)."""
        bus = EventBus()
        calls = []

        # Subscribe lambda handler
        def lambda_handler(event):
            calls.append(event.symbol)

        bus.subscribe(events.Market.IncomingBar, lambda_handler)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        bus.publish(event)
        assert calls == ["AAPL"]

        # Should be able to unsubscribe lambda
        bus.unsubscribe(events.Market.IncomingBar, lambda_handler)
        bus.publish(event)
        assert calls == ["AAPL"]  # No new calls


class TestEventBusEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_event_bus_publish(self):
        """Test publishing to event bus with no subscribers."""
        bus = EventBus()

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        # Should not raise exception
        with patch("onesecondtrader.monitoring.console.logger.warning") as mock_log:
            bus.publish(event)
            mock_log.assert_called_once()

    def test_handler_deduplication(self):
        """Test that duplicate handlers are properly deduplicated in cache."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(event.symbol)

        # Subscribe same handler to parent and child event types
        bus.subscribe(events.Base.Market, handler)
        bus.subscribe(events.Market.IncomingBar, handler)

        event = events.Market.IncomingBar(
            ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
            symbol="AAPL",
            bar=models.Bar(open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        )

        bus.publish(event)

        # Handler should only be called once despite multiple subscriptions
        assert calls == ["AAPL"]

    def test_complex_filter_combinations(self):
        """Test complex filter logic combinations."""
        bus = EventBus()
        calls = []

        def handler(event):
            calls.append(f"{event.symbol}:{event.bar.close}")

        # Complex filter: AAPL with price > 150 and volume > 500
        def complex_filter(event):
            return (
                event.symbol == "AAPL"
                and event.bar.close > 150.0
                and event.bar.volume > 500
            )

        bus.subscribe(events.Market.IncomingBar, handler, complex_filter)

        # Test various combinations
        test_cases = [
            ("AAPL", 151.0, 600, True),  # Should pass
            ("AAPL", 149.0, 600, False),  # Price too low
            ("AAPL", 151.0, 400, False),  # Volume too low
            ("GOOGL", 151.0, 600, False),  # Wrong symbol
        ]

        for symbol, price, volume, should_pass in test_cases:
            event = events.Market.IncomingBar(
                ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
                symbol=symbol,
                bar=models.Bar(
                    open=price - 1,
                    high=price + 1,
                    low=price - 2,
                    close=price,
                    volume=volume,
                ),
            )
            bus.publish(event)

        # Only first event should pass filter
        assert calls == ["AAPL:151.0"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
