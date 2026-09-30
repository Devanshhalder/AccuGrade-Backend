import httpx
import os
import mimetypes


ML_API_URL = "https://accugrade-ml-production.up.railway.app/evaluate"


async def evaluate_with_ml(
    image_path: str,
    question: str,
    answer_key: str,
    max_marks: float,
):
    extension = os.path.splitext(image_path)[1].lower()

    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    mime_type = mime_types.get(
        extension,
        mimetypes.guess_type(image_path)[0] or "application/octet-stream"
    )

    filename = os.path.basename(image_path)

    with open(image_path, "rb") as image_file:

        files = {
            "image": (
                filename,
                image_file,
                mime_type,
            )
        }

        data = {
            "question": question,
            "answer_key": answer_key,
            "max_marks": str(max_marks),
        }

        async with httpx.AsyncClient(timeout=120.0) as client:

            response = await client.post(
                ML_API_URL,
                files=files,
                data=data,
            )

            response.raise_for_status()

            return response.json()