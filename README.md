# YT Batch Manager

A Python+Flask-based web application for batch editing YouTube video titles and descriptions.

* Disclaimer: YouTube is a registered trademark of Google LLC, and this project is not affiliated with YouTube in any way.

## Features

- Edit video titles and descriptions in a single page, which YouTube does not allow.
  - YouTube forces a very user-unfriendly experiences, where you have to go to each video page to edit the title and description, and then save it.
- Save/load video data to/from local JSON files.

## Prerequisites

- Python 3.11+ installed.
- Google Cloud Console project with YouTube Data API v3 enabled.
- Your own YouTube channel.

## Setup

### 1. Install dependencies

* I personally recommend using venv.
```bash
$ python -m venv venv
$ source venv/bin/activate
```

* Install dependencies.
```bash
$ pip install -r requirements.txt
```

### 2. Google API setup

#### 2.1. Create a new project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project, name it whatever you want.
3. Search for the **YouTube Data API v3** in the search bar, and enable it.
4. Search for the **OAuth consent screen** in the search bar, and click 'Clients' on the left sidebar.
5. Create a new client app as a desktop app, name it whatever you want.
6. Download the credentials JSON file.
7. Rename the file to `credentials.json` and move it to the root of the project.

#### 2.2. Add scopes
1. Search for the **OAuth consent screen** in the search bar, and click 'Data Access' on the left sidebar.
2. Click 'Add or remove scopes' and enter following scopes in **Manually add scopes** text box:
```
https://www.googleapis.com/auth/youtube
```
3. Click 'Add to table'.
4. Click 'Update'.
5. Click 'Save'.

#### 2.3. Add yourself as a test user
1. Search for the **OAuth consent screen** in the search bar, and click 'Audience' on the left sidebar.
2. Click 'Add user' under 'Test users' and enter your email address.

### 3. Run the application

```bash
python main.py
```

The application will:
- Start the Flask server on `http://127.0.0.1:5000`
- Automatically open your default browser.
- Prompt for Google OAuth authentication on first run.

## Usage

### Initial Setup
1. Run the application.
2. Complete Google OAuth authentication in your browser.
3. Click "Load from YouTube" to fetch your videos.

### Managing Videos
- **Edit titles and descriptions**: Simply click in the text fields and make changes.
- **Update individual videos**: Click the "Update Video" button that appears after making changes.
- **Save backup**: Click "Save to File" to create a local JSON backup.
- **Load backup**: Click "Load from File" to restore from a previous backup.

## Troubleshooting

### Google OAuth authentication fails
1. Check if the `credentials.json` file is placed in the root of the project.
2. Remove existing `token.json` file, and run the application again.
3. If the problem persists, try to re-create the `credentials.json` file.