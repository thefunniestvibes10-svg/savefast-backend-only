from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import os
import requests
import re

app = Flask(__name__)
CORS(app)

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)

@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'عفاك دخل الرابط'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best', 
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_data = {
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration_string', '00:00'),
                'author': info.get('uploader', 'Unknown'),
                'download_url': info.get('url', ''), 
                'platform': info.get('extractor_key', 'Unknown')
            }

            formats = []
            
            # 1. خيار الفيديو (Best Quality)
            formats.append({
                'type': 'MP4',
                'quality': 'Best Quality', 
                'size': 'HD',
                'url': info.get('url', '') 
            })
            
            # 2. خيار الصوت (Audio Only)
            # كنحاولو نلقاو رابط صوت بوحدو
            audio_url = None
            # بحث عن أحسن صيغة صوتية متوفرة
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_url = f.get('url')
                    break
            
            # إلا مالقيناش صوت بوحدو، كنستعملو الرابط الأصلي (الحل البديل)
            if not audio_url:
                audio_url = info.get('url', '')

            formats.append({
                'type': 'MP3', 
                'quality': 'Audio Only', 
                'size': 'Music',
                'url': audio_url 
            })
            
            video_data['formats'] = formats
            return jsonify(video_data)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'ماقدرناش نعالجو هاد الفيديو. تأكد من الرابط.'}), 500

@app.route('/api/download')
def download_proxy():
    video_url = request.args.get('url')
    title = request.args.get('title', 'video')
    file_type = request.args.get('type', 'MP4') # نوع الملف
    
    if not video_url:
        return "No URL provided", 400

    try:
        req = requests.get(video_url, stream=True)
        
        safe_title = sanitize_filename(title)
        # تحديد الامتداد بناء على النوع
        ext = 'mp3' if file_type == 'MP3' else 'mp4'
        filename = f"{safe_title}_SaveFast.{ext}"

        return Response(
            stream_with_context(req.iter_content(chunk_size=1024)),
            content_type=req.headers['content-type'],
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        print(f"Download Error: {e}")
        return "Error downloading file", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)