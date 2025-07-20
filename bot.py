import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Video processing setup
try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
    import imageio
    imageio.plugins.ffmpeg.download()  # Ensure FFmpeg is available
    VIDEO_ENABLED = True
except ImportError as e:
    logger.warning(f"Video processing disabled: {e}")
    VIDEO_ENABLED = False

# Configuration
WATERMARK_TEXT = "Rocky"
FONT_PATH = "font.ttf"  # Include this file in your deployment
FONT_SIZE = 20
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mkv', '.mov', '.avi', '.flv']

app = Client(
    "watermark_bot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

def safe_remove(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Error removing file {file_path}: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply("📸 Send me images or videos to add watermarks!\n"
                      "🎥 Supported video formats: MP4, MKV, MOV, AVI, FLV")

@app.on_message(filters.photo & filters.private)
async def watermark_image(client: Client, message: Message):
    photo_path = watermarked_path = None
    try:
        photo_path = await message.download()
        image = Image.open(photo_path)
        
        # Add watermark
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        except:
            font = ImageFont.load_default()
        
        textwidth = draw.textlength(WATERMARK_TEXT, font)
        textheight = FONT_SIZE
        width, height = image.size
        x, y = width - textwidth - 10, height - textheight - 10
        draw.text((x, y), WATERMARK_TEXT, font=font, fill=(255, 255, 255))
        
        watermarked_path = "watermarked.jpg"
        image.save(watermarked_path)
        await message.reply_photo(watermarked_path)
        
        # OCR caption
        try:
            caption = pytesseract.image_to_string(image)
            if caption.strip():
                await message.reply_text(f"📝 Detected text:\n{caption}")
        except Exception as e:
            logger.warning(f"OCR failed: {e}")

    except Exception as e:
        await message.reply_text(f"❌ Error processing image: {str(e)}")
    finally:
        safe_remove(photo_path)
        safe_remove(watermarked_path)

@app.on_message(filters.video & filters.private)
async def watermark_video(client: Client, message: Message):
    if not VIDEO_ENABLED:
        return await message.reply_text("❌ Video processing unavailable (server missing dependencies)")
    
    video_path = watermarked_path = None
    try:
        video_path = await message.download()
        
        # Check file extension
        file_ext = os.path.splitext(video_path)[1].lower()
        if file_ext not in SUPPORTED_VIDEO_FORMATS:
            return await message.reply_text(f"❌ Unsupported video format. Supported formats: {', '.join(SUPPORTED_VIDEO_FORMATS)}")
        
        # Process video
        clip = VideoFileClip(video_path)
        watermark = (TextClip(WATERMARK_TEXT, fontsize=FONT_SIZE, color='white')
                    .set_position(('right', 'bottom'))
                    .set_duration(clip.duration))
        
        final = CompositeVideoClip([clip, watermark])
        watermarked_path = "watermarked.mp4"
        final.write_videofile(
            watermarked_path,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='fast'
        )
        
        await message.reply_video(
            watermarked_path,
            caption="Here's your watermarked video!"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error processing video: {str(e)}")
    finally:
        safe_remove(video_path)
        safe_remove(watermarked_path)

if __name__ == "__main__":
    app.run()
