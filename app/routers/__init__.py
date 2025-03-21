"""Router module initialization"""
# Import routers at usage time to avoid circular imports
from app.routers.users import router as users_router
from app.routers.penalties import router as penalties_router
from app.routers.transactions import router as transactions_router

__all__ = ['users_router', 'penalties_router', 'transactions_router']