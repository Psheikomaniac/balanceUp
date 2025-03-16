from app.database.models import Penalty, init_db
from sqlalchemy.orm import Session
import uuid

def add_guids_to_penalties():
    engine = init_db()
    with Session(engine) as session:
        penalties = session.query(Penalty).all()
        for penalty in penalties:
            penalty.penalty_id = str(uuid.uuid4())
        session.commit()

if __name__ == "__main__":
    add_guids_to_penalties()
    print("Die Spalte 'penalty_id' wurde erfolgreich hinzugefügt und mit GUIDs gefüllt.")
