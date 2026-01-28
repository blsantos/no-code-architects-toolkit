"""
Route for fast video conversion (WebM to MP4)
Endpoint: POST /v1/video/convert
"""

from flask import Blueprint
from services.v1.video.convert import process_convert_video

v1_video_convert_bp = Blueprint('v1_video_convert', __name__, url_prefix='/v1/video/convert')

@v1_video_convert_bp.route('', methods=['POST'])
def convert_video_route(job_id, data):
    """
    Fast video conversion from WebM to MP4
    No trimming - just format/codec conversion

    Request body:
    {
        "video_url": "https://..."  // Required: URL of video to convert
    }

    Returns:
    {
        "output_url": "https://...",
        "job_id": "...",
        "format": "mp4",
        "codec": "h264"
    }
    """
    return process_convert_video(job_id, data)
