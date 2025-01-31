from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlmodel import Session
from app.models import Penalty
from app.models import User
from app.database import get_db
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

@router.get("/new", response_class=HTMLResponse)
async def new_penalty_form(request: Request):
    return templates.TemplateResponse("penalty_form.html", {"request": request})

@router.post("/new")
async def create_penalty(
    request: Request,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    penalty = Penalty(
        reason=form_data["reason"],
        amount=float(form_data["amount"]),
        user_id=int(form_data["user_id"])
    )
    db.add(penalty)
    db.commit()
    return RedirectResponse(url=f"/users/{penalty.user_id}", status_code=303)

@router.get("/{penalty_id}/edit", response_class=HTMLResponse)
async def edit_penalty_form(
    request: Request,
    penalty_id: int,
    db: Session = Depends(get_db)
):
    penalty = db.get(Penalty, penalty_id)
    if not penalty:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("penalty_form.html", {
        "request": request,
        "penalty": penalty
    })

@router.get("/", response_class=HTMLResponse)
async def list_penalties(request: Request, db: Session = Depends(get_db)):
    try:
        # Get all penalties with user relationships
        penalties = db.exec(
            select(Penalty)
            .join(User)
            .options(joinedload(Penalty.user))
            .order_by(Penalty.created_date.desc())
        ).unique().all()

        return templates.TemplateResponse(
            "penalties.html",
            {"request": request, "penalties": penalties}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))