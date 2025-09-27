import os
import uuid
import json
import time
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from prepare_kb import prepare_knowledge_base
import queue

app = Flask(__name__)
CORS(app)

TEMP_BASE_DIR = os.path.abspath("temp_sessions")
os.makedirs(TEMP_BASE_DIR, exist_ok=True)


@app.route('/api/models', methods=['GET'])
def get_models():
    try:
        import tiktoken
        return jsonify(list(tiktoken.model.MODEL_TO_ENCODING.keys()))
    except ImportError:
        return jsonify(['gpt-4o', 'gpt-4', 'gpt-3.5-turbo'])


@app.route('/api/process', methods=['POST'])
def process_files_setup():
    """Sets up the processing job, saves files, and returns a session ID."""
    try:
        if 'config' not in request.form: return jsonify({"error": "Missing config"}), 400
        if 'files' not in request.files: return jsonify({"error": "Missing files"}), 400

        session_id = str(uuid.uuid4())
        session_dir = os.path.join(TEMP_BASE_DIR, session_id)
        source_dir = os.path.join(session_dir, 'source')
        output_dir = os.path.join(session_dir, 'output')
        os.makedirs(source_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        config_data = json.loads(request.form['config'])
        config_data.update({
            'source_directory': source_dir,
            'output_directory': output_dir,
            'report_path': os.path.join(output_dir, 'report.json')
        })
        with open(os.path.join(session_dir, 'config.json'), 'w') as f:
            json.dump(config_data, f)

        for file in request.files.getlist('files'):
            file.save(os.path.join(source_dir, file.filename))

        return jsonify({"session_id": session_id})
    except Exception as e:
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500


@app.route('/api/stream/<session_id>', methods=['GET'])
def stream_progress(session_id):
    """Streams the progress of the knowledge base preparation using SSE."""

    def event_stream():
        q = queue.Queue()

        def progress_callback(data):
            q.put(data)

        # This should run in a separate thread, but for simplicity, we'll
        # run it and then process the queue. A better implementation
        # would use threading or a different async framework.

        # A simple generator that yields from the queue
        def generate_events():
            # Load config
            session_dir = os.path.join(TEMP_BASE_DIR, session_id)
            config_path = os.path.join(session_dir, 'config.json')
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # This is a simplified example of how you might need to run the
            # heavy task in a background thread to not block.
            # For this case, we will just call it and it will block.

            # The callback will put messages on the queue
            report = prepare_knowledge_base(config_data, progress_callback=progress_callback)

            # Put a final message on the queue
            output_dir = config_data['output_directory']
            download_links = [f"/api/download/{session_id}/{f}" for f in os.listdir(output_dir) if f.endswith('.pdf')]
            q.put({
                'type': 'complete',
                'report': report,
                'download_links': download_links
            })

        from threading import Thread
        thread = Thread(target=generate_events)
        thread.start()

        while True:
            try:
                data = q.get()  # Blocks until an item is available
                if 'type' in data and data['type'] == 'complete':
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                else:
                    event_data = {**data, 'type': 'progress'}
                    yield f"data: {json.dumps(event_data)}\n\n"
            except queue.Empty:
                time.sleep(0.1)

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id, filename):
    directory = os.path.join(TEMP_BASE_DIR, session_id, 'output')
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, port=5001)

