import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.tweet import Tweet, TweetStatus
from app.paths import HOME_ROOT, images_dir

router = APIRouter(prefix="/images", tags=["images"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024
EXT_MAP = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}


@router.post("/upload")
async def upload_image(
    tweet_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    tweet = db.query(Tweet).filter(
        Tweet.id == tweet_id,
        Tweet.status.in_([TweetStatus.queued, TweetStatus.scheduled]),
    ).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="JPEG / PNG / GIF / WEBP のみ対応しています")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="ファイルサイズは5MB以内にしてください")

    user_images_dir = images_dir(user)
    user_images_dir.mkdir(parents=True, exist_ok=True)

    if tweet.image_path:
        Path(tweet.image_path).unlink(missing_ok=True)

    ext = EXT_MAP.get(file.content_type, ".jpg")
    filename = f"{uuid.uuid4().hex}{ext}"
    image_path = str(user_images_dir / filename)

    with open(image_path, "wb") as f:
        f.write(content)

    tweet.image_path = image_path
    db.commit()

    return {
        "image_path": image_path,
        "preview_url": f"/xpost/api/images/preview/{filename}",
    }


@router.delete("/{tweet_id}")
def delete_image(tweet_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="ツイートが見つかりません")
    if tweet.image_path:
        Path(tweet.image_path).unlink(missing_ok=True)
        tweet.image_path = None
        db.commit()
    return {"ok": True}


@router.get("/preview/{filename}")
def preview_image(filename: str):
    filename = Path(filename).name  # パストラバーサル防止
    # プレビューは <img src> から直接読み込まれるため認証ヘッダーを付けられず、
    # 未認証のまま提供している（filenameはuuid4なので実質推測不可能）。
    # user_idがURLに含まれないため、全ユーザーのimages/を探索して見つける。
    for candidate in HOME_ROOT.glob(f"*/xpost/images/{filename}"):
        if candidate.is_file():
            return FileResponse(str(candidate))
    raise HTTPException(status_code=404, detail="画像が見つかりません")
