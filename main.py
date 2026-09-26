from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

import os
import tempfile
import json
import shutil
import uuid
import traceback


from database import (
    Base,
    engine,
    get_db,
)

from models import (
    User,
    EvaluationBatch,
    AnswerSheet,
    BatchEvaluator,
)

from auth import router as auth_router

from ml_client import evaluate_with_ml


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AccuGrade Backend",
    description=(
        "Backend API for the AccuGrade "
        "examination evaluation platform"
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://accu-grade-frontend.vercel.app",
],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

app.include_router(
    auth_router
)


# ============================================================
# UPLOAD STORAGE
# ============================================================

UPLOAD_DIR = "uploads"


os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ============================================================
# ADMIN — CREATE EVALUATION BATCH
# ============================================================

@app.post("/admin/batches")
async def create_evaluation_batch(

    batch_name: str = Form(...),

    subject: str = Form(...),

    examination: str = Form(...),

    max_marks: float = Form(...),

    evaluators: str = Form(...),

    ai_features: str = Form(...),

    answer_key: UploadFile = File(...),

    answer_sheets: list[UploadFile] = File(...),

    db: Session = Depends(get_db),

):

    batch = None

    try:

        # ====================================================
        # VALIDATE BASIC INPUT
        # ====================================================

        if not batch_name.strip():

            raise HTTPException(
                status_code=400,
                detail="Batch name is required."
            )


        if not subject.strip():

            raise HTTPException(
                status_code=400,
                detail="Subject is required."
            )


        if not examination.strip():

            raise HTTPException(
                status_code=400,
                detail="Examination is required."
            )


        if max_marks <= 0:

            raise HTTPException(
                status_code=400,
                detail="Maximum marks must be greater than zero."
            )


        if not answer_sheets:

            raise HTTPException(
                status_code=400,
                detail="At least one answer sheet is required."
            )


        # ====================================================
        # PARSE EVALUATORS
        # ====================================================

        try:

            evaluator_list = json.loads(
                evaluators
            )

        except Exception:

            evaluator_list = []


        if not isinstance(
            evaluator_list,
            list
        ):

            evaluator_list = []


        # ====================================================
        # PARSE AI FEATURES
        # ====================================================

        try:

            ai_config = json.loads(
                ai_features
            )

        except Exception:

            ai_config = {}


        if not isinstance(
            ai_config,
            dict
        ):

            ai_config = {}


        # ====================================================
        # CREATE DATABASE BATCH
        # ====================================================

        batch = EvaluationBatch(

            batch_name=batch_name.strip(),

            subject=subject.strip(),

            examination=examination.strip(),

            max_marks=max_marks,

            status="created",

            assisted_marking=bool(
                ai_config.get(
                    "assistedMarking",
                    True
                )
            ),

            unchecked_answers=bool(
                ai_config.get(
                    "uncheckedAnswers",
                    True
                )
            ),

            marking_anomalies=bool(
                ai_config.get(
                    "markingAnomalies",
                    True
                )
            ),

            unusual_scoring=bool(
                ai_config.get(
                    "unusualScoring",
                    True
                )
            ),

        )


        db.add(batch)

        db.flush()


        # ====================================================
        # CREATE BATCH DIRECTORY
        # ====================================================

        batch_directory = os.path.join(

            UPLOAD_DIR,

            f"batch_{batch.id}"

        )


        os.makedirs(

            batch_directory,

            exist_ok=True

        )


        # ====================================================
        # SAVE ANSWER KEY
        # ====================================================

        answer_key_extension = (

            os.path.splitext(
                answer_key.filename or ""
            )[1]

            or ".pdf"

        )


        answer_key_filename = (

            "answer_key_"

            + uuid.uuid4().hex

            + answer_key_extension

        )


        answer_key_path = os.path.join(

            batch_directory,

            answer_key_filename

        )


        with open(

            answer_key_path,

            "wb"

        ) as buffer:

            shutil.copyfileobj(

                answer_key.file,

                buffer

            )


        # ====================================================
        # SAVE STUDENT ANSWER SHEETS
        # ====================================================

        created_sheets = []


        for answer_sheet in answer_sheets:

            extension = (

                os.path.splitext(
                    answer_sheet.filename or ""
                )[1]

                or ".pdf"

            )


            stored_filename = (

                "sheet_"

                + uuid.uuid4().hex

                + extension

            )


            file_path = os.path.join(

                batch_directory,

                stored_filename

            )


            with open(

                file_path,

                "wb"

            ) as buffer:

                shutil.copyfileobj(

                    answer_sheet.file,

                    buffer

                )


            sheet = AnswerSheet(

                batch_id=batch.id,

                original_filename=(

                    answer_sheet.filename

                    or stored_filename

                ),

                stored_filename=stored_filename,

                file_path=file_path,

                status="uploaded",

            )


            db.add(sheet)

            created_sheets.append(sheet)


        # ====================================================
        # ASSIGN EVALUATORS
        # ====================================================

        for evaluator_name in evaluator_list:

            if not str(
                evaluator_name
            ).strip():

                continue


            evaluator = BatchEvaluator(

                batch_id=batch.id,

                evaluator_name=str(
                    evaluator_name
                ).strip(),

            )


            db.add(evaluator)


        # ====================================================
        # COMMIT DATABASE TRANSACTION
        # ====================================================

        db.commit()

        db.refresh(batch)


        # ====================================================
        # SUCCESS RESPONSE
        # ====================================================

        return {

            "message":
                "Evaluation batch created successfully",

            "batch_id":
                batch.id,

            "batch_name":
                batch.batch_name,

            "subject":
                batch.subject,

            "examination":
                batch.examination,

            "max_marks":
                batch.max_marks,

            "answer_sheets":
                len(created_sheets),

            "evaluators":
                len(evaluator_list),

            "status":
                batch.status,

        }


    except HTTPException:

        db.rollback()

        raise


    except Exception as error:

        db.rollback()


        # ----------------------------------------------------
        # Cleanup uploaded files if database creation fails
        # ----------------------------------------------------

        if batch is not None:

            batch_directory = os.path.join(

                UPLOAD_DIR,

                f"batch_{batch.id}"

            )


            if os.path.exists(
                batch_directory
            ):

                shutil.rmtree(
                    batch_directory,
                    ignore_errors=True
                )


        raise HTTPException(

            status_code=500,

            detail=str(error)

        )


# ============================================================
# SERVE UPLOADED ANSWER SHEETS
# ============================================================

@app.get("/answer-sheets/{sheet_id}")
def get_answer_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
):
    sheet = (
        db.query(AnswerSheet)
        .filter(AnswerSheet.id == sheet_id)
        .first()
    )

    if not sheet:
        raise HTTPException(
            status_code=404,
            detail="Answer sheet not found.",
        )

    if not sheet.file_path or not os.path.isfile(sheet.file_path):
        raise HTTPException(
            status_code=404,
            detail="Answer sheet file not found on server.",
        )

    import mimetypes

    media_type, _ = mimetypes.guess_type(
        sheet.file_path
    )

    return FileResponse(
        path=sheet.file_path,
        filename=(
            sheet.original_filename
            or sheet.stored_filename
        ),
        media_type=(
            media_type
            or "application/octet-stream"
        ),
    )


# ============================================================
# EVALUATOR — LIST ANSWER SHEETS
# ============================================================

@app.get("/evaluator/answer-sheets")
def get_evaluator_answer_sheets(
    db: Session = Depends(get_db),
):
    sheets = (
        db.query(
            AnswerSheet,
            EvaluationBatch
        )
        .join(
            EvaluationBatch,
            AnswerSheet.batch_id == EvaluationBatch.id
        )
        .order_by(
            AnswerSheet.id.desc()
        )
        .all()
    )

    return [
        {
            "sheet_id": sheet.id,
            "batch_id": batch.id,
            "batch_name": batch.batch_name,
            "subject": batch.subject,
            "examination": batch.examination,
            "max_marks": batch.max_marks,
            "filename": sheet.original_filename,
            "status": sheet.status,
            "file_url": f"/answer-sheets/{sheet.id}",
        }
        for sheet, batch in sheets
    ]


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {

        "service":
            "AccuGrade Backend",

        "status":
            "running",

    }


# ============================================================
# ANSWER EVALUATION
# ============================================================

@app.post("/evaluate")
async def evaluate(

    image: UploadFile = File(...),

    question: str = Form(...),

    answer_key: str = Form(...),

    max_marks: float = Form(...),

):

    suffix = (

        os.path.splitext(
            image.filename or ".jpg"
        )[1]

        or ".jpg"

    )


    temp_path = None


    try:

        # ----------------------------------------------------
        # Save uploaded answer-sheet image
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(

            delete=False,

            suffix=suffix,

        ) as temp_file:

            temp_file.write(

                await image.read()

            )

            temp_path = temp_file.name


        # ----------------------------------------------------
        # Send answer sheet to ML service
        # ----------------------------------------------------

        result = await evaluate_with_ml(

            image_path=temp_path,

            question=question,

            answer_key=answer_key,

            max_marks=max_marks,

        )


        # ----------------------------------------------------
        # Return evaluation result
        # ----------------------------------------------------

        return {

            "message":
                "Answer evaluated successfully",

            "evaluation":
                result,

        }


    except HTTPException:

        raise


    except Exception as error:

        print(
            "\n================ AI EVALUATION ERROR ================"
        )

        traceback.print_exc()

        print(
            "=======================================================\n"
        )

        error_message = str(error)

        # ----------------------------------------------------
        # Gemini quota / rate-limit error
        # ----------------------------------------------------

        if (
            "429" in error_message
            or "RESOURCE_EXHAUSTED" in error_message
        ):

            raise HTTPException(

                status_code=429,

                detail=(
                    "AI evaluation quota is "
                    "temporarily unavailable. "
                    "Please try again later."
                ),

            )


        # ----------------------------------------------------
        # Other errors
        # ----------------------------------------------------

        raise HTTPException(

            status_code=500,

            detail=error_message,

        )


    finally:

        # ----------------------------------------------------
        # Delete temporary evaluation file
        # ----------------------------------------------------

        if (

            temp_path

            and

            os.path.exists(
                temp_path
            )

        ):

            os.remove(
                temp_path
            )