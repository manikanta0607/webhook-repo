import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Enable CORS for all routes
CORS(app)

# Try to import MongoDB (optional)
try:
    from pymongo import MongoClient
    from bson import ObjectId
    MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/webhook_receiver")
    client = MongoClient(MONGO_URI)
    db = client.webhook_receiver
    events_collection = db.events
    # Test connection
    client.admin.command('ping')
    logging.info("MongoDB connected successfully")
    USE_MONGODB = True
except Exception as e:
    logging.warning(f"MongoDB not available: {e}")
    events_collection = None
    USE_MONGODB = False

# In-memory storage for events (always available as backup)
events_storage = []

def format_timestamp(timestamp_str):
    """Format timestamp to match the required format"""
    try:
        # Parse ISO format timestamp
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        # Format as required: "1st April 2021 - 9:30 PM UTC"
        day = dt.day
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        
        formatted_date = dt.strftime(f"%{day}{suffix} %B %Y - %I:%M %p UTC")
        return formatted_date
    except Exception as e:
        logging.error(f"Error formatting timestamp: {e}")
        return timestamp_str

def process_webhook_event(payload):
    """Process incoming webhook event and format according to requirements"""
    try:
        event_type = payload.get('action', 'unknown')
        repository = payload.get('repository', {})
        repo_name = repository.get('name', 'unknown')
        
        # Handle different event types
        if 'commits' in payload and payload.get('ref'):
            # PUSH event
            pusher = payload.get('pusher', {})
            author = pusher.get('name', 'Unknown')
            ref = payload.get('ref', '')
            branch = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
            timestamp = payload.get('head_commit', {}).get('timestamp', datetime.utcnow().isoformat() + 'Z')
            
            formatted_timestamp = format_timestamp(timestamp)
            message = f'"{author}" pushed to "{branch}" on {formatted_timestamp}'
            
            event_data = {
                'id': len(events_storage) + 1,
                'type': 'push',
                'message': message,
                'author': author,
                'branch': branch,
                'timestamp': formatted_timestamp,
                'repository': repo_name,
                'raw_timestamp': timestamp
            }
            
        elif event_type == 'opened' and 'pull_request' in payload:
            # PULL REQUEST event
            pull_request = payload.get('pull_request', {})
            author = pull_request.get('user', {}).get('login', 'Unknown')
            from_branch = pull_request.get('head', {}).get('ref', 'unknown')
            to_branch = pull_request.get('base', {}).get('ref', 'unknown')
            timestamp = pull_request.get('created_at', datetime.utcnow().isoformat() + 'Z')
            
            formatted_timestamp = format_timestamp(timestamp)
            message = f'"{author}" submitted a pull request from "{from_branch}" to "{to_branch}" on {formatted_timestamp}'
            
            event_data = {
                'id': len(events_storage) + 1,
                'type': 'pull_request',
                'message': message,
                'author': author,
                'from_branch': from_branch,
                'to_branch': to_branch,
                'timestamp': formatted_timestamp,
                'repository': repo_name,
                'raw_timestamp': timestamp
            }
            
        elif event_type == 'closed' and 'pull_request' in payload:
            # MERGE event (when PR is closed and merged)
            pull_request = payload.get('pull_request', {})
            if pull_request.get('merged', False):
                author = pull_request.get('merged_by', {}).get('login', 'Unknown')
                from_branch = pull_request.get('head', {}).get('ref', 'unknown')
                to_branch = pull_request.get('base', {}).get('ref', 'unknown')
                timestamp = pull_request.get('merged_at', datetime.utcnow().isoformat() + 'Z')
                
                formatted_timestamp = format_timestamp(timestamp)
                message = f'"{author}" merged branch "{from_branch}" to "{to_branch}" on {formatted_timestamp}'
                
                event_data = {
                    'id': len(events_storage) + 1,
                    'type': 'merge',
                    'message': message,
                    'author': author,
                    'from_branch': from_branch,
                    'to_branch': to_branch,
                    'timestamp': formatted_timestamp,
                    'repository': repo_name,
                    'raw_timestamp': timestamp
                }
            else:
                return None
        else:
            logging.warning(f"Unhandled event type: {event_type}")
            return None
            
        # Store event in MongoDB if available, otherwise use in-memory storage
        if USE_MONGODB and events_collection is not None:
            try:
                # Add MongoDB metadata
                event_data['created_at'] = datetime.utcnow()
                result = events_collection.insert_one(event_data)
                event_data['_id'] = str(result.inserted_id)
                
                # Keep only last 100 events (cleanup)
                total_events = events_collection.count_documents({})
                if total_events > 100:
                    oldest_events = events_collection.find().sort('created_at', 1).limit(total_events - 100)
                    for event in oldest_events:
                        events_collection.delete_one({'_id': event['_id']})
                
                logging.info(f"Stored event in MongoDB: {event_data}")
            except Exception as e:
                logging.error(f"MongoDB storage failed, using fallback: {e}")
                # Fallback to in-memory storage
                events_storage.append(event_data)
                if len(events_storage) > 50:
                    events_storage.pop(0)
        else:
            # Store in memory
            events_storage.append(event_data)
            logging.info(f"Stored event: {event_data}")
            
            # Keep only last 50 events
            if len(events_storage) > 50:
                events_storage.pop(0)
                
        return event_data
        
    except Exception as e:
        logging.error(f"Error processing webhook event: {e}")
        return None

@app.route('/')
def index():
    """Main page displaying the events"""
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    """GitHub webhook endpoint"""
    try:
        payload = request.json
        if not payload:
            return jsonify({'error': 'No payload received'}), 400
            
        logging.info(f"Received webhook payload: {payload}")
        
        event_data = process_webhook_event(payload)
        
        if event_data:
            return jsonify({
                'status': 'success',
                'message': 'Event processed successfully',
                'event': event_data
            }), 200
        else:
            return jsonify({
                'status': 'ignored',
                'message': 'Event type not handled'
            }), 200
            
    except Exception as e:
        logging.error(f"Error in webhook endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/events', methods=['GET'])
def get_events():
    """API endpoint to get all events"""
    try:
        if USE_MONGODB and events_collection is not None:
            try:
                # Get events from MongoDB
                events = list(events_collection.find().sort('created_at', -1))
                # Convert ObjectId to string for JSON serialization
                for event in events:
                    if '_id' in event:
                        event['_id'] = str(event['_id'])
                    if 'created_at' in event:
                        del event['created_at']  # Remove internal timestamp
                
                return jsonify({
                    'events': events,
                    'count': len(events)
                })
            except Exception as e:
                logging.error(f"MongoDB read failed, using fallback: {e}")
                # Fall through to in-memory storage
        
        # Return events in reverse chronological order (newest first)
        return jsonify({
            'events': list(reversed(events_storage)),
            'count': len(events_storage)
        })
    except Exception as e:
        logging.error(f"Error getting events: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/events/clear', methods=['POST'])
def clear_events():
    """API endpoint to clear all events"""
    try:
        if USE_MONGODB and events_collection is not None:
            # MongoDB storage
            try:
                result = events_collection.delete_many({})
                return jsonify({
                    'status': 'success',
                    'message': f'Cleared {result.deleted_count} events from MongoDB'
                })
            except Exception as e:
                logging.error(f"MongoDB clear failed: {e}")
                # Fall through to clear in-memory storage
        
        # In-memory storage (fallback or default)
        cleared_count = len(events_storage)
        events_storage.clear()
        return jsonify({
            'status': 'success',
            'message': f'Cleared {cleared_count} events from memory'
        })
    except Exception as e:
        logging.error(f"Error clearing events: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/test-webhook', methods=['POST'])
def test_webhook():
    """Test endpoint to simulate GitHub webhook events"""
    try:
        request_data = request.json or {}
        event_type = request_data.get('type', 'push')
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        if event_type == 'push':
            test_payload = {
                'ref': 'refs/heads/main',
                'pusher': {
                    'name': 'TestUser'
                },
                'repository': {
                    'name': 'test-repo'
                },
                'head_commit': {
                    'timestamp': current_time
                }
            }
        elif event_type == 'pull_request':
            test_payload = {
                'action': 'opened',
                'pull_request': {
                    'user': {
                        'login': 'TestUser'
                    },
                    'head': {
                        'ref': 'feature-branch'
                    },
                    'base': {
                        'ref': 'main'
                    },
                    'created_at': current_time
                },
                'repository': {
                    'name': 'test-repo'
                }
            }
        elif event_type == 'merge':
            test_payload = {
                'action': 'closed',
                'pull_request': {
                    'merged': True,
                    'merged_by': {
                        'login': 'TestUser'
                    },
                    'head': {
                        'ref': 'feature-branch'
                    },
                    'base': {
                        'ref': 'main'
                    },
                    'merged_at': current_time
                },
                'repository': {
                    'name': 'test-repo'
                }
            }
        else:
            return jsonify({'error': 'Invalid event type'}), 400
            
        event_data = process_webhook_event(test_payload)
        
        if event_data:
            return jsonify({
                'status': 'success',
                'message': 'Test event created successfully',
                'event': event_data
            }), 200
        else:
            return jsonify({'error': 'Failed to create test event'}), 500
            
    except Exception as e:
        logging.error(f"Error in test webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)