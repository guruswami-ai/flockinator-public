"""Validate reported scripted-world positions without inventing missing data."""
import math
from node_commissioner.protocol import validate_status

STATES = ("HOLD", "SCAN", "SEEN", "SHARE", "CHECK", "DOUBT", "EVENT", "LOST", "MARK", "CRASH", "EMPTY", "NOLINK", "ALERT", "PRIORITY", "CLAIM", "ASSIGN", "YIELD", "LOITER", "R2B", "LAND", "CHARGE", "STANDBY", "FRIEND", "TARGET", "DEPLOY", "APPROVED", "ORDERS", "TAKEOFF", "BLANK", "READY")

# Older firmware uses the same numeric slots with historical presentation names.
LEGACY_STATES = {"ENGAGE": "EVENT", "KILL": "MARK"}

def project(index, status, mac, label):
    validate_status(status, mac, label)
    if not 0 <= index < 16:
        raise ValueError('invalid node index')
    panel = status.get('panel')
    mission = status.get('mission')
    if not isinstance(panel, dict) or not isinstance(mission, dict):
        return None
    world = panel.get('world')
    if not isinstance(world, dict) or world.get('source') != 'scripted_mission_shared_world' or mission.get('source') != 'scripted_simulation':
        return None
    pos = world.get('position')
    heading = world.get('heading')
    if not isinstance(pos, list) or len(pos) != 3 or any(type(n) not in (int, float) or not math.isfinite(n) or abs(n) > 100000 for n in pos):
        raise ValueError('invalid world position')
    if type(heading) not in (int, float) or not math.isfinite(heading) or not 0 <= heading <= 360:
        raise ValueError('invalid heading')
    if world.get('freshness') not in ('LIVE', 'STALE', 'RESYNC') or type(mission.get('running')) is not bool:
        raise ValueError('invalid mission state')
    state=mission.get('state')
    if isinstance(state, str):
        state = LEGACY_STATES.get(state, state)
    if state not in STATES:
        raise ValueError('invalid mission state')
    return {'state':STATES.index(state), 'index':index, 'position':tuple(pos), 'heading':heading,
            'freshness':world['freshness'], 'running':mission['running'], 'source':'scripted_simulation'}
