from database import SessionLocal
from models import AnswerSheet

db = SessionLocal()

try:
    sheets = db.query(AnswerSheet).order_by(AnswerSheet.id.desc()).all()

    print("\nALL ANSWER SHEETS:\n")

    for sheet in sheets:
        print(
            f"ID: {sheet.id} | "
            f"Batch ID: {sheet.batch_id} | "
            f"Filename: {sheet.original_filename} | "
            f"Student: {sheet.student_identifier} | "
            f"Status: {sheet.status}"
        )

finally:
    db.close()