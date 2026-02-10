"""
Dummy meter data generator for development and testing.
Provides a simple generator function that yields fake readings.
"""
from typing import Iterator
from dataclasses import dataclass
import datetime
import random


@dataclass
class MeterReading:
    timestamp: datetime.datetime
    watts: float


def generate_readings(start: datetime.datetime, count: int) -> Iterator[MeterReading]:
    """Yield `count` fake meter readings spaced 15 seconds apart (placeholder)."""
    for i in range(count):
        yield MeterReading(timestamp=start + datetime.timedelta(seconds=15 * i), watts=random.random() * 1000)


if __name__ == "__main__":
    # Quick smoke run
    for r in generate_readings(datetime.datetime.utcnow(), 5):
        print(r)

