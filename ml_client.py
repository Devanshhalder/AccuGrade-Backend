import httpx


ML_API_URL = "http://127.0.0.1:8001/evaluate"


async def evaluate_with_ml(
    image_path: str,
    question: str,
    answer_key: str,
    max_marks: float,
):
    with open(image_path, "rb") as image_file:

        files = {
            "image": (
                "answer.jpg",
                image_file,
                "image/jpeg",
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