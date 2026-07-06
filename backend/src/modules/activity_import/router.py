"""Activity import API routes."""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.core.auth import CurrentUser
from src.core.responses import error_json, success_json
from src.modules.activity_import.deps import get_ingestion_service
from src.modules.activity_import.schemas import ImportFitResponse
from src.modules.activity_import.service import ActivityIngestionService

router = APIRouter(tags=["activity-import"])


@router.post("/api/activities/import/fit")
async def import_fit_activity(
    user: CurrentUser,
    athlete_id: int = Form(...),
    file: UploadFile = File(...),
    service: ActivityIngestionService = Depends(get_ingestion_service),
):
    if athlete_id != user.id:
        raise error_json(403, "You can only import activities for your own account")

    file_bytes = await file.read()
    filename = file.filename or "upload.fit"

    activity_import, err, status = service.ingest_fit_upload(
        file_bytes=file_bytes,
        filename=filename,
        athlete_id=athlete_id,
    )
    if err:
        raise error_json(status, err)

    response = ImportFitResponse(
        job_id=str(activity_import.id),
        status=activity_import.status,
    )
    return success_json(response.model_dump(by_alias=True), status_code=status)
