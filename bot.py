import os
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
except ImportError:
    logger.warning("MoviePy not installed - video watermarking disabled")
    VideoFileClip = None

# Configuration
WATERMARK_TEXT = "Rocky"
FONT_PATH = "font.ttf"  # Include this file in your project
FONT_SIZE = 20

# Initialize client
app = Client(
    "watermark_bot",
    api_id=int(os.getenv("API_ID", 22505271)),
    api_hash=os.getenv("API_HASH", "c89a94fcfda4bc06524d0903977fc81e"),
    bot_token=os.getenv("BOT_TOKEN")
)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply("Send me an image or video to add a watermark!")

@app.on_message(filters.photo & filters.private)
async def watermark_image(client: Client, message: Message):
    try:
        photo_path = await message.download()
        image = Image.open(photo_path)
        
        # Add watermark
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        except:
            font = ImageFont.load_default()
        
        textwidth, textheight = draw.textsize(WATERMARK_TEXT, font)
        width, height = image.size
        x, y = width - textwidth - 10, height - textheight - 10
        draw.text((x, y), WATERMARK_TEXT, font=font, fill=(255, 255, 255))
        
        watermarked_path = "watermarked.jpg"
        image.save(watermarked_path)
        await message.reply_photo(watermarked_path)
        
        # OCR caption (optional)
        try:
            caption = pytesseract.image_to_string(image)
            if caption.strip():
                await message.reply_text(f"Detected text:\n{caption}")
        except Exception as e:
            logger.warning(f"OCR failed: {e}")

    except Exception as e:
        await message.reply_text(f"Error processing image: {e}")
    finally:
        for f in [photo_path, watermarked_path]:
            if f and os.path.exists(f): os.remove(f)

@app.on_message(filters.video & filters.private)
async def watermark_video(client: Client, message: Message):
    if not VideoFileClip:
        return await message.reply_text("Video processing not available (missing dependencies)")
    
    try:
        video_path = await message.download()
        clip = VideoFileClip(video_path)
        
        # Create watermark
        watermark = TextClip(
            WATERMARK_TEXT,
            fontsize=FONT_SIZE,
            color='white',
            font=FONT_PATH
        ).set_position(('right', 'bottom')).set_duration(clip.duration)
        
        # Composite video
        final = CompositeVideoClip([clip, watermark])
        watermarked_path = "watermarked.mp4"
        final.write_videofile(watermarked_path, codec='libx264')
        
        await message.reply_video(watermarked_path)
    except Exception as e:
        await message.reply_text(f"Error processing video: {e}")
    finally:
        for f in [video_path, watermarked_path]:
            if f and os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    app.run()
