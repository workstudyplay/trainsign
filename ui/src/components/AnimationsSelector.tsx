import { useState, useEffect } from 'react';
import { Loader2, Save, GripVertical } from 'lucide-react';

import { API_BASE } from "../const"

interface Animation {
  name: string;
  display_name: string;
  enabled: boolean;
  configured: boolean;
  id?: number;
  duration: number;
}

interface Props {
  onStatusChange?: (message: string) => void;
}

export default function AnimationsSelector({ onStatusChange }: Props) {
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchAnimations();
  }, []);

  const fetchAnimations = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/animations`);
      if (response.ok) {
        const data = await response.json();
        setAnimations(data);
      }
    } catch (error) {
      console.error('Error fetching animations:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleAnimation = (name: string) => {
    setAnimations(animations.map(a =>
      a.name === name ? { ...a, enabled: !a.enabled } : a
    ));
  };

  const updateDuration = (name: string, duration: number) => {
    setAnimations(animations.map(a =>
      a.name === name ? { ...a, duration } : a
    ));
  };

  const saveConfig = async () => {
    setSaving(true);
    onStatusChange?.('Saving animations...');

    // Build scripts array from animations
    const scripts = animations
      .filter(a => a.enabled || a.configured)
      .map((a, index) => ({
        id: a.id || Date.now() + index,
        name: a.name,
        enabled: a.enabled,
        duration: a.duration
      }));

    try {
      const response = await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scripts })
      });

      if (response.ok) {
        onStatusChange?.('Animations saved!');
        fetchAnimations(); // Refresh to get updated IDs
      } else {
        onStatusChange?.('Error saving animations');
      }
    } catch (error) {
      onStatusChange?.('Error saving animations');
      console.error('Error saving config:', error);
    } finally {
      setSaving(false);
      setTimeout(() => onStatusChange?.(''), 3000);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-xl p-4 sm:p-6">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="animate-spin" size={20} />
          Loading animations...
        </div>
      </div>
    );
  }

  const enabledCount = animations.filter(a => a.enabled).length;
  const totalDuration = animations.filter(a => a.enabled).reduce((sum, a) => sum + a.duration, 0);

  return (
    <div className="bg-gray-800 rounded-lg shadow-xl p-4 sm:p-6">
      <div className="flex justify-between items-center mb-3 sm:mb-4">
        <div>
          <h2 className="text-lg sm:text-xl font-semibold text-white">Animations</h2>
          <p className="text-xs sm:text-sm text-gray-400">
            {enabledCount} enabled · {totalDuration}s total
          </p>
        </div>
        <button
          onClick={saveConfig}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-3 sm:px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
        >
          {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
          Save
        </button>
      </div>

      <div className="space-y-2">
        {animations.map((animation) => (
          <div
            key={animation.name}
            className={`bg-gray-700 rounded-lg p-3 sm:p-4 flex items-center gap-2 sm:gap-3 ${
              animation.enabled ? 'ring-1 ring-purple-500' : ''
            }`}
          >
            <GripVertical size={20} className="text-gray-500 hidden sm:block" />

            <input
              type="checkbox"
              checked={animation.enabled}
              onChange={() => toggleAnimation(animation.name)}
              className="w-5 h-5 rounded cursor-pointer accent-purple-500 flex-shrink-0"
            />

            <span className={`flex-1 text-sm sm:text-base ${animation.enabled ? 'text-white' : 'text-gray-500'}`}>
              {animation.display_name}
            </span>

            <div className="flex items-center gap-1 sm:gap-2">
              <input
                type="number"
                value={animation.duration}
                onChange={(e) => updateDuration(animation.name, parseInt(e.target.value) || 10)}
                className="w-14 sm:w-16 bg-gray-600 text-white px-2 py-1 rounded text-center text-sm"
                min="1"
              />
              <span className="text-gray-400 text-xs sm:text-sm">sec</span>
            </div>
          </div>
        ))}
      </div>

      {animations.length === 0 && (
        <p className="text-gray-400 text-center py-4 text-sm">No animations found in animations folder</p>
      )}
    </div>
  );
}
