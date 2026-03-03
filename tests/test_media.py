import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from application import routes



async def test_upload_media(
    client: AsyncClient, test_session: AsyncSession, tmp_path, monkeypatch
):
    test_media_dir = tmp_path / "test_media"
    test_media_dir.mkdir()
    monkeypatch.setattr(routes, "MEDIA_DIR", str(test_media_dir))

    file_content = b"fake-image-content"
    file = io.BytesIO(file_content)

    files = {"file": ("test_image.jpg", file, "image/jpeg")}
    headers = {"api-key": "test"}

    response = await client.post("/api/medias", files=files, headers=headers)
    answer = response.json()
    created_files = list(test_media_dir.iterdir())

    assert len(created_files) == 1
    assert created_files[0].suffix == ".jpg"
    assert response.status_code == 200
    assert isinstance(answer["media_id"], int)
