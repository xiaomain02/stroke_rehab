async def seed_media(session, patients):
    import os

    if os.environ.get("SEED_SKIP_S3", "").lower() in ("1", "true", "yes"):
        print("    [skip] seed_media (SEED_SKIP_S3=1)")
        return

    if await session.scalar(select(MediaFile.id).limit(1)) is not None:
        return
    attempt = await session.scalar(select(Attempt).limit(1))
    if attempt is None:
        return

    from app.services import storage
    storage.ensure_bucket()  # проверка, что бакет есть

    for i in range(3):
        key = f"seed/audio/{uuid.uuid4()}.webm"
        size = storage.put_dummy(key, media_type="audio")
        session.add(
            MediaFile(
                uploaded_by=patients[0].id,
                attempt_id=attempt.id,
                media_type="audio",
                storage_key=key,
                original_name=f"answer_{i}.webm",
                mime_type="audio/webm",
                size_bytes=size,
                duration_ms=random.randint(5_000, 30_000),
                status="ready",
            )
        )
    await session.flush()