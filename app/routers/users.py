from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from app.models import User, Penalty
from app.database import get_db
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/{user_id}", response_class=HTMLResponse)
async def user_detail(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Get user with penalties
        user = db.exec(
            select(User)
            .where(User.id == user_id)
            .options(joinedload(User.penalties))
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Process penalties
        all_penalties = user.penalties or []
        unpaid_penalties = [p for p in all_penalties if not p.paid_date and p.amount > 0]
        paid_penalties = [p for p in all_penalties if p.paid_date]
        credit_penalties = [p for p in all_penalties if p.amount < 0]

        # Calculate totals
        unpaid_total = round(sum(float(p.amount) for p in unpaid_penalties), 2)
        credit_balance = round(abs(sum(float(p.amount) for p in credit_penalties)), 2)
        paid_total = round(sum(float(p.amount) for p in paid_penalties), 2)

        return templates.TemplateResponse(
            "user_detail.html",
            {
                "request": request,
                "user": user,
                "unpaid_penalties": unpaid_penalties,
                "paid_penalties": paid_penalties,
                "unpaid_total": unpaid_total,
                "credit_balance": credit_balance,
                "paid_total": paid_total
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_class=HTMLResponse)
async def list_users(request: Request, db: Session = Depends(get_db)):
    try:
        users = db.exec(select(User).order_by(User.full_name)).all()
        return templates.TemplateResponse(
            "users.html",
            {"request": request, "users": users}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_class=HTMLResponse)
async def create_user(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        form_data = await request.form()
        user = User(
            full_name=form_data.get("full_name"),
            team_id=int(form_data.get("team_id"))
        )
        db.add(user)
        db.commit()
        return RedirectResponse(url="/users", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))