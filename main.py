import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import requests
from io import BytesIO

app = FastAPI(
    title="GitHub Banner Cropper API",
    description="GitHub থেকে ইমেজ নিয়ে অন-দ্য-ফ্লাই ক্রপ করার API",
    version="1.0.0"
)

# CORS পলিসি সেটআপ (যাতে যেকোনো ওয়েবসাইট বা অ্যাপ থেকে এই API কল করা যায়)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# আপনার GitHub রিপোজিটরির কনফিগারেশন
GITHUB_OWNER = "AstroCode-GBot"
GITHUB_REPO = "kdhdsdf"
FOLDER_PATH = "banner"

def get_github_files():
    """GitHub API ব্যবহার করে ফোল্ডারের সমস্ত ইমেজের নামের লিস্ট নিয়ে আসে"""
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{FOLDER_PATH}"
    
    # GitHub API রেট লিমিট এড়াতে টোকেন থাকলে সেটি ব্যবহার করবে (ঐচ্ছিক)
    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"
        
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        
        items = response.json()
        valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
        # শুধুমাত্র ইমেজ ফাইলগুলো ফিল্টার করা হচ্ছে
        image_files = [
            item['name'] for item in items 
            if item['type'] == 'file' and item['name'].lower().endswith(valid_extensions)
        ]
        return image_files
    except Exception:
        return []

@app.get("/", response_class=HTMLResponse)
async def root():
    """রুট ইউআরএল-এ স্বাগতম বার্তা এবং ড্যাশবোর্ড লিংক"""
    return """
    <html>
        <head><title>Banner API</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px; background: #121212; color: white;">
            <h1>GitHub Banner Cropper API Live! 🚀</h1>
            <p>সব ব্যানারের লাইভ প্রিভিউ দেখতে ভিজিট করুন: <a href="/banners" style="color: #00adb5;">/banners</a></p>
            <p>নির্দিষ্ট ইমেজ দেখতে ব্যবহার করুন: <code>/banner/{filename.png}</code></p>
        </body>
    </html>
    """

@app.get("/banners", response_class=HTMLResponse)
async def list_all_banners():
    """সব ইমেজের লাইভ প্রিভিউ দেখার জন্য ড্যাশবোর্ড গ্রিড ভিউ"""
    files = get_github_files()
    if not files:
        return """
        <body style="font-family: Arial, sans-serif; background: #1e1e1e; color: white; padding: 20px;">
            <h3>কোনো ইমেজ পাওয়া যায়নি অথবা GitHub API লিমিট শেষ হয়েছে।</h3>
        </body>
        """
    
    html_content = """
    <html>
        <head>
            <title>All Cropped Banners Preview</title>
            <style>
                body { font-family: Arial, sans-serif; background: #1e1e1e; color: white; padding: 20px; margin: 0; }
                h2 { border-bottom: 2px solid #333; padding-bottom: 10px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; padding-top: 20px; }
                .card { background: #2d2d2d; border-radius: 8px; padding: 12px; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.4); }
                img { max-width: 100%; height: auto; border-radius: 4px; margin-top: 10px; background: #111; }
                a { color: #00adb5; text-decoration: none; word-break: break-all; font-size: 14px; font-weight: bold; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h2>GitHub Banner Preview Panel (/banner)</h2>
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

@app.get("/banner/{filename}")
async def get_cropped_banner(filename: str):
    """ডাইনামিক রুট: ফাইলের আসল নামে ক্রপ করে লাইভ ইমেজ রিটার্ন করবে"""
    # GitHub থেকে সরাসরি র' (raw) ইমেজ নেওয়ার লিংক
    raw_img_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/refs/heads/main/{FOLDER_PATH}/{filename}"
    
    try:
        response = requests.get(raw_img_url, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Image not found in GitHub repository")
        
        # মেমোরিতে ইমেজ ওপেন করা হচ্ছে
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        
        if width <= height:
            raise HTTPException(status_code=400, detail="Image width is too small to crop the avatar section")

        # বাম পাশের স্কয়ার অ্যাভাটার অংশ বাদ দিয়ে বাকি ডান পাশের অংশ ক্রপ করা
        crop_area = (height, 0, width, height)
        cropped_img = img.crop(crop_area)
        
        # ক্রপ করা ইমেজ মেমোরিতে (RAM) রাইট করা
        img_io = BytesIO()
        
        # সঠিক ফরম্যাট এক্সটেনশন নির্ধারণ করা
        ext = filename.lower().split('.')[-1]
        img_format = "PNG" if ext == "png" else "JPEG"
        
        cropped_img.save(img_io, format=img_format)
        img_io.seek(0)
        
        media_type = f"image/{img_format.lower()}"
        return StreamingResponse(img_io, media_type=media_type)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
