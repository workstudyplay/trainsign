import { useState, useEffect } from 'react';
import { Play, Square, Send } from 'lucide-react';
import StopsSelector from './components/StopsSelector';
import ArrivalsPanel from './components/ArrivalsPanel';
import DisplayControl from './components/DisplayControl';
import AnimationsSelector from './components/AnimationsSelector';

import { API_BASE } from "./const"

export default function RGBMatrixController() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    async function loadConfig() {
      try {
        const response = await fetch(`${API_BASE}/api/config`);
        if (response.ok) {
          const data = await response.json();
          setIsPlaying(data.running || false);
        }
      } catch (error) {
        console.error('Error loading config:', error);
      }
    }
    loadConfig();
  }, []);

  const sendMessage = async () => {
    if (!message.trim()) return;
    
    // Simulate API call
    setStatus('Sending message...');
    console.log("Sending message:", message);
    try {
        const response = await fetch(`${API_BASE}api/message`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ message })
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        } else {
          console.log("Message sent successfully");
          setStatus('Message sent successfully!');
          setMessage('');
          setTimeout(() => setStatus(''), 3000);
        }
      } catch (error:unknown) {
        setStatus(`Error sending message: ${error as Error}.message}`);
        setTimeout(() => setStatus(''), 5000);
        return;
      }
    
  };

  const togglePlayback = async () => {
    try {
      const endpoint = isPlaying ? '/api/playback/stop' : '/api/playback/start';
      const response = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
      if (response.ok) {
        setIsPlaying(!isPlaying);
        setStatus(isPlaying ? 'Switched to train arrivals' : 'Playing scripts');
      } else {
        setStatus('Error toggling playback');
      }
    } catch (error) {
      setStatus('Error connecting to server');
      console.error('Error toggling playback:', error);
    }
    setTimeout(() => setStatus(''), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-800 rounded-lg shadow-2xl p-6 mb-6">
          <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
            
            TRAINSIGN.nyc
          </h1>
        </div>

        {/* Status Bar */}
        {status && (
          <div className="bg-green-600 text-white px-4 py-3 rounded-lg mb-6 shadow-lg">
            {status}
          </div>
        )}

        {/* Display Control */}
        <div className="mb-6">
          <DisplayControl />
        </div>

        {/* Broadcast Message */}
        <div className="bg-gray-800 rounded-lg shadow-xl p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Broadcast Message</h2>
          <div className="flex gap-3">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Enter message to display..."
              className="flex-1 bg-gray-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <button
              onClick={sendMessage}
              className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg flex items-center gap-2 transition-colors"
            >
              <Send size={20} />
              Send
            </button>
          </div>
        </div>

        {/* Station Selection */}
        <div className="mb-6">
          <StopsSelector />
        </div>

        {/* Train Arrivals */}
        <div className="mb-6">
          <ArrivalsPanel />
        </div>

        {/* Animations */}
        <div className="mb-6">
          <AnimationsSelector onStatusChange={setStatus} />
        </div>

        {/* Playback Control */}
        <div className="bg-gray-800 rounded-lg shadow-xl p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold text-white">Playback</h2>
              <p className="text-sm text-gray-400">
                {isPlaying ? 'Playing animations on display' : 'Showing train arrivals'}
              </p>
            </div>
            <button
              onClick={togglePlayback}
              className={`${
                isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
              } text-white px-6 py-3 rounded-lg flex items-center gap-2 transition-colors`}
            >
              {isPlaying ? <Square size={18} /> : <Play size={18} />}
              {isPlaying ? 'Stop' : 'Start Animations'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}