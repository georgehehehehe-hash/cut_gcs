import io
import uuid
import requests
from fastapi import FastAPI, HTTPException
from PIL import Image
from google.cloud import storage
import os

app = FastAPI()

# 环境变量（Cloud Run 里配置）
GCS_BUCKET = os.environ.get("GCS_BUCKET")
GRID_SIZE = 6  # 6x6 = 36 张

if not GCS_BUCKET:
    raise RuntimeError("GCS_BUCKET env not set")


@app.post("/crop")
def crop_image(payload: dict):
    image_url = payload.get("image_url")
    if not image_url:
        raise HTTPException(400, "image_url is required")

    # 下载图片
    resp = requests.get(image_url, timeout=20)
    if resp.status_code != 200:
        raise HTTPException(400, "failed to download image")

    img = Image.open(io.BytesIO(resp.content)).convert("RGB")

    width, height = img.size
    tile_w = width // GRID_SIZE
    tile_h = height // GRID_SIZE

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)

    results = []
    batch_id = uuid.uuid4().hex

    index = 1
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            left = col * tile_w
            top = row * tile_h
            right = left + tile_w
            bottom = top + tile_h

            cropped = img.crop((left, top, right, bottom))

            buf = io.BytesIO()
            cropped.save(buf, format="JPEG", quality=95)
            buf.seek(0)

            filename = f"crop/{batch_id}/{index}.jpg"
            blob = bucket.blob(filename)
            blob.upload_from_file(buf, content_type="image/jpeg")

            results.append(
                f"https://storage.googleapis.com/{GCS_BUCKET}/{filename}"
            )
            index += 1

    return {
        "count": len(results),
        "images": results
    }
