import io
from typing import BinaryIO

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_upload_media(client: AsyncClient):
    file_content = b"fake-image-content"
    file = io.BytesIO(file_content)

    files = {"file": ("test_image.jpg", file, "image/jpeg")}
    headers = {"api-key": "test"}
    answer = {"media_id": 1}
    response = await client.post("/api/medias", files=files, headers=headers)

    assert response.status_code == 200
    assert response.json() == answer