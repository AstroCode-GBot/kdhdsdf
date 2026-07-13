from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from PIL import Image
import requests
from io import BytesIO

app = FastAPI(title="GitHub Banner Cropper API")

# আপনার GitHub রিপোজিটরির ইনফরমেশন
GITHUB_OWNER = "AstroCode-GBot"
GITHUB_REPO = "kdhdsdf"
FOLDER_PATH = "banner"

# GitHub API-এর মাধ্যমে ফোল্ডারের সব ফাইলের লিস্ট আনার ফাংশন
def get_github_files():
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{FOLDER_PATH}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return []
    
    items = response.json()
    # শুধুমাত্র ইমেজ ফাইলগুলোর (png, jpg, jpeg, webp) নামের লিস্ট ফিল্টার করা হচ্ছে
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    image_files = [item['name'] for item in items if item['type'] == 'file' and item['name'].lower().endswith(valid_extensions)]
    return image_files

# ১. অল ইমেজ প্রিভিউ দেখার জন্য HTML ড্যাশবোর্ড রুট
@app.get("/banners", response_class=HTMLResponse)
async def list_all_banners():
    files = get_github_files()
    if not files:
        return "<h3>No images found or GitHub API error.</h3>"
    
    # ব্রাউজারে সুন্দরভাবে সব ক্রপ করা ছবি একসাথে দেখার জন্য গ্রিড ভিউ ডিজাইন
    html_content = """
    <html>
        <head>
            <title>All Cropped Banners Preview</title>
            <style>
                body { font-family: Arial, sans-serif; background: #1e1e1e; color: white; padding: 20px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .card { background: #2d2d2d; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
                img { max-width: 100%; border-radius: 4px; margin-top: 10px; }
                a { color: #00adb5; text-decoration: none; word-break: break-all; font-size: 14px; }
            </style>
        </head>
        <body>
            <h2>GitHub Banner Preview (/banner)</h2>
            <div class="grid">
    """
    
    for filename in files:
        api_image_url = f"/banner/{filename}"
        html_content += f"""
            <div class="card">
                <a href="{api_image_url}" target="_blank">{filename}</a><br/>
                <img src="{api_image_url}" alt="{filename}" />
            </div>
        """
        
    html_content += """
            </div>
        </body>
    </html>
    """
    return html_content

# ২. ডাইনামিক রুট: ফাইলের আসল নামে ক্রপ করে লাইভ ইমেজ রিটার্ন করবে
@app.get("/banner/{filename}")
async def get_cropped_banner(filename: str):
    # GitHub এর র' (raw) ইমেজ URL তৈরি করা হচ্ছে
    raw_img_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/refs/heads/main/{FOLDER_PATH}/{filename}"
    
    # রানটাইমে ইমেজ ডাউনলোড করা (স্টোরেজে কোনো ফাইল সেভ হবে না)
    response = requests.get(raw_img_url)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Image not found in GitHub repository")
    
    try:
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        
        # বাম পাশের স্কয়ার অ্যাভাটার অংশ কেটে বাদ দিয়ে ডান পাশের অংশ রাখা হচ্ছে
        crop_area = (height, 0, width, height)
        cropped_img = img.crop(crop_area)
        
        # ক্রপ করা ইমেজটি মেমোরিতে (RAM) হোল্ড করা হচ্ছে
        img_io = BytesIO()
        
        # এক্সটেনশন চেক করে সঠিক ফরম্যাটে পাঠানো
        img_format = "PNG" if filename.lower().endswith(".png") else "JPEG"
        cropped_img.save(img_io, format=img_format)
        img_io.seek(0)
        
        # মিডিয়া টাইপ ডিক্লেয়ার করে ব্রাউজারে সরাসরি ইমেজ রেসপন্স পাঠানো
        media_type = f"image/{img_format.lower()}"
        return StreamingResponse(img_io, media_type=media_type)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
