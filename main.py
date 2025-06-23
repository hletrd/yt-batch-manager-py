import os
import json
import webbrowser
import socket
import urllib.request
from threading import Timer
from flask import Flask, render_template, request, jsonify, send_file
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CACHE_DIR = 'cache/thumbnails'


class YouTubeManager:
  def __init__(self):
    self.service = None
    self.videos = []
    self.thumbnail_urls = {}
    os.makedirs(CACHE_DIR, exist_ok=True)
    self.authenticate()

  def authenticate(self):
    if not os.path.exists('credentials.json'):
      raise FileNotFoundError(
        "credentials.json not found. Please download it from "
        "Google Cloud Console and save it in the project root."
      )

    creds = None
    if os.path.exists('token.json'):
      creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
      else:
        flow = InstalledAppFlow.from_client_secrets_file(
          'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

      with open('token.json', 'w') as token:
        token.write(creds.to_json())

    self.service = build(API_SERVICE_NAME, API_VERSION, credentials=creds)

  def download_thumbnail(self, url, filename):
    try:
      urllib.request.urlretrieve(url, filename)
      return True
    except Exception as e:
      print(f"Error downloading thumbnail {url}: {e}")
      return False

  def create_local_thumbnail_urls(self, video_id, thumbnails):
    local_thumbnails = {}
    for size, thumb_data in thumbnails.items():
      width = thumb_data['width']
      height = thumb_data['height']
      filename = f"{video_id}_{size}_{width}_{height}.jpg"

      self.thumbnail_urls[filename] = thumb_data['url']

      local_thumbnails[size] = {
        'url': f'/thumbnail/{filename}',
        'width': width,
        'height': height
      }

    return local_thumbnails

  def get_channel_videos(self, channel_id=None, max_results=200):
    try:
      if not channel_id:
        channels_response = self.service.channels().list(
          part='contentDetails',
          mine=True
        ).execute()

        if not channels_response['items']:
          return []

        uploads_playlist_id = (
          channels_response['items'][0]['contentDetails']
          ['relatedPlaylists']['uploads']
        )
      else:
        channels_response = self.service.channels().list(
          part='contentDetails',
          id=channel_id
        ).execute()

        if not channels_response['items']:
          return []

        uploads_playlist_id = (
          channels_response['items'][0]['contentDetails']
          ['relatedPlaylists']['uploads']
        )

      playlist_items = []
      next_page_token = None

      while len(playlist_items) < max_results:
        playlist_response = self.service.playlistItems().list(
          part='snippet,status',
          playlistId=uploads_playlist_id,
          maxResults=min(50, max_results - len(playlist_items)),
          pageToken=next_page_token
        ).execute()

        playlist_items.extend(playlist_response['items'])
        next_page_token = playlist_response.get('nextPageToken')

        if not next_page_token:
          break

      videos = []
      for item in playlist_items:
        try:
          snippet = item.get('snippet', {})
          resource_id = snippet.get('resourceId', {})

          if 'videoId' not in resource_id:
            continue

          video_id = resource_id['videoId']
          thumbnails = snippet.get('thumbnails', {})

          local_thumbnails = self.create_local_thumbnail_urls(video_id, thumbnails)

          thumbnail_url = ''
          for size in ['medium', 'high', 'default', 'standard']:
            if size in local_thumbnails:
              thumbnail_url = local_thumbnails[size]['url']
              break

          status = item.get('status', {})
          privacy_status = status.get('privacyStatus', 'unknown')

          video_data = {
            'id': video_id,
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'thumbnail_url': thumbnail_url,
            'thumbnails': local_thumbnails,
            'published_at': snippet.get('publishedAt', ''),
            'privacy_status': privacy_status
          }
          videos.append(video_data)
        except Exception as e:
          print(f"Error processing video item: {e}")
          continue

      self.videos = videos
      return videos

    except Exception as e:
      print(f"Error fetching videos: {e}")
      return []

  def update_video(self, video_id, title, description):
    try:
      self.service.videos().update(
        part='snippet',
        body={
          'id': video_id,
          'snippet': {
            'title': title,
            'description': description,
            'categoryId': '22'
          }
        }
      ).execute()
      return True
    except Exception as e:
      print(f"Error updating video {video_id}: {e}")
      return False

  def save_videos_to_file(self, filename='videos_backup.json'):
    try:
      with open(filename, 'w', encoding='utf-8') as f:
        json.dump(self.videos, f, indent=2, ensure_ascii=False)
      return True
    except Exception as e:
      print(f"Error saving videos: {e}")
      return False

  def load_videos_from_file(self, filename='videos_backup.json'):
    try:
      if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
          self.videos = json.load(f)
        return True
      return False
    except Exception as e:
      print(f"Error loading videos: {e}")
      return False


youtube_manager = YouTubeManager()


@app.route('/')
def index():
  return render_template('index.html', videos=youtube_manager.videos)


@app.route('/thumbnail/<filename>')
def serve_thumbnail(filename):
  try:
    filepath = os.path.join(CACHE_DIR, filename)

    if os.path.exists(filepath):
      return send_file(filepath, mimetype='image/jpeg')

    if filename in youtube_manager.thumbnail_urls:
      original_url = youtube_manager.thumbnail_urls[filename]
      if youtube_manager.download_thumbnail(original_url, filepath):
        return send_file(filepath, mimetype='image/jpeg')

    return '', 404
  except Exception as e:
    print(f"Error serving thumbnail {filename}: {e}")
    return '', 500


@app.route('/api/load_videos')
def load_videos():
  videos = youtube_manager.get_channel_videos()
  return jsonify({'success': True, 'videos': videos, 'count': len(videos)})


@app.route('/api/save_videos', methods=['POST'])
def save_videos():
  success = youtube_manager.save_videos_to_file()
  return jsonify({'success': success})


@app.route('/api/download_videos')
def download_videos():
  try:
    videos_json = json.dumps(
      youtube_manager.videos, indent=2, ensure_ascii=False
    )
    response = app.response_class(
      videos_json,
      mimetype='application/json',
      headers={
        'Content-Disposition': 'attachment; filename=videos_backup.json'
      }
    )
    return response
  except Exception as e:
    print(f"Error creating download: {e}")
    return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/load_from_file', methods=['POST'])
def load_from_file():
  success = youtube_manager.load_videos_from_file()
  if success:
    return jsonify({'success': True, 'videos': youtube_manager.videos})
  return jsonify({'success': False, 'message': 'No backup file found'})


@app.route('/api/update_video', methods=['POST'])
def update_video():
  data = request.json
  video_id = data.get('video_id')
  title = data.get('title')
  description = data.get('description')

  success = youtube_manager.update_video(video_id, title, description)

  if success:
    for video in youtube_manager.videos:
      if video['id'] == video_id:
        video['title'] = title
        video['description'] = description
        break

  return jsonify({'success': success})


@app.route('/api/update_videos_batch', methods=['POST'])
def update_videos_batch():
  data = request.json
  updates = data.get('updates', [])

  if not updates:
    return jsonify({'success': False, 'message': 'No updates provided'})

  results = {
    'successful': [],
    'failed': []
  }

  for update in updates:
    video_id = update.get('video_id')
    title = update.get('title')
    description = update.get('description')

    if not video_id or title is None or description is None:
      results['failed'].append({
        'video_id': video_id,
        'error': 'Missing required fields'
      })
      continue

    success = youtube_manager.update_video(video_id, title, description)

    if success:
      # Update local video data
      for video in youtube_manager.videos:
        if video['id'] == video_id:
          video['title'] = title
          video['description'] = description
          break

      results['successful'].append({
        'video_id': video_id,
        'title': title
      })
    else:
      results['failed'].append({
        'video_id': video_id,
        'error': 'YouTube API update failed'
      })

  success_count = len(results['successful'])
  total_count = len(updates)

  return jsonify({
    'success': success_count > 0,
    'results': results,
    'summary': {
      'total': total_count,
      'successful': success_count,
      'failed': len(results['failed'])
    }
  })


def find_available_port(start_port=5000):
  port = start_port
  while port < start_port + 100:
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      sock.bind(('127.0.0.1', port))
      sock.close()
      return port
    except OSError:
      port += 1
  raise RuntimeError("Could not find an available port")


def open_browser(port):
  webbrowser.open(f'http://127.0.0.1:{port}')


if __name__ == '__main__':
  if not os.path.exists('templates'):
    os.makedirs('templates')

  try:
    port = find_available_port()
    print(f"Starting server on port {port}")

    Timer(1.5, lambda: open_browser(port)).start()

    app.run(host='127.0.0.1', port=port, debug=True, use_reloader=False)
  except RuntimeError as e:
    print(f"Error: {e}")
    print("Please free up some ports and try again.")