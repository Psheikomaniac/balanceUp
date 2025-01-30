import csv
from datetime import datetime
from io import StringIO
from sqlmodel import Session
from app.models import Team, User, Penalty

async def import_penalties(csv_data: str, team_id: int, db: Session):
    reader = csv.DictReader(StringIO(csv_data), delimiter=';')
    
    # Get or create team
    team = db.get(Team, team_id)
    if not team:
        team = Team(team_id=team_id, name="HSG WBW Herren 2")
        db.add(team)
        db.commit()
        db.refresh(team)
    
    for row in reader:
        # Get or create user
        user = db.query(User).filter_by(
            full_name=row['penatly_user'].strip(),
            team_id=team_id
        ).first()
        
        if not user:
            user = User(
                full_name=row['penatly_user'].strip(),
                team_id=team_id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create penalty with euro conversion
        penalty = Penalty(
            created_date=datetime.strptime(row['penatly_created'], "%d-%m-%Y").date(),
            reason=row['penatly_reason'].strip(),
            archived=row['penatly_archived'].strip().upper() == "YES",
            amount=float(row['penatly_amount']) / 100,  # Convert cents to euros
            currency=row['penatly_currency'].strip(),
            user_id=user.id,
            team_id=team_id
        )
        db.add(penalty)
    
    db.commit()