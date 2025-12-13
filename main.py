import os
import uuid
import datetime
import cv2
import numpy as np
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import storage

# --- 配置 ---
# 【请修改】这里填你第一步创建的 Bucket 名字
# BUCKET_NAME = "你的-bucket-名字-填在这里"

# --- 配置 ---
try:
    BUCKET_NAME = os.environ['GCS_BUCKET_NAME']
except KeyError:
    raise Exception("GCS_BUCKET_NAME environment variable not set. Deployment failed.")

app = FastAPI(title="Grid Splitter Service")

# 初始化 GCS 客户端 (Cloud Run 环境下会自动通过内网获取认证)
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


class ImageRequest(BaseModel):
    url: str


def process_and_upload(image_bytes: bytes):
    """
    核心处理流：内存解码 -> 切割 -> 内存上传 -> 返回URL
    """
    # 1. 解码图片
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法解析图片数据，请检查链接是否为有效图片")

    # 2. 预处理 (二值化找轮廓)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 3. 筛选 9:16 的矩形
    valid_crops = []
    h_img, w_img = img.shape[:2]
    img_area = w_img * h_img

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / float(h)
        area = w * h
        # 宽松判定：面积 > 千分之一，长宽比 0.4~0.8 (标准9:16是0.56)
        if area > (img_area * 0.001) and 0.4 < aspect < 0.8:
            valid_crops.append((x, y, w, h))

    if not valid_crops:
        raise ValueError("未检测到符合 9:16 比例的子图")

    # 4. 智能排序 (行优先，再列优先)
    # 先按 Y 排序
    valid_crops.sort(key=lambda r: r[1])

    sorted_crops = []
    row_group = []
    if valid_crops:
        last_y = valid_crops[0][1]
        # 同一行的判定容差：高度的一半
        tolerance = valid_crops[0][3] // 2

        for rect in valid_crops:
            x, y, w, h = rect
            if abs(y - last_y) > tolerance:
                # 结算上一行 (按 X 排序)
                row_group.sort(key=lambda r: r[0])
                sorted_crops.extend(row_group)
                row_group = []
                last_y = y
            row_group.append(rect)
        # 结算最后一行
        row_group.sort(key=lambda r: r[0])
        sorted_crops.extend(row_group)

    # 5. 切割并上传
    uploaded_urls = []
    # 生成批次ID，作为文件夹名
    batch_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:6]

    for idx, (x, y, w, h) in enumerate(sorted_crops):
        crop_img = img[y:y + h, x:x + w]

        # 编码回 JPG 格式
        success, encoded_img = cv2.imencode('.jpg', crop_img)
        if success:
            file_bytes = encoded_img.tobytes()
            # 设置云端路径: split_results/批次号/001.jpg
            blob_name = f"split_results/{batch_id}/{idx + 1:03d}.jpg"
            blob = bucket.blob(blob_name)

            # 上传 (因为我们在 Bucket 层级开了 public 权限，所以不用单独设 ACL)
            blob.upload_from_string(file_bytes, content_type='image/jpeg')

            # 拼接公开 URL
            public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
            uploaded_urls.append(public_url)

    return uploaded_urls


@app.post("/split", summary="切割并上传到 GCS")
async def split_handler(req: ImageRequest):
    # 1. 下载图片
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(req.url, timeout=45.0)  # 下载超时设长一点
            if resp.status_code != 200:
                raise HTTPException(400, f"源图片下载失败: HTTP {resp.status_code}")
            image_content = resp.content
    except Exception as e:
        raise HTTPException(400, f"网络请求错误: {str(e)}")

    # 2. 处理逻辑
    try:
        urls = process_and_upload(image_content)
        return {
            "status": "success",
            "batch_id": urls[0].split('/')[-2],  # 从URL中提取批次ID方便追踪
            "total_count": len(urls),
            "images": urls
        }
    except ValueError as ve:
        raise HTTPException(422, str(ve))
    except Exception as e:
        # 记录详细错误到 Cloud Logging
        print(f"Internal Error: {e}")
        raise HTTPException(500, "服务器内部处理错误")


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Grid Splitter"}
