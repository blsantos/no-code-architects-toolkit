"""
Route for fast video conversion (WebM to MP4)
Endpoint: POST /v1/video/convert
"""

from flask import Blueprint
from app_utils import *
import logging
from services.v1.video.convert import process_convert_video
from services.authentication import authenticate

v1_video_convert_bp = Blueprint('v1_video_convert', __name__)
logger = logging.getLogger(__name__)

@v1_video_convert_bp.route('/v1/video/convert', methods=['POST'])
@authenticate
@validate_payload({
    "type": "object",
    "properties": {
        "video_url": {"type": "string", "format": "uri"},
        "force_audio": {"type": "boolean"}  # Optional: Force silent audio track if missing
    },
    "required": ["video_url"],
    "additionalProperties": False
})
@queue_task_wrapper(bypass_queue=False)
def convert_video_route(job_id, data):
    """
    Fast video conversion from WebM to MP4
    No trimming - just format/codec conversion
    Optionally adds silent audio track for Facebook Stories compatibility

    Request body:
    {
        "video_url": "https://...",        // Required: URL of video to convert
        "force_audio": true                // Optional: Add silent audio if missing (default: false)
    }

    Returns:
    {
        "output_url": "https://...",
        "job_id": "...",
        "format": "mp4",
        "codec": "h264",
        "silent_audio_added": true         // Present if silent audio was added
    }
    """
    logger.info(f"Job {job_id}: Received video convert request for {data['video_url']}")
    return process_convert_video(job_id, data)
