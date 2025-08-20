from .models import DomainModel

# Convenience aliases for domain models
MarketData = DomainModel.MarketData
PositionManagement = DomainModel.PositionManagement
SystemManagement = DomainModel.SystemManagement

__all__ = [
    "DomainModel",
    "MarketData",
    "PositionManagement",
    "SystemManagement",
]
