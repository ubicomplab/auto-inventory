## Highlights
- Automated Data Entry: Automatically pulls relevant order confirmations, receipts, or request emails from Gmail.
- Intelligent Extraction: Uses LLMs to parse unstructured text and PDF attachments into clean, structured data.
- Seamless Sync: Writes extracted details directly into a Google Sheet for real-time collaboration.
- Lightweight Deployment: Runs as a simple Python script locally or on a cloud micro-instance (e.g., Fly.io).

## Overview
Tracking orders, managing budgets, or maintaining inventories by manually entering information is tedious and error-prone. This project provides a flexible, automated pipeline that turns your email inbox into an up-to-date inventory.
The pipeline periodically fetches relevant emails (based on your filters), sends the full text and any PDF attachments to an LLM, and extracts key fields defined by your schema (e.g., item names, prices, tracking numbers, or project codes). The results are instantly appended to a Google Sheet.
Everything is implemented as a lightweight Python script that you can run locally or deploy on a small VM.
This tool is also easily adaptable for auditing and grant reporting.

## Installation
1. Clone this repository and enter the project directory
2. Install Python dependencies `pip install -r requirements.txt`

## Configuration
By the end of this section you should have **three JSON credential files** in the project root:
- `credentials.json`  (Gmail OAuth client)
- `token.json`        (Gmail user token, created after first run)
- `service_account.json`  (Google Sheets service account key)

### 1. Gmail API (credentials.json / token.json)
The pipeline reads purchase emails from your Gmail inbox using the Gmail API.
1. Go to the Google Cloud Console and create a project (or reuse an existing one).
2. Enable the **Gmail API** for that project.
3. Configure an OAuth consent screen (minimal configuration is fine for internal use).
4. Create an **OAuth client ID** of type **Desktop app**.
5. Download the JSON file and save it as `credentials.json` in the project root (next to `src/`).
The first time you run the pipeline locally, it will:
- open a browser window asking you to log in to Gmail and grant access;
- then create a `token.json` file in the project root.
From then on, the script will reuse `token.json` to refresh the access token and read your emails.  
> **If you see errors like `invalid_grant` / `Token has been expired or revoked`:**
> delete `token.json` and run the script again.  
> It will open the browser once more, let you re-authorize, and create a fresh `token.json`.

### 2. Google Sheets (spreadsheet + service_account.json)
The pipeline writes all extracted items into a Google Sheet.
1. **Create the inventory spreadsheet**
   - Create a new Google Sheet in your Google account.
   - In the first sheet (name it `Sheet1`), add the following header row:
     | A           | B            | C        | D           | E         | F       | G             |
     | ----------- | ------------ | -------- | ----------- | --------- | ------- | ------------- |
     | category    | product_name | quantity | order_date  | requester | pi_name | ee_component  |
   - Create another sheet named `processed_ids`.  
     Column A will be used to store processed Gmail message IDs.
2. **Find your `SPREADSHEET_ID`**
   - The spreadsheet ID is the long string in the URL
   - Configure this ID in `sheets_write.py`:
     SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"
3. **Enable the Google Sheets API and create a service account**
   - In the Google Cloud Console:
     1. Enable the **Google Sheets API** for your project.
     2. Create a **Service Account**.
     3. Generate a JSON key for this service account and download it as `service_account.json`.
   - Place `service_account.json` in the project root (next to `src/`).
   - Share your inventory spreadsheet with the service account’s email address  
     (visible inside `service_account.json`), and give it **Editor** permission.
The code will then use `service_account.json` to authenticate and write rows into your Google Sheet.

### 3. Gemini API key
This project uses Gemini for the extraction step.  
Set the `GOOGLE_API_KEY` environment variable to your own API key before running the pipeline.
- Local (macOS / Linux / WSL): `export GOOGLE_API_KEY="sk-xxxx..."`
- Windows PowerShell: `$Env:GOOGLE_API_KEY = "sk-xxxx..."`

## Usage / Runtime behavior
1. Run the pipeline locally
   - From the project root, run: `python src/main.py`.
   - On the first run, it will open a browser for Gmail authorization (if `token.json` does not exist yet).
   - After that, it will start an infinite loop: fetch emails → extract items → write to Google Sheet → sleep.
### Polling interval (`SLEEP_SECONDS`)
The sleep time between cycles is controlled by the `SLEEP_SECONDS` constant in `main.py`, for example:
`SLEEP_SECONDS = 5 * 60 * 60  # 5 hours`
This means the script will:
- fetch emails from Gmail,
- process and write new items to the Google Sheet,
- then sleep for 5 hours before the next run.

## Deploying on Fly.io (optional)
You can run this pipeline as a long-running worker on Fly.io so it keeps polling Gmail and updating your inventory sheet in the background.
1. **Install and log in to Fly.io**
   - Install `flyctl` following the Fly.io docs.
   - Log in with: `fly auth login`.
4. **Create the Fly app (first time only)**
   - Run: `fly launch --no-deploy`.  
   - This creates an app and a `fly.toml` file in the current directory.  
   - Make sure `fly.toml` is configured to run your pipeline entry point (for example `python -m src.main`).
5. **Configure secrets on Fly**
   Set the same environment variables you used locally:
   - `fly secrets set GOOGLE_API_KEY=sk-xxxx...`  
6. **Deploy the app**
   - From the project root, run: `fly deploy`.  
   - Fly will build a Docker image (including your code and the JSON credentials that are present in the directory) and start a machine running the pipeline.
7. **Monitor logs**
   - Run: `fly logs`.  
   - You should see the pipeline:
     - loading processed IDs from the `processed_ids` sheet  
     - fetching emails from Gmail  
     - extracting items via the LLM  
     - appending rows into your inventory sheet  
     - sleeping between cycles  
   - If you later change the code or configuration, update the files locally and run `fly deploy` again to roll out a new version.

