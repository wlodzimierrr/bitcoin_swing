"""Synthetic owner code for the RBT-002 R2 nested-callable census tests.

Loaded by ``test_research_backtest_coverage_nested`` under an in-scope module
name. It is never an owner and holds no market data. Each local callable
exercises one ``OWNER_INTERNAL``/``EXTERNAL`` rule of
``input_census._classify_nested``.
"""

import functools


def package_sorter(values, key):
    return sorted(values, key=key)


def nested_root(values, callback):
    def internal(reason, *, flag=True):
        return (reason, flag)

    def computed(value, scale=1):
        return value * scale

    def escapes(value):
        return value

    def unpacked(*items):
        return items

    @functools.cache
    def decorated(value):
        return value

    def rebound(value):
        return value

    rebound = escapes

    def wrapper(items):
        return sorted(items, key=lambda item: -item)

    class Local:
        def method(self):
            return 1

    assigned = lambda item: item  # noqa: E731 - a lambda bound to a local name
    local_value = len(values)
    labels = (internal("A"), internal("B", flag=False), internal("C", flag=local_value))
    return (
        labels,
        computed(local_value + 1),
        sorted(values, key=lambda item: item),
        package_sorter(values, key=lambda item: -item),
        sum(item for item in values),
        [sum(step for step in range(item)) for item in values],
        [assigned(1) for _ in values],
        unpacked(*values),
        decorated(1),
        rebound(2),
        wrapper(values),
        Local().method(),
        callback(escapes),
    )
