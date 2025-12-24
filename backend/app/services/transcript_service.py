"""Service for fetching YouTube video transcripts with Whisper fallback."""

import os
import tempfile
import subprocess
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
import openai
from app.config import settings


class TranscriptService:
    """
    Fetches video transcripts using youtube-transcript-api with Whisper fallback.

    Priority:
    1. Manual captions (human-created)
    2. Auto-generated captions
    3. Whisper transcription (fallback)
    """

    def __init__(self):
        self.openai_client = None
        if settings.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)

    def get_transcript(
        self,
        video_id: str,
        languages: list[str] = ["en"],
        use_whisper_fallback: bool = True,
    ) -> Optional[dict]:
        """
        Get transcript for a video, with optional Whisper fallback.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages in order
            use_whisper_fallback: Whether to use Whisper if no transcript found

        Returns:
            Dictionary with:
            - content: Full transcript text
            - segments: List of {start, end, text} segments
            - source: 'youtube_manual', 'youtube_auto', or 'whisper'
            - language: Detected language code
        """
        # Try YouTube transcripts first
        result = self._get_youtube_transcript(video_id, languages)
        if result:
            return result

        # Fall back to Whisper if enabled
        if use_whisper_fallback and self.openai_client:
            return self._get_whisper_transcript(video_id)

        return None

    def _get_youtube_transcript(
        self,
        video_id: str,
        languages: list[str],
    ) -> Optional[dict]:
        """
        Fetch transcript from YouTube.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages

        Returns:
            Transcript data or None
        """
        try:
            # Get list of available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            transcript = None
            source = "youtube_auto"

            # Try to find manual transcript first
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
                source = "youtube_manual"
            except NoTranscriptFound:
                # Fall back to auto-generated
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                    source = "youtube_auto"
                except NoTranscriptFound:
                    # Try any available transcript and translate
                    try:
                        available = list(transcript_list)
                        if available:
                            transcript = available[0]
                            if transcript.language_code not in languages:
                                transcript = transcript.translate(languages[0])
                            source = "youtube_auto"
                    except Exception:
                        return None

            if transcript is None:
                return None

            # Fetch the actual transcript data
            segments = transcript.fetch()

            # Build full text and segment list
            full_text = " ".join(seg["text"] for seg in segments)
            formatted_segments = [
                {
                    "start": seg["start"],
                    "end": seg["start"] + seg["duration"],
                    "text": seg["text"],
                }
                for seg in segments
            ]

            return {
                "content": full_text,
                "segments": formatted_segments,
                "source": source,
                "language": transcript.language_code,
                "word_count": len(full_text.split()),
            }

        except (TranscriptsDisabled, VideoUnavailable) as e:
            # Transcripts explicitly disabled or video unavailable
            return None
        except Exception as e:
            # Log and return None for any other errors
            print(f"Error fetching YouTube transcript: {e}")
            return None

    def _get_whisper_transcript(self, video_id: str) -> Optional[dict]:
        """
        Download audio and transcribe with Whisper.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript data or None
        """
        if not self.openai_client:
            return None

        audio_path = None
        try:
            # Download audio using yt-dlp
            audio_path = self._download_audio(video_id)
            if not audio_path:
                return None

            # Transcribe with Whisper
            with open(audio_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            # Format response
            segments = []
            if hasattr(response, "segments") and response.segments:
                segments = [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                    }
                    for seg in response.segments
                ]

            full_text = response.text

            return {
                "content": full_text,
                "segments": segments,
                "source": "whisper",
                "language": response.language or "en",
                "word_count": len(full_text.split()),
            }

        except Exception as e:
            print(f"Error with Whisper transcription: {e}")
            return None
        finally:
            # Clean up temp file
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)

    def _download_audio(self, video_id: str) -> Optional[str]:
        """
        Download audio from YouTube video using yt-dlp.

        Args:
            video_id: YouTube video ID

        Returns:
            Path to downloaded audio file or None
        """
        try:
            # Create temp file
            temp_dir = tempfile.mkdtemp()
            output_template = os.path.join(temp_dir, "audio.%(ext)s")

            # Use yt-dlp to download audio
            cmd = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--audio-quality", "0",  # Best quality
                "-o", output_template,
                "--no-playlist",
                "--max-filesize", "25M",  # Whisper has 25MB limit
                f"https://www.youtube.com/watch?v={video_id}",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                print(f"yt-dlp error: {result.stderr}")
                return None

            # Find the output file
            audio_path = os.path.join(temp_dir, "audio.mp3")
            if os.path.exists(audio_path):
                return audio_path

            # Check for other extensions
            for ext in ["m4a", "webm", "opus"]:
                path = os.path.join(temp_dir, f"audio.{ext}")
                if os.path.exists(path):
                    return path

            return None

        except subprocess.TimeoutExpired:
            print("yt-dlp download timed out")
            return None
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return None

    def check_transcript_availability(self, video_id: str) -> dict:
        """
        Check what transcript options are available for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with availability info
        """
        result = {
            "has_manual": False,
            "has_auto": False,
            "available_languages": [],
            "can_use_whisper": self.openai_client is not None,
        }

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            for transcript in transcript_list:
                lang_info = {
                    "code": transcript.language_code,
                    "name": transcript.language,
                    "is_generated": transcript.is_generated,
                }
                result["available_languages"].append(lang_info)

                if transcript.is_generated:
                    result["has_auto"] = True
                else:
                    result["has_manual"] = True

        except (TranscriptsDisabled, VideoUnavailable):
            pass
        except Exception as e:
            print(f"Error checking transcript availability: {e}")

        return result


# Singleton instance
transcript_service = TranscriptService()
