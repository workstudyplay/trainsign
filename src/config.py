import json
import os
from typing import List, Dict, Any

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')


def _load_config() -> Dict[str, Any]:
    """Load the full config file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'scripts': [], 'selected_stops': []}


def _save_config(data: Dict[str, Any]) -> None:
    """Save the full config file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_selected_stops() -> List[str]:
    """Load selected stop IDs from config file"""
    config = _load_config()
    return config.get('selected_stops', [])


def save_selected_stops(stop_ids: List[str]) -> None:
    """Save selected stop IDs to config file"""
    config = _load_config()
    config['selected_stops'] = stop_ids
    _save_config(config)


def load_scripts() -> List[Dict[str, Any]]:
    """Load scripts from config file"""
    config = _load_config()
    return config.get('scripts', [])


def save_scripts(scripts: List[Dict[str, Any]]) -> None:
    """Save scripts to config file"""
    config = _load_config()
    config['scripts'] = scripts
    _save_config(config)
