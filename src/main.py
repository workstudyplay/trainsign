"""
RGB Matrix Web API Service
Can be imported and controlled from main.py
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import subprocess
import threading
import time
import os
from typing import Optional, List, Dict, Callable
from transit.worker import load_stop_data, MTAWorker, DataBuffers
from config import load_selected_stops, save_selected_stops, load_scripts, save_scripts
from display import DisplayRenderer

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")
ASSETS_DIR = os.path.join(WEB_DIR, "assets")

class StopWorkersManager:
    """Manages MTAWorker instances for configured stops"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.workers: Dict[str, MTAWorker] = {}
        self.buffers: Dict[str, DataBuffers] = {}
        self.stops_data: Dict = {}
        self._load_stops_data()

    def _load_stops_data(self):
        """Load all stops data from file"""
        stops_file = os.path.join(os.path.dirname(__file__), 'transit', 'data', 'stops.txt')
        self.stops_data = load_stop_data(stops_file)

    def start_workers(self, stop_ids: List[str]):
        """Start workers for the given stop IDs"""
        # Stop any workers that are no longer needed
        current_ids = set(self.workers.keys())
        new_ids = set(stop_ids)

        for stop_id in current_ids - new_ids:
            self._stop_worker(stop_id)

        # Start workers for new stops
        for stop_id in new_ids - current_ids:
            self._start_worker(stop_id)

    def _start_worker(self, stop_id: str):
        """Start a worker for a specific stop"""
        if stop_id in self.workers:
            return

        if stop_id not in self.stops_data:
            print(f"Stop {stop_id} not found in stops data")
            return

        buffers = DataBuffers()
        worker = MTAWorker(
            stops=self.stops_data,
            configured_stop_ids=[stop_id],
            refresh_s=30.0,
            api_key=self.api_key,
            buffers=buffers,
            name=f"worker-{stop_id}",
        )
        worker.start()

        self.workers[stop_id] = worker
        self.buffers[stop_id] = buffers
        print(f"Started worker for stop {stop_id}")

    def _stop_worker(self, stop_id: str):
        """Stop a worker for a specific stop"""
        if stop_id not in self.workers:
            return

        worker = self.workers[stop_id]
        worker.stop()
        del self.workers[stop_id]
        del self.buffers[stop_id]
        print(f"Stopped worker for stop {stop_id}")

    def get_stop_names(self) -> Dict[str, str]:
        """Get stop names for all configured stops"""
        return {
            stop_id: self.stops_data[stop_id].name if stop_id in self.stops_data else stop_id
            for stop_id in self.buffers.keys()
        }

    def get_arrivals(self) -> Dict:
        """Get arrivals for all configured stops"""
        result = {}
        for stop_id, buffers in self.buffers.items():
            lines, data = buffers.snapshot()
            stop_info = self.stops_data.get(stop_id)
            result[stop_id] = {
                'stop_name': stop_info.name if stop_info else stop_id,
                'lines': lines,
                'arrivals': data,
            }
        return result

    def stop_all(self):
        """Stop all workers"""
        for stop_id in list(self.workers.keys()):
            self._stop_worker(stop_id)


class MatrixController:
    """Controller for managing RGB matrix script playback"""
    
    def __init__(self, script_runner: Optional[Callable] = None):
        """
        Initialize the controller
        
        Args:
            script_runner: Optional custom function to run scripts.
                         Signature: script_runner(script_name: str, duration: int)
                         If None, uses default subprocess runner
        """
        self.running = False
        self.current_script = None
        self.thread = None
        self.scripts = []
        self.script_runner = script_runner or self._default_script_runner
        self.message_file = 'broadcast_message.txt'
        self.message_callback = None
        self.load_config()
    
    def set_message_callback(self, callback: Callable[[str], None]):
        """
        Set a callback function for when messages are broadcast
        
        Args:
            callback: Function that takes a message string
        """
        self.message_callback = callback
    
    def _default_script_runner(self, script_name: str, duration: int):
        """Default script runner using subprocess"""
        # Scripts are in the animations folder
        animations_dir = os.path.join(os.path.dirname(__file__), 'animations')
        script_path = os.path.join(animations_dir, script_name)

        try:
            process = subprocess.Popen(['python3', script_path])
            start_time = time.time()

            while time.time() - start_time < duration and self.running:
                time.sleep(0.1)

            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        except Exception as e:
            print(f"Error running {script_name}: {e}")

    @staticmethod
    def list_available_animations() -> List[Dict]:
        """List all available animation scripts"""
        animations_dir = os.path.join(os.path.dirname(__file__), 'animations')
        animations = []

        if os.path.exists(animations_dir):
            for filename in sorted(os.listdir(animations_dir)):
                if filename.endswith('.py') and not filename.startswith('__'):
                    animations.append({
                        'name': filename,
                        'display_name': filename.replace('.py', '').replace('_', ' ').title()
                    })

        return animations
    
    def load_config(self):
        """Load configuration from file"""
        self.scripts = load_scripts()

    def save_config(self):
        """Save configuration to file"""
        save_scripts(self.scripts)
    
    def run_loop(self):
        """Main loop that runs scripts in sequence"""
        while self.running:
            enabled_scripts = [s for s in self.scripts if s['enabled']]
            
            if not enabled_scripts:
                time.sleep(1)
                continue
            
            for script in enabled_scripts:
                if not self.running:
                    break
                
                self.current_script = script['name']
                self.script_runner(script['name'], script['duration'])
    
    def start(self):
        """Start the playback loop"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_loop, daemon=True)
            self.thread.start()
            return True
        return False
    
    def stop(self):
        """Stop the playback loop"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            self.current_script = None
            return True
        return False
    
    def get_status(self) -> Dict:
        """Get current status"""
        enabled_count = sum(1 for s in self.scripts if s['enabled'])
        total_duration = sum(s['duration'] for s in self.scripts if s['enabled'])
        
        return {
            'running': self.running,
            'current_script': self.current_script,
            'active_scripts': enabled_count,
            'total_scripts': len(self.scripts),
            'loop_duration': total_duration
        }




class WebAPIService:
    """Flask web API service for RGB matrix control"""

    def __init__(self, controller: MatrixController, host='0.0.0.0', port=5002, api_key: str = ""):
        """
        Initialize the web API service

        Args:
            controller: MatrixController instance to control
            host: Host to bind to
            port: Port to listen on
            api_key: MTA API key for transit data
        """
        self.controller = controller
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        self.workers_manager = StopWorkersManager(api_key=api_key)
        self.display_renderer = DisplayRenderer(display_duration=5.0)
        self._setup_routes()
        self.server_thread = None
        self._running = False

        # Start workers for configured stops
        selected_stops = load_selected_stops()
        if selected_stops:
            self.workers_manager.start_workers(selected_stops)
            self._update_display_buffers()
            self.display_renderer.start()

    def _update_display_buffers(self):
        """Update display renderer with current worker buffers"""
        self.display_renderer.set_buffers(
            self.workers_manager.buffers,
            self.workers_manager.get_stop_names()
        )

    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            return jsonify({
                'scripts': self.controller.scripts,
                'running': self.controller.running,
                'current_script': self.controller.current_script
            })
        
        @self.app.route('/api/config', methods=['POST'])
        def update_config():
            data = request.json
            self.controller.scripts = data.get('scripts', self.controller.scripts)
            self.controller.save_config()
            return jsonify({'status': 'success'})
        
        @self.app.route('/api/scripts', methods=['POST'])
        def add_script():
            data = request.json
            new_script = {
                'id': int(time.time() * 1000),
                'name': data['name'],
                'enabled': data.get('enabled', True),
                'duration': data.get('duration', 10)
            }
            self.controller.scripts.append(new_script)
            self.controller.save_config()
            return jsonify(new_script)
        
        @self.app.route('/api/scripts/<int:script_id>', methods=['DELETE'])
        def delete_script(script_id):
            self.controller.scripts = [
                s for s in self.controller.scripts if s['id'] != script_id
            ]
            self.controller.save_config()
            return jsonify({'status': 'success'})

        @self.app.route('/api/animations', methods=['GET'])
        def list_animations():
            """List all available animation scripts"""
            available = self.controller.list_available_animations()
            # Mark which ones are currently enabled
            enabled_names = {s['name'] for s in self.controller.scripts if s.get('enabled')}
            configured_names = {s['name'] for s in self.controller.scripts}

            for anim in available:
                anim['enabled'] = anim['name'] in enabled_names
                anim['configured'] = anim['name'] in configured_names
                # Find the config entry if it exists
                for s in self.controller.scripts:
                    if s['name'] == anim['name']:
                        anim['id'] = s.get('id')
                        anim['duration'] = s.get('duration', 10)
                        break
                else:
                    anim['duration'] = 10

            return jsonify(available)
        
        @self.app.route('/api/playback/start', methods=['POST'])
        def start_playback():
            # Stop train arrivals display and start script playback
            self.display_renderer.stop()
            self.controller.start()
            return jsonify({'status': 'started', 'mode': 'scripts'})

        @self.app.route('/api/playback/stop', methods=['POST'])
        def stop_playback():
            # Stop script playback and resume train arrivals display
            self.controller.stop()
            self._update_display_buffers()
            self.display_renderer.start()
            return jsonify({'status': 'stopped', 'mode': 'arrivals'})
        
        @self.app.route('/api/message', methods=['POST'])
        def broadcast_message():
            data = request.json
            message = data.get('message', '')
            duration = data.get('duration', 10.0)
            print("|--- Broadcast message: -----------------------------------------|")
            print(message)
            print("|----------------------------------------------------------------|")
            # Save to file
            with open(self.controller.message_file, 'w') as f:
                f.write(message)

            # Show scrolling message on display
            if message and self.display_renderer.running:
                self.display_renderer.show_broadcast(message, duration=duration)

            # Call callback if set
            if self.controller.message_callback:
                try:
                    self.controller.message_callback(message)
                except Exception as e:
                    print(f"Error in message callback: {e}")

            return jsonify({'status': 'message sent', 'message': message})
        
        @self.app.get("/api/health")
        def health():
            return jsonify(ok=True)

        @self.app.get("/")
        def index():
            return send_from_directory(WEB_DIR, "index.html")

        # Catch-all for client-side routes (e.g. /settings, /users/123)
        @self.app.get("/<path:path>")
        def spa_catch_all(path: str):
            full_path = os.path.join(WEB_DIR, path)

            # If it's a real file (js/css/img/etc), serve it
            if os.path.isfile(full_path):
                return send_from_directory(WEB_DIR, path)

            # Otherwise serve index.html so the SPA router can handle it
            return send_from_directory(WEB_DIR, "index.html")

        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            return jsonify(self.controller.get_status())

        @self.app.route('/api/stops', methods=['GET'])
        def get_stops():
            """Return all directional stops (N/S) with coordinates"""
            stops_file = os.path.join(os.path.dirname(__file__), 'transit', 'data', 'stops.txt')
            all_stops = load_stop_data(stops_file)

            directional_stops = [
                {
                    'stop_id': stop.stop_id,
                    'stop_name': stop.name,
                    'lat': float(stop.lat),
                    'lon': float(stop.lon),
                    'line': stop.line,
                    'direction': 'Northbound' if stop.stop_id.endswith('N') else 'Southbound'
                }
                for stop in all_stops.values()
                if stop.stop_id.endswith('N') or stop.stop_id.endswith('S')
            ]

            return jsonify(directional_stops)

        @self.app.route('/api/selected-stops', methods=['GET'])
        def get_selected_stops():
            """Return user's saved stop selections"""
            selected_ids = load_selected_stops()
            return jsonify({'selected_stops': selected_ids})

        @self.app.route('/api/selected-stops', methods=['POST'])
        def save_selected_stops_endpoint():
            """Save user's stop selections and restart workers"""
            data = request.json
            stop_ids = data.get('selected_stops', [])

            if not isinstance(stop_ids, list):
                return jsonify({'error': 'selected_stops must be a list'}), 400

            save_selected_stops(stop_ids)
            # Restart workers for the new stop selection
            self.workers_manager.start_workers(stop_ids)
            # Update display renderer with new buffers
            self._update_display_buffers()
            # Start display if not already running
            if stop_ids and not self.display_renderer.running:
                self.display_renderer.start()
            elif not stop_ids and self.display_renderer.running:
                self.display_renderer.stop()
            return jsonify({'status': 'success', 'selected_stops': stop_ids})

        @self.app.route('/api/arrivals', methods=['GET'])
        def get_arrivals():
            """Return current arrivals for all configured stops"""
            arrivals = self.workers_manager.get_arrivals()
            return jsonify(arrivals)

        @self.app.route('/api/display/start', methods=['POST'])
        def start_display():
            """Start the display renderer"""
            self._update_display_buffers()
            self.display_renderer.start()
            return jsonify({'status': 'started', 'running': True})

        @self.app.route('/api/display/stop', methods=['POST'])
        def stop_display():
            """Stop the display renderer"""
            self.display_renderer.stop()
            return jsonify({'status': 'stopped', 'running': False})

        @self.app.route('/api/display/status', methods=['GET'])
        def display_status():
            """Get display renderer status"""
            return jsonify({
                'running': self.display_renderer.running,
                'stops_count': len(self.display_renderer.buffers)
            })

    def start(self, blocking=False):
        """
        Start the web API service
        
        Args:
            blocking: If True, runs in current thread. If False, runs in background thread.
        """
        if self._running:
            print("Web API service already running")
            return
        
        self._running = True
        
        if blocking:
            print(f"Starting Web API on http://{self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        else:
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(
                    host=self.host, 
                    port=self.port, 
                    debug=False, 
                    use_reloader=False
                ),
                daemon=True
            )
            self.server_thread.start()
            print(f"Web API service started on http://{self.host}:{self.port}")
    
    def stop(self):
        """Stop the web API service"""
        self._running = False
        # Note: Flask doesn't have a built-in graceful shutdown in development mode
        # For production, use a proper WSGI server like gunicorn
        print("Web API service stopped")


# Convenience function for simple usage
def create_service(script_runner=None, host='0.0.0.0', port=5002, api_key: str = ""):
    """
    Create and return a WebAPIService instance

    Args:
        script_runner: Optional custom script runner function
        host: Host to bind to
        port: Port to listen on
        api_key: MTA API key for transit data

    Returns:
        WebAPIService instance
    """
    controller = MatrixController(script_runner=script_runner)
    service = WebAPIService(controller, host=host, port=port, api_key=api_key)
    return service


if __name__ == '__main__':
    # Standalone mode
    os.makedirs('scripts', exist_ok=True)
    service = create_service()
    service.start(blocking=True)