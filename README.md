# GitHub Webhook Receiver

A Flask web application to receive, display, and test GitHub webhook events (Push, Pull Request, Merge) in real-time. Events are stored in MongoDB (if available) or in-memory, and a modern UI is provided for visualization.

---

## Project Structure

```
.env
app.py
main.py
README.md
requirements.txt
static/
    script.js
    style.css
templates/
    index.html
```

---

## Step-by-Step Setup

### 1. Clone the Repository

```sh
git clone <your-repo-url>
cd Webhoo_Task
```

### 2. Install Dependencies

```sh
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Edit the `.env` file with your secrets and MongoDB URI (or use the provided defaults):

```
SESSION_SECRET="your-secret"
FLASK_ENV=development
FLASK_DEBUG=True
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
```

If MongoDB is not available, the app will use in-memory storage.

### 4. Run the Application

```sh
python main.py
```

The app will be available at [http://localhost:5001](http://localhost:5001).

---

## How to Use

1. **Open the app in your browser:**  
   Go to [http://localhost:5001](http://localhost:5001).

2. **Copy the Webhook URL:**  
   Use the "Webhook URL" shown in the UI for your GitHub repository webhook settings.

3. **Simulate Events:**  
   Use the "Test Webhook Events" buttons to generate sample events (Push, Pull Request, Merge).

4. **View Events:**  
   Incoming events will appear in the "Repository Events" section.

---

## API Endpoints

- `POST /webhook`  
  Receives GitHub webhook payloads.

- `GET /api/events`  
  Returns all stored events (JSON).

- `POST /api/events/clear`  
  Clears all stored events.

- `POST /test-webhook`  
  Simulates a webhook event (body: `{ "type": "push" | "pull_request" | "merge" }`).

---

## File Descriptions

- [`app.py`](app.py): Main Flask app, API endpoints, event processing, MongoDB/in-memory storage.
- [`main.py`](main.py): Entry point to run the Flask app.
- [`requirements.txt`](requirements.txt): Python dependencies.
- [`static/script.js`](static/script.js): Frontend logic for polling, rendering, and notifications.
- [`static/style.css`](static/style.css): Custom styles for the UI.
- [`templates/index.html`](templates/index.html): Main HTML template for the web UI.

---

## Notes

- If MongoDB is not available, events are stored in memory (lost on restart).
- The UI polls for new events every 15 seconds.
- For production, set `FLASK_ENV=production` and use a production-ready server (e.g., Gunicorn).

---
