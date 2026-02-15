import io

import pytest
from httpx import AsyncClient

from application import routes


@pytest.mark.asyncio
async def test_upload_media(client: AsyncClient, tmp_path, monkeypatch):
    test_media_dir = tmp_path / "test_media"
    test_media_dir.mkdir()
    monkeypatch.setattr(routes, "MEDIA_DIR", str(test_media_dir))

    file_content = b"fake-image-content"
    file = io.BytesIO(file_content)

    files = {"file": ("test_image.jpg", file, "image/jpeg")}
    headers = {"api-key": "test"}
    answer = {"media_id": 1}
    response = await client.post("/api/medias", files=files, headers=headers)
    created_files = list(test_media_dir.iterdir())

    assert len(created_files) == 1
    assert created_files[0].suffix == ".jpg"
    assert response.status_code == 200
    assert response.json() == answer
