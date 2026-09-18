"""
AI Video Translation & Voice Cloning Platform - Gradio UI
Main application with modern, professional interface.
"""
import gradio as gr
import threading
from pathlib import Path

from config import ensure_output_dir
from pipeline import Pipeline


# Theme colors
THEME_PRIMARY = "#6366F1"  # Indigo
THEME_SECONDARY = "#8B5CF6"  # Purple
THEME_ACCENT = "#22D3EE"  # Cyan
THEME_BG = "#0F172A"  # Dark slate
THEME_SURFACE = "#1E293B"  # Slate
THEME_TEXT = "#F8FAFC"  # Light
THEME_SUCCESS = "#22C55E"  # Green
THEME_ERROR = "#EF4444"  # Red

# Voice options for TTS
VOICE_OPTIONS = [
    ("vi-Female-1 (Nữ - HoaiMy)", "vi-Female-1"),
    ("vi-Male-1 (Nam - NamMinh)", "vi-Male-1"),
    ("default (Nữ)", "default"),
]


def run_pipeline(
    url: str,
    voice_id: str,
    background_music: str,
    youtube_upload: bool,
    facebook_upload: bool,
    progress_callback,
):
    """
    Run the translation pipeline with progress updates.
    """
    results = {"success": False, "error": None, "youtube_url": "", "facebook_url": ""}

    def callback(step: str, message: str):
        progress_callback(
            f"**{step}**: {message}",
            f"[{step}] {message}",
        )

    # Determine target platforms
    target_platforms = []
    if youtube_upload:
        target_platforms.append("youtube")
    if facebook_upload:
        target_platforms.append("facebook")

    try:
        pipeline = Pipeline(output_callback=callback)
        results = pipeline.run(
            url=url,
            voice_id=voice_id,
            background_music=background_music,
            target_platforms=target_platforms,
        )
    except Exception as e:
        results["error"] = str(e)
        callback("ERROR", str(e))

    return results


def create_ui():
    """Create the Gradio UI interface."""

    with gr.Blocks(
        title="AI Video Translation",
    ) as app:

        # Header
        gr.Markdown(
            """
            # 🎬 AI Video Translation & Voice Cloning
            ### Tự động dịch và lồng tiếng Việt cho video YouTube, TikTok, Douyin
            """,
            elem_id="header",
        )

        with gr.Row(equal_height=False):
            # Left Panel - Input
            with gr.Column(scale=1):
                gr.Markdown("### 📥 Input Configuration")

                # URL Input
                url_input = gr.Textbox(
                    label="Video URL",
                    placeholder="Paste YouTube, TikTok, or Douyin URL here...",
                    lines=2,
                )

                # File Upload
                file_input = gr.File(
                    label="Or Upload Video File",
                    file_count="single",
                    file_types=["video"],
                    elem_id="video-upload",
                )

                # Platform Detection
                platform_radio = gr.Radio(
                    choices=["Auto-detect", "YouTube", "TikTok", "Douyin"],
                    value="Auto-detect",
                    label="Platform",
                    info="Select platform or let system auto-detect",
                )

                # Voice Selection
                voice_dropdown = gr.Dropdown(
                    choices=VOICE_OPTIONS,
                    value="vi-Female-1",
                    label="Voice Selection (Giọng Việt)",
                    info="ASR và dịch chạy local mặc định; Edge TTS là lựa chọn tương thích tạm thời.",
                )

                # Background Music
                bg_music_radio = gr.Radio(
                    choices=["None", "Duck (-12dB)"],
                    value="None",
                    label="Background Music",
                    info="Process original background music",
                )

                # Target Platforms
                gr.Markdown("### 📤 Target Platforms")
                youtube_checkbox = gr.Checkbox(
                    label="YouTube (OAuth2)",
                    value=False,
                )
                facebook_checkbox = gr.Checkbox(
                    label="Facebook (Graph API)",
                    value=False,
                )

                # Run Button
                run_button = gr.Button(
                    "▶ RUN PIPELINE",
                    variant="primary",
                    size="lg",
                )

            # Right Panel - Output
            with gr.Column(scale=1):
                gr.Markdown("### 📊 Progress & Results")

                # Progress Display
                progress_text = gr.Textbox(
                    label="Progress Log",
                    lines=15,
                    interactive=False,
                    show_label=True,
                )

                # Status
                status_html = gr.HTML(
                    value='<div style="padding: 10px; background: #1E293B; border-radius: 8px;">'
                         '<span style="color: #F8FAFC;">Ready to process</span>'
                         '</div>',
                    label="Status",
                )

                # Results
                gr.Markdown("### ✅ Results")
                result_video = gr.Video(label="Dubbed Video Result", interactive=False)
                result_youtube = gr.Textbox(
                    label="YouTube URL",
                    interactive=False,
                    placeholder="Upload complete to see URL...",
                )
                result_facebook = gr.Textbox(
                    label="Facebook URL",
                    interactive=False,
                    placeholder="Upload complete to see URL...",
                )
                result_output = gr.Textbox(
                    label="Output Directory",
                    interactive=False,
                    placeholder="...",
                )

        # Event Handlers
        def on_run(
            url,
            video_file,
            platform,
            voice_id,
            background_music,
            youtube_upload,
            facebook_upload,
        ):
            # Check if either URL or file is provided
            has_url = url and url.strip()
            has_file = video_file is not None

            if not has_url and not has_file:
                return (
                    "Error: Please enter a video URL or upload a video file",
                    '<div style="padding: 10px; background: #EF4444; border-radius: 8px;">'
                    '<span style="color: white;">Error: No URL or file provided</span></div>',
                    None,
                    "",
                    "",
                    "",
                )

            # Validate URL if provided
            if has_url:
                url_lower = url.lower()
                supported = any([
                    "youtube.com" in url_lower,
                    "youtu.be" in url_lower,
                    "tiktok.com" in url_lower,
                    "douyin.com" in url_lower,
                    "vt.tiktok" in url_lower,
                ])
                if not supported or "localhost" in url_lower:
                    return (
                        f"Error: Unsupported URL. Please enter a valid YouTube/TikTok/Douyin URL.\nReceived: {url[:50]}...",
                        '<div style="padding: 10px; background: #EF4444; border-radius: 8px;">'
                        '<span style="color: white;">Error: Invalid video URL</span></div>',
                        None,
                        "",
                        "",
                        "",
                    )

            # Convert background_music string to expected format
            bg_option = "duck" if "Duck" in background_music else "none"

            # Determine target platforms
            target_platforms = []
            if youtube_upload:
                target_platforms.append("youtube")
            if facebook_upload:
                target_platforms.append("facebook")

            # Progress messages collector
            progress_messages = ["**Starting pipeline...**\n"]

            def progress_callback(step: str, message: str):
                progress_messages.append(f"**{step}**: {message}\n")

            try:
                pipeline = Pipeline(output_callback=progress_callback)
                
                # Determine local file path if uploaded
                local_video = video_file.name if video_file else None
                
                output = pipeline.run(
                    url=url if has_url else "",
                    voice_id=voice_id,
                    background_music=bg_option,
                    target_platforms=target_platforms,
                    local_video_path=local_video,
                )

                youtube_url = output.get("youtube_url", "")
                facebook_url = output.get("facebook_url", "")
                output_dir = output.get("output_dir", "")

                if output.get("success"):
                    status = (
                        '<div style="padding: 10px; background: #22C55E; border-radius: 8px;">'
                        '<span style="color: white;">✓ PIPELINE COMPLETE</span></div>'
                    )
                    progress_messages.append("**DONE**: Pipeline complete!")
                else:
                    status = (
                        '<div style="padding: 10px; background: #EF4444; border-radius: 8px;">'
                        f'<span style="color: white;">✗ Error: {output.get("error", "Unknown")}</span></div>'
                    )
                    progress_messages.append(f"**ERROR**: {output.get('error', 'Unknown')}")

                return (
                    "\n".join(progress_messages),
                    status,
                    output.get("dubbed_video"),
                    youtube_url,
                    facebook_url,
                    output_dir,
                )

            except Exception as e:
                return (
                    f"**ERROR**: {str(e)}",
                    f'<div style="padding: 10px; background: #EF4444; border-radius: 8px;">'
                    f'<span style="color: white;">Error: {str(e)}</span></div>',
                    None,
                    "",
                    "",
                    "",
                )

        # Wire up the button
        run_button.click(
            fn=on_run,
            inputs=[
                url_input,
                file_input,
                platform_radio,
                voice_dropdown,
                bg_music_radio,
                youtube_checkbox,
                facebook_checkbox,
            ],
            outputs=[progress_text, status_html, result_video, result_youtube, result_facebook, result_output],
        )

        # Examples
        gr.Markdown("### 📝 Examples")
        gr.Examples(
            examples=[
                ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "default", "None"],
                ["https://www.tiktok.com/@user/video/1234567890", "vi-Female-1", "Duck (-12dB)"],
            ],
            inputs=[url_input, voice_dropdown, bg_music_radio],
            label="Quick Examples",
        )

        # Footer
        gr.Markdown(
            """
            ---
            ### 🔧 Local-first configuration
            - **faster-whisper**: ASR trên máy, không cần Groq.
            - **Local LLM**: dịch và metadata qua Ollama/vLLM endpoint trong `.env`.
            - **Edge TTS**: lựa chọn tương thích trong khi chờ TTS tiếng Việt self-hosted.
            - **YouTube OAuth / Facebook Token**: chỉ cần khi bạn bật đăng video.

            Sao chép `.env.example` thành `.env`. `AUTO_PUBLISH=false` là mặc định,
            nên video được tạo sẽ chờ bạn duyệt trước khi đăng.
            """,
            elem_id="footer",
        )

    return app


def main():
    """Main entry point."""
    app = create_ui()
    app.queue(default_concurrency_limit=1).launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
            neutral_hue="slate",
        ),
    )


if __name__ == "__main__":
    main()
