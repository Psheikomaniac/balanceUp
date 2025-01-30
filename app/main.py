from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Session, select
from sqlalchemy.orm import joinedload
from app.database import engine, get_db
from app.routers import (
    teams_router as teams,
    users_router as users,
    penalties_router as penalties,
    imports_router as imports
)
from app.models import Team, User, Penalty, UserRead
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

app = FastAPI()

# Initialize database
SQLModel.metadata.create_all(engine)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(teams, prefix="/teams", tags=["teams"])
app.include_router(users, prefix="/users", tags=["users"])
app.include_router(penalties, prefix="/penalties", tags=["penalties"])
app.include_router(imports, prefix="/import", tags=["imports"])

@app.exception_handler(Exception)
async def handle_exceptions(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": str(exc)},
        status_code=500
    )

@app.get("/", include_in_schema=False)
async def overview(request: Request, db: Session = Depends(get_db)):
    try:
        # Fixed query with unique() and proper relationship loading
        stmt = select(User).options(joinedload(User.penalties)).order_by(User.full_name)
        result = db.exec(stmt)
        db_users = result.unique().all()  # Add unique() to deduplicate results

        users = []
        total_open = 0
        total_open_sum = 0.0
        total_paid = 0
        total_paid_sum = 0.0

        for db_user in db_users:
            # Access penalties through relationship
            penalties = db_user.penalties if db_user.penalties else []
            
            # Convert Decimal to float safely
            unpaid = [p for p in penalties if not p.paid_date and float(p.amount) > 0]
            paid = [p for p in penalties if p.paid_date]
            credits = [p for p in penalties if float(p.amount) < 0]

            total_debt = sum(float(p.amount) for p in unpaid)
            total_credit = abs(sum(float(p.amount) for p in credits))
            balance = total_debt - total_credit

            # Update global totals
            total_open += len(unpaid)
            total_open_sum += total_debt
            total_paid += len(paid)
            total_paid_sum += sum(float(p.amount) for p in paid)

            users.append(UserRead(
                **db_user.dict(),
                total_debt=round(total_debt, 2),
                total_credit=round(total_credit, 2),
                balance=round(balance, 2)
            ))

        return templates.TemplateResponse("overview.html", {
            "request": request,
            "users": users,
            "total_open": total_open,
            "total_open_sum": round(total_open_sum, 2),
            "total_paid": total_paid,
            "total_paid_sum": round(total_paid_sum, 2)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))