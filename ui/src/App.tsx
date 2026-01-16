import { useState } from 'react';
import { Train, Settings, Send, ChevronDown } from 'lucide-react';
import StopsSelector from './components/StopsSelector';
import ArrivalsPanel from './components/ArrivalsPanel';
import DisplayControl from './components/DisplayControl';
import AnimationsSelector from './components/AnimationsSelector';

import { API_BASE } from "./const"

type Tab = 'home' | 'settings';

const PRESET_MESSAGES = [
  { label: 'Hello :)', value: 'Hello :)' },
  { label: 'Welcome!', value: 'Welcome!' },
  { label: 'Have a great day!', value: 'Have a great day!' },
  { label: 'Good morning :)', value: 'Good morning :)' },
  { label: 'Good night *_*', value: 'Good night *_*' },
  { label: 'Party time!!!', value: '*** PARTY TIME ***' },
  { label: 'Be right back', value: 'BRB...' },
  { label: 'Love NYC <3', value: 'I <3 NYC' },
  { label: 'Go team!', value: '>>> GO TEAM! <<<' },
  { label: 'Testing 123', value: 'Testing 1 2 3...' },
];

export default function RGBMatrixController() {
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('');

  const sendMessage = async () => {
    if (!message.trim()) return;

    setStatus('Sending message...');
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
        setStatus('Message sent!');
        setMessage('');
        setTimeout(() => setStatus(''), 3000);
      }
    } catch (error: unknown) {
      setStatus(`Error: ${(error as Error).message}`);
      setTimeout(() => setStatus(''), 5000);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex flex-col">
      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-6 pb-20">
        <div className="w-full">
          {/* Status Bar */}
          {status && (
            <div className="bg-green-600 text-white px-3 py-2 rounded-lg mb-4 shadow-lg text-sm">
              {status}
            </div>
          )}

          {activeTab === 'home' && (
            <div className="w-full space-y-4">
              {/* Broadcast Message */}
              <div className="bg-gray-800 rounded-lg shadow-xl p-4">
                <div className="space-y-3">
                  {/* Preset message selector */}
                  <div className="relative">
                    <select
                      onChange={(e) => {
                        if (e.target.value) {
                          setMessage(e.target.value);
                        }
                      }}
                      value=""
                      className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm appearance-none cursor-pointer"
                    >
                      <option value="">Quick messages...</option>
                      {PRESET_MESSAGES.map((preset) => (
                        <option key={preset.label} value={preset.value}>
                          {preset.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>

                  {/* Custom message input */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder="Or type custom message..."
                      className="flex-1 bg-gray-700 text-white px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
                    />
                    <button
                      onClick={sendMessage}
                      className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                    >
                      <Send size={18} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Train Arrivals */}
              <div className="w-full">
                <ArrivalsPanel />
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <>
              {/* Display Control */}
              <div className="mb-4">
                <DisplayControl />
              </div>

              {/* Station Selection */}
              <div className="mb-4">
                <StopsSelector />
              </div>

              {/* Animations */}
              {/* <div className="mb-4">
                <AnimationsSelector onStatusChange={setStatus} />
              </div> */}
            </>
          )}
        </div>
      </div>

      {/* Bottom Tab Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-700 safe-area-bottom">
        <div className="flex">
          <button
            onClick={() => setActiveTab('home')}
            className={`flex-1 flex flex-col items-center py-3 transition-colors ${
              activeTab === 'home' ? 'text-purple-400' : 'text-gray-500'
            }`}
          >
            <Train size={24} />
            <span className="text-xs mt-1">Trains</span>
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex-1 flex flex-col items-center py-3 transition-colors ${
              activeTab === 'settings' ? 'text-purple-400' : 'text-gray-500'
            }`}
          >
            <Settings size={24} />
            <span className="text-xs mt-1">Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
}
