from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.database import crud, models, schemas
from app.errors.exceptions import InsufficientFundsError, PaymentError

class FinancialService:
    def __init__(self, db: Session):
        self.db = db

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

    def get_user_balance(self, user_id: str) -> Tuple[float, List[models.Penalty]]:
        """Get user's current balance and unpaid penalties."""
        unpaid_penalties = crud.get_user_penalties(self.db, user_id)
        unpaid_penalties = [p for p in unpaid_penalties if not p.paid]
        total_amount = sum(p.amount for p in unpaid_penalties)
        return total_amount, unpaid_penalties

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