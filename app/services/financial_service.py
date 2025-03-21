from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import crud, models, schemas
from app.errors.exceptions import (
    InsufficientFundsError,
    PaymentError,
    ResourceNotFoundException,
    DatabaseError
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class FinancialService:
    def __init__(self, db: Session):
        self.db = db

    def create_penalty(self, penalty_data: schemas.PenaltyCreate) -> models.Penalty:
        """Create a new penalty with validation"""
        try:
            # Verify user exists
            user = crud.get_user(self.db, penalty_data.user_id)
            if not user:
                raise ResourceNotFoundException(f"User {penalty_data.user_id} not found")

            return crud.create_penalty(self.db, penalty_data)
        except SQLAlchemyError as e:
            logger.error(f"Error creating penalty: {str(e)}")
            raise DatabaseError("Failed to create penalty", {"original_error": str(e)})

    def pay_penalty(self, penalty_id: str) -> Tuple[models.Penalty, models.Transaction]:
        """Process penalty payment with transaction management"""
        try:
            penalty = crud.get_penalty(self.db, penalty_id)
            if not penalty:
                raise ResourceNotFoundException(f"Penalty {penalty_id} not found")

            if penalty.paid:
                raise PaymentError("Penalty already paid", 
                    {"penalty_id": penalty_id, "paid_at": penalty.paid_at})

            # Create transaction record
            transaction = crud.create_transaction(
                self.db,
                schemas.TransactionCreate(
                    user_id=penalty.user_id,
                    amount=penalty.amount,
                    description=f"Payment for penalty: {penalty.reason or penalty_id}"
                )
            )

            # Mark penalty as paid
            penalty = crud.mark_penalty_as_paid(self.db, penalty_id)

            return penalty, transaction
        except SQLAlchemyError as e:
            logger.error(f"Error processing penalty payment: {str(e)}")
            raise DatabaseError("Failed to process payment", {"original_error": str(e)})

    def process_payment(self, user_id: str, amount: float, description: Optional[str] = None) -> models.Transaction:
        """Process a payment from a user."""
        # Get unpaid penalties
        unpaid_penalties = crud.get_user_penalties(
            self.db,
            user_id=user_id,
            skip=0,
            limit=100
        )
        unpaid_penalties = [p for p in unpaid_penalties if not p.paid]
        
        if not unpaid_penalties:
            raise PaymentError("No unpaid penalties found for this user")

        remaining_amount = amount
        paid_penalties = []

        # Process penalties in order (FIFO)
        for penalty in sorted(unpaid_penalties, key=lambda x: x.date):
            if remaining_amount <= 0:
                break

            if remaining_amount >= penalty.amount:
                crud.mark_penalty_paid(self.db, penalty.penalty_id)
                remaining_amount -= penalty.amount
                paid_penalties.append(penalty)
            
        if not paid_penalties:
            raise InsufficientFundsError("Payment amount too small for any penalties")

        # Create transaction record
        transaction = crud.create_transaction(
            self.db,
            schemas.TransactionCreate(
                user_id=user_id,
                amount=amount,
                description=description or f"Payment for {len(paid_penalties)} penalties"
            )
        )

        # Create audit log
        crud.create_audit_log(
            self.db,
            schemas.AuditLogCreate(
                action="payment_processed",
                entity_type="transaction",
                entity_id=transaction.transaction_id,
                user_id=user_id,
                details=f"Paid {len(paid_penalties)} penalties, total amount: {amount}"
            )
        )

        return transaction

    def get_user_balance(self, user_id: str) -> schemas.UserBalance:
        """Get user's current balance with detailed calculations"""
        try:
            user = crud.get_user(self.db, user_id)
            if not user:
                raise ResourceNotFoundException(f"User {user_id} not found")

            total_unpaid = crud.get_user_balance(self.db, user_id)

            return schemas.UserBalance(
                user_id=user_id,
                total_unpaid=total_unpaid
            )
        except SQLAlchemyError as e:
            logger.error(f"Error calculating user balance: {str(e)}")
            raise DatabaseError("Failed to calculate balance", {"original_error": str(e)})

    def get_payment_summary(self, user_id: str) -> dict:
        """Get payment summary for a user."""
        penalties = crud.get_user_penalties(self.db, user_id)
        transactions = crud.get_user_transactions(self.db, user_id)

        total_penalties = sum(p.amount for p in penalties)
        paid_penalties = sum(p.amount for p in penalties if p.paid)
        total_payments = sum(t.amount for t in transactions)

        return {
            "total_penalties": total_penalties,
            "paid_penalties": paid_penalties,
            "unpaid_penalties": total_penalties - paid_penalties,
            "total_payments": total_payments,
            "last_payment_date": max((t.transaction_date for t in transactions), default=None) if transactions else None
        }

    def refund_payment(self, transaction_id: str, reason: str) -> models.Transaction:
        """Process a refund for a payment."""
        original_transaction = crud.get_transaction(self.db, transaction_id)
        if not original_transaction:
            raise PaymentError("Original transaction not found")

        # Create refund transaction
        refund = crud.create_transaction(
            self.db,
            schemas.TransactionCreate(
                user_id=original_transaction.user_id,
                amount=-original_transaction.amount,
                description=f"Refund: {reason}"
            )
        )

        # Create audit log
        crud.create_audit_log(
            self.db,
            schemas.AuditLogCreate(
                action="payment_refunded",
                entity_type="transaction",
                entity_id=refund.transaction_id,
                user_id=original_transaction.user_id,
                details=f"Refunded transaction {transaction_id}: {reason}"
            )
        )

        return refund

    def get_penalties_summary(self) -> schemas.PenaltySummary:
        """Get summary of all penalties"""
        try:
            summary = crud.get_penalties_summary(self.db)
            return schemas.PenaltySummary(**summary)
        except SQLAlchemyError as e:
            logger.error(f"Error getting penalties summary: {str(e)}")
            raise DatabaseError("Failed to get penalties summary", {"original_error": str(e)})

    def get_user_penalties_summary(self, user_id: str) -> schemas.PenaltySummary:
        """Get summary of user's penalties"""
        try:
            return crud.get_user_penalties_summary(self.db, user_id)
        except ResourceNotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error getting user penalties summary: {str(e)}")
            raise DatabaseError("Failed to get user penalties summary", {"original_error": str(e)})

    def process_bulk_payment(self, user_id: str, amount: float) -> List[models.Penalty]:
        """Process bulk payment for user's penalties"""
        try:
            user = crud.get_user(self.db, user_id)
            if not user:
                raise ResourceNotFoundException(f"User {user_id} not found")

            # Get unpaid penalties ordered by date
            unpaid_penalties = crud.get_user_penalties(self.db, user_id, include_paid=False)
            if not unpaid_penalties:
                raise PaymentError("No unpaid penalties found", {"user_id": user_id})

            total_unpaid = sum(p.amount for p in unpaid_penalties)
            if amount < total_unpaid:
                raise InsufficientFundsError(
                    "Insufficient payment amount",
                    {
                        "required": total_unpaid,
                        "provided": amount,
                        "missing": total_unpaid - amount
                    }
                )

            paid_penalties = []
            remaining_amount = amount

            # Process penalties in order
            for penalty in sorted(unpaid_penalties, key=lambda p: p.date):
                if remaining_amount >= penalty.amount:
                    penalty, _ = self.pay_penalty(penalty.penalty_id)
                    paid_penalties.append(penalty)
                    remaining_amount -= penalty.amount

            return paid_penalties
        except SQLAlchemyError as e:
            logger.error(f"Error processing bulk payment: {str(e)}")
            raise DatabaseError("Failed to process bulk payment", {"original_error": str(e)})