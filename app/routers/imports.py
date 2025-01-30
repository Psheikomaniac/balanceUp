from fastapi import APIRouter, UploadFile, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app.services.csv_importer import import_penalties
from app.database import get_db
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def import_page(request: Request):
    return templates.TemplateResponse("import.html", {"request": request})

@router.post("/{team_id}", response_class=HTMLResponse)
async def import_penalties_file(
    team_id: int,
    file: UploadFile,
    request: Request,
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, detail="Invalid file type")
    
    contents = await file.read()
    csv_data = contents.decode("utf-8")
    
    try:
        await import_penalties(csv_data, team_id, db)
        return templates.TemplateResponse(
            "import.html",
            {
                "request": request,
                "message": f"Successfully imported {csv_data.count(chr(10))-1} penalties"
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "import.html",
            {
                "request": request,
                "error": f"Import failed: {str(e)}"
            },
            status_code=400
        )