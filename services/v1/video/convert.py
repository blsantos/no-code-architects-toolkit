"""
Video conversion service - Simple WebM to MP4 conversion without trimming
Fast conversion for short videos (< 1 minute)
"""

import os
import subprocess
import logging
from services.file_management import download_file
from services.cloud_storage import upload_file
from config import LOCAL_STORAGE_PATH

logger = logging.getLogger(__name__)

def process_convert_video(job_id, data):
    """
    Convert video from WebM to MP4 without trimming
    Much faster than trim endpoint for short videos

    Args:
        job_id: Unique job identifier
        data: {
            "video_url": "https://...",  # Required: URL of video to convert
            "force_audio": bool,          # Optional: Force silent audio track if missing (default: False)
        }

    Returns:
        (result, endpoint, status_code)
    """
    try:
        video_url = data.get('video_url')
        force_audio = data.get('force_audio', False)  # Default: False for backward compatibility

        if not video_url:
            return "Missing video_url parameter", "/v1/video/convert", 400

        # Download the input video
        logger.info(f"Job {job_id}: Downloading video from {video_url}")
        input_file = download_file(video_url, job_id)

        if not input_file or not os.path.exists(input_file):
            return "Failed to download video", "/v1/video/convert", 500

        # Force MP4 output for H.264
        output_filename = os.path.join(LOCAL_STORAGE_PATH, f"{job_id}_output.mp4")

        # Detect if input has audio stream
        has_audio = False
        if force_audio:
            try:
                # Use ffprobe to detect audio streams
                probe_command = [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_streams',
                    '-select_streams', 'a',  # Select only audio streams
                    input_file
                ]
                probe_result = subprocess.run(
                    probe_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                import json
                probe_data = json.loads(probe_result.stdout)
                has_audio = len(probe_data.get('streams', [])) > 0
                logger.info(f"Job {job_id}: Input video has audio: {has_audio}")
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to probe audio streams, assuming no audio: {e}")
                has_audio = False

        # Build FFmpeg command based on audio detection
        if force_audio and not has_audio:
            # Generate silent audio track for videos without audio (Facebook Stories compatibility)
            logger.info(f"Job {job_id}: Adding silent audio track (AAC 48kHz stereo) for Facebook Stories compatibility")
            ffmpeg_command = [
                'ffmpeg',
                '-i', input_file,
                '-f', 'lavfi',
                '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000',  # Silent audio source
                '-c:v', 'libx264',      # H.264 codec
                '-preset', 'fast',       # Faster encoding
                '-crf', '23',            # Quality (18-28 range, 23 is good)
                '-c:a', 'aac',           # AAC audio codec
                '-b:a', '128k',          # 128kbps audio bitrate
                '-ar', '48000',          # 48kHz sample rate
                '-ac', '2',              # Stereo
                '-shortest',             # Match audio duration to video duration
                '-pix_fmt', 'yuv420p',   # 4:2:0 chroma subsampling
                '-movflags', '+faststart', # Moov atom at front for web streaming
                '-y',                    # Overwrite output
                output_filename
            ]
        else:
            # Normal conversion (with existing audio or no audio injection)
            ffmpeg_command = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', 'libx264',      # H.264 codec
                '-preset', 'fast',       # Faster encoding
                '-crf', '23',            # Quality (18-28 range, 23 is good)
                '-c:a', 'aac',           # AAC audio
                '-b:a', '128k',          # 128kbps audio
                '-ar', '48000',          # 48kHz sample rate
                '-ac', '2',              # Stereo
                '-pix_fmt', 'yuv420p',   # 4:2:0 chroma subsampling
                '-movflags', '+faststart', # Moov atom at front for web streaming
                '-y',                    # Overwrite output
                output_filename
            ]

        logger.info(f"Job {job_id}: Converting to MP4 (fast preset)")
        result = subprocess.run(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            error_msg = f"FFmpeg error: {result.stderr}"
            logger.error(f"Job {job_id}: {error_msg}")
            # Clean up
            if os.path.exists(input_file):
                os.remove(input_file)
            return error_msg, "/v1/video/convert", 500

        # Upload to storage
        logger.info(f"Job {job_id}: Uploading converted video to storage")
        output_url = upload_file(output_filename)

        # Clean up local files
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_filename):
            os.remove(output_filename)

        logger.info(f"Job {job_id}: Conversion complete, output URL: {output_url}")

        result_data = {
            "output_url": output_url,
            "job_id": job_id,
            "format": "mp4",
            "codec": "h264"
        }

        # Add metadata if silent audio was injected
        if force_audio and not has_audio:
            result_data["silent_audio_added"] = True
            logger.info(f"Job {job_id}: Silent audio track was added for Facebook Stories compatibility")

        return result_data, "/v1/video/convert", 200

    except Exception as e:
        logger.error(f"Job {job_id}: Error in process_convert_video: {str(e)}")
        return str(e), "/v1/video/convert", 500
