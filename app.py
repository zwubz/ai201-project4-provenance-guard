import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from signals import (
    analyze_semantic_coherence,
    analyze_sentence_length_variance,
    analyze_lexical_diversity,
    combine_signals,
    get_transparency_label
)
from database import init_db, insert_submission, get_all_submissions, register_appeal

app = Flask(__name__)

# Initialize rate limiter with in-memory storage for local development
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# Initialize database schema on startup
init_db()

@app.route("/", methods=["GET"])
def index():
    """
    GET /
    Returns metadata about the API endpoints.
    """
    return jsonify({
        "name": "Provenance Guard API",
        "version": "1.0.0",
        "description": "Multi-signal AI content verification pipeline",
        "endpoints": {
            "POST /submit": "Evaluates a text block and returns AI classification results (Rate limited)",
            "GET /log": "Returns the most recent audit logs",
            "POST /appeal": "Disputes a classification by submitting creator reasoning"
        }
    }), 200

@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit_content():
    """
    POST /submit
    Accepts a JSON payload containing:
    - text: str (the text to analyze)
    - creator_id: str (the identifier for the creator)
    
    Validates input, runs Signal 1, 2, and 3, synthesizes them using the ensemble formula,
    resolves transparency labels, writes diagnostics to SQLite, and returns the response.
    
    Enforces Rate Limiting (10 requests per minute, 100 requests per day).
    """
    # Validate request content type
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
        
    data = request.get_json()
    
    # Validate required parameters
    text = data.get("text")
    creator_id = data.get("creator_id")
    
    if not text or not isinstance(text, str):
        return jsonify({"error": "Missing or invalid parameter: 'text' (must be a non-empty string)"}), 400
        
    if not creator_id or not isinstance(creator_id, str):
        return jsonify({"error": "Missing or invalid parameter: 'creator_id' (must be a non-empty string)"}), 400

    # Generate a unique content ID for tracking this submission
    content_id = str(uuid.uuid4())
    
    # Execute Signals
    s_llm = analyze_semantic_coherence(text)
    s_slv = analyze_sentence_length_variance(text)
    s_ttr = analyze_lexical_diversity(text)
    
    # Combine signals according to the 3-signal spec weighting formula
    confidence = combine_signals(s_llm, s_slv, s_ttr)
    
    # Threshold mapping for attribution category based on calibration
    if confidence <= 0.35:
        attribution = "likely_human"
    elif confidence <= 0.70:
        attribution = "uncertain"
    else:
        attribution = "likely_ai"

    # Resolve transparency labels (title, body) from the planning.md spec
    label_title, label_body = get_transparency_label(confidence)

    # Write structured diagnostics entry to persistent SQLite database audit log
    try:
        insert_submission(
            content_id=content_id,
            creator_id=creator_id,
            text=text,
            attribution=attribution,
            confidence=confidence,
            llm_score=s_llm,
            slv_score=s_slv,
            ttr_score=s_ttr
        )
    except Exception as e:
        # Log database error, but do not fail the API response if insertion fails
        print(f"Database insertion failed: {e}")

    # Generate timestamp matching the database entry format
    timestamp = datetime.utcnow().isoformat()[:-3] + "Z"

    # Construct response payload
    response_payload = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": s_llm,
        "slv_score": s_slv,
        "ttr_score": s_ttr,
        "label_title": label_title,
        "label_body": label_body,
        "status": "classified"
    }
    
    return jsonify(response_payload), 200

@app.route("/appeal", methods=["POST"])
def appeal_classification():
    """
    POST /appeal
    Accepts a JSON payload containing:
    - content_id: str (UUIDv4 of the target submission)
    - creator_reasoning: str (creator reasoning text)
    
    Validates input, updates submission status to "under_review", 
    stores reasoning, and returns confirmation.
    """
    # Validate request content type
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
        
    data = request.get_json()
    
    content_id = data.get("content_id")
    creator_reasoning = data.get("creator_reasoning")
    
    # Validate required parameters
    if not content_id or not isinstance(content_id, str):
        return jsonify({"error": "Missing or invalid parameter: 'content_id' (must be a non-empty string)"}), 400
        
    if not creator_reasoning or not isinstance(creator_reasoning, str):
        return jsonify({"error": "Missing or invalid parameter: 'creator_reasoning' (must be a non-empty string)"}), 400

    # Register the appeal in the database
    try:
        updated = register_appeal(content_id, creator_reasoning)
        if not updated:
            return jsonify({"error": f"Content ID '{content_id}' not found in database"}), 404
            
        return jsonify({
            "message": "Appeal received",
            "content_id": content_id,
            "status": "under_review"
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Database mutation failed", "message": str(e)}), 500

@app.route("/log", methods=["GET"])
def get_log():
    """
    GET /log
    Returns the most recent audit log entries from the database.
    """
    try:
        entries = get_all_submissions()
        return jsonify({"entries": entries}), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve logs", "message": str(e)}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """
    Custom error handler for HTTP 429 Too Many Requests (Rate limit exceeded).
    """
    return jsonify({
        "error": "Too Many Requests",
        "message": f"Rate limit exceeded: {e.description}"
    }), 429

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "message": str(error)}), 400

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal server error", "message": str(error)}), 500

if __name__ == "__main__":
    # Start the Flask app on port 5000 in debug mode for local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
