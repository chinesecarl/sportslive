# /// script
# dependencies = ["requests", "pytz", "rich>=13.0.0"]
# ///

import sys, os, time, re, pytz, requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich import box

console = Console()
TZ = pytz.timezone('Europe/Berlin')
# Cloud deploy: https://github.com/chinesecarl/sportslive
ET = pytz.timezone('US/Eastern')

REFRESH_SECONDS = 30
MAX_RETRIES = 3
CACHE_TTL = 300
# Load .env file (Render Secret File / local fallback)
for _dotenv_path in ('.env', '/etc/secrets/.env', '/etc/secrets/env'):
    if os.path.exists(_dotenv_path):
        with open(_dotenv_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#'):
                    _k, _, _v = _line.partition('=')
                    os.environ.setdefault(_k.strip(), _v.strip())

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
RUNDOWN_API_KEY = os.getenv("RUNDOWN_API_KEY", "")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")

THEME = {
    "accent":   "#87AFFF",
    "live":     "#5FFF87",
    "home":     "#00FFAA",
    "away":     "#FFAA00",
    "text":     "#E0E0E0",
    "muted":    "#949494",
    "dim":      "#5A5A5A",
    "border":   "#3A3A3A",
    "alt_row":  "#1E1E1E",
    "error":    "#FF6B6B",
}

ODDS_SPORT_MAP = {
    "soccer/eng.1": "soccer_epl",
    "soccer/ger.1": "soccer_germany_bundesliga",
    "soccer/esp.1": "soccer_spain_la_liga",
    "soccer/uefa.champions": "soccer_uefa_champions_league",
    "soccer/den.1": "soccer_denmark_superliga",
    "basketball/nba": "basketball_nba",
    "football/nfl": "americanfootball_nfl",
    "soccer/fifa.world": "soccer_fifa_world_cup",
}

RUNDOWN_SOCCER_IDS = {
    "soccer/esp.1": 12,
    "soccer/ger.1": 11,
    "soccer/eng.1": 10,
    "soccer/uefa.champions": 15,
    "soccer/den.1": 16,
}

LEAGUES = {
    "1": ("soccer/eng.1", "Premier League", True, False),
    "2": ("soccer/ger.1", "Bundesliga", True, False),
    "3": ("soccer/esp.1", "La Liga", True, False),
    "4": ("soccer/uefa.champions", "Champions League", True, False),
    "5": ("soccer/den.1", "Superliga", True, False),
}
SPORTS = {
    "nba": ("basketball/nba", "NBA", False, False),
    "nfl": ("football/nfl", "NFL", False, False),
    "f1":  ("racing/f1", "Formula 1", False, True),
    "wc":  ("soccer/fifa.world", "FIFA World Cup", True, False),
}
SHOW_ALL_SPORTS = {"soccer/fifa.world"}

ABBR_FLAG = {
    "ARG":"🇦🇷","BOL":"🇧🇴","BRA":"🇧🇷","CHI":"🇨🇱","COL":"🇨🇴","ECU":"🇪🇨",
    "PAR":"🇵🇾","PER":"🇵🇪","URU":"🇺🇾","VEN":"🇻🇪",
    "CAN":"🇨🇦","CRC":"🇨🇷","CUB":"🇨🇺","DOM":"🇩🇴","SLV":"🇸🇻","GUA":"🇬🇹",
    "HAI":"🇭🇹","HON":"🇭🇳","JAM":"🇯🇲","MEX":"🇲🇽","NCA":"🇳🇮","PAN":"🇵🇦",
    "TRI":"🇹🇹","USA":"🇺🇸",
    "ALB":"🇦🇱","AND":"🇦🇩","ARM":"🇦🇲","AUT":"🇦🇹","AZE":"🇦🇿","BEL":"🇧🇪",
    "BIH":"🇧🇦","BUL":"🇧🇬","CRO":"🇭🇷","CYP":"🇨🇾","CZE":"🇨🇿","DEN":"🇩🇰",
    "ENG":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","ESP":"🇪🇸","EST":"🇪🇪",
    "FIN":"🇫🇮","FRA":"🇫🇷","GEO":"🇬🇪","GER":"🇩🇪","GRE":"🇬🇷","HUN":"🇭🇺",
    "ISL":"🇮🇸","IRL":"🇮🇪","ISR":"🇮🇱","ITA":"🇮🇹","KAZ":"🇰🇿","KOS":"🇽🇰",
    "LVA":"🇱🇻","LIE":"🇱🇮","LTU":"🇱🇹","LUX":"🇱🇺","MLT":"🇲🇹","MDA":"🇲🇩",
    "MNE":"🇲🇪","NED":"🇳🇱","MKD":"🇲🇰","NIR":"🇬🇧","NOR":"🇳🇴",
    "WAL":"🏴󠁧󠁢󠁷󠁬󠁳󠁿","POL":"🇵🇱","POR":"🇵🇹",
    "ROU":"🇷🇴","RUS":"🇷🇺","SCO":"🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "SMR":"🇸🇲","SRB":"🇷🇸","SVK":"🇸🇰","SVN":"🇸🇮",
    "SWE":"🇸🇪","SUI":"🇨🇭","TUR":"🇹🇷","UKR":"🇺🇦",
    "ALG":"🇩🇿","ANG":"🇦🇴","BEN":"🇧🇯","BOT":"🇧🇼","BFA":"🇧🇫","BDI":"🇧🇮",
    "CMR":"🇨🇲","CPV":"🇨🇻","CHA":"🇹🇩","CGO":"🇨🇬","COD":"🇨🇩","CIV":"🇨🇮",
    "EGY":"🇪🇬","ETH":"🇪🇹","GAB":"🇬🇦","GHA":"🇬🇭","GUI":"🇬🇳","KEN":"🇰🇪",
    "LBY":"🇱🇾","MAD":"🇲🇬","MLI":"🇲🇱","MAR":"🇲🇦","MRI":"🇲🇺","MOZ":"🇲🇿",
    "NAM":"🇳🇦","NGA":"🇳🇬","RSA":"🇿🇦","SEN":"🇸🇳","SLE":"🇸🇱","SDN":"🇸🇩",
    "TAN":"🇹🇿","TOG":"🇹🇬","TUN":"🇹🇳","UGA":"🇺🇬","ZAM":"🇿🇲","ZIM":"🇿🇼",
    "AUS":"🇦🇺","BHR":"🇧🇭","CHN":"🇨🇳","HKG":"🇭🇰","IND":"🇮🇳","IDN":"🇮🇩",
    "IRN":"🇮🇷","IRQ":"🇮🇶","JPN":"🇯🇵","JOR":"🇯🇴","PRK":"🇰🇵","KOR":"🇰🇷",
    "KSA":"🇸🇦","KUW":"🇰🇼","LIB":"🇱🇧","MAS":"🇲🇾","OMA":"🇴🇲","PAK":"🇵🇰",
    "PHI":"🇵🇭","QAT":"🇶🇦","SIN":"🇸🇬","SRI":"🇱🇰","SYR":"🇸🇾","THA":"🇹🇭",
    "UAE":"🇦🇪","UZB":"🇺🇿","VIE":"🇻🇳",
    "NZL":"🇳🇿","FIJ":"🇫🇯",
}

_odds_cache = {}
_odds_cache_time = {}
_rundown_cache = {}
_rundown_cache_time = {}
_football_data_cache = {}
_football_data_cache_time = {}
_espn_cache = {}
_espn_cache_time = {}
_prob_cache = {}
_prob_cache_time = {}
_session = requests.Session()

def _get(url, timeout=5, headers=None):
    return _session.get(url, timeout=timeout, headers=headers or {})

def fetch(path, st_off=-1, end_off=365):
    dt = lambda d: (datetime.now() + timedelta(days=d)).strftime('%Y%m%d')
    cache_key = f"{path}:{dt(st_off)}-{dt(end_off)}"
    now = time.time()
    if cache_key in _espn_cache and now - _espn_cache_time.get(cache_key, 0) < CACHE_TTL:
        return _espn_cache[cache_key]
    url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={dt(st_off)}-{dt(end_off)}&limit=150"
    try:
        res = _get(url)
        if res.status_code == 400 and end_off > 30:
            res = _get(url.replace(dt(end_off), dt(30)))
        res.raise_for_status()
        result = (res.json().get('events', []), None)
        _espn_cache[cache_key] = result
        _espn_cache_time[cache_key] = now
        return result
    except Exception as e:
        return None, f"System Error: {e}"

def fetch_odds(sport_key):
    if not ODDS_API_KEY or sport_key not in ODDS_SPORT_MAP:
        return {}
    now = time.time()
    if sport_key in _odds_cache and now - _odds_cache_time.get(sport_key, 0) < CACHE_TTL:
        return _odds_cache[sport_key]
    try:
        api_sport = ODDS_SPORT_MAP[sport_key]
        url = (f"https://api.the-odds-api.com/v4/sports/{api_sport}/odds/"
               f"?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal")
        res = _get(url)
        if res.status_code != 200:
            return {}
        cache = {}
        for event in res.json():
            home = event.get('home_team', '').upper()
            away = event.get('away_team', '').upper()
            key = f"{home} vs {away}"
            all_outcomes = []
            for bm in event.get('bookmakers', []):
                for market in bm.get('markets', []):
                    if market['key'] == 'h2h':
                        outcomes = {o['name'].upper(): o['price'] for o in market['outcomes']}
                        all_outcomes.append(outcomes)
                        break
            if all_outcomes:
                avg = {}
                for outcome in all_outcomes:
                    for team, price in outcome.items():
                        if team not in avg:
                            avg[team] = []
                        avg[team].append(price)
                final = {team: sum(prices)/len(prices) for team, prices in avg.items()}
                cache[key] = final
                nk = f"{normalize_name(home)} vs {normalize_name(away)}"
                if nk != key:
                    cache[nk] = final
        _odds_cache[sport_key] = cache
        _odds_cache_time[sport_key] = now
        return cache
    except Exception:
        return {}

def fetch_rundown_odds(sport_key):
    if not RUNDOWN_API_KEY or sport_key not in RUNDOWN_SOCCER_IDS:
        return {}
    now = time.time()
    if sport_key in _rundown_cache and now - _rundown_cache_time.get(sport_key, 0) < CACHE_TTL:
        return _rundown_cache[sport_key]
    try:
        sport_id = RUNDOWN_SOCCER_IDS[sport_key]
        headers = {"Authorization": f"Bearer {RUNDOWN_API_KEY}"}
        dates = [(datetime.now(TZ) + timedelta(days=d)).strftime('%Y-%m-%d') for d in range(8)]

        def _fetch_day(date):
            url = f"https://therundown.io/api/v2/sports/{sport_id}/events/{date}"
            res = _get(url, headers=headers)
            return (date, res) if res.status_code == 200 else (date, None)

        cache = {}
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(_fetch_day, d) for d in dates]
            for fut in as_completed(futs):
                date, res = fut.result()
                if res is None:
                    continue
                for event in res.json().get('events', []):
                    teams = event.get('teams', [])
                    if len(teams) < 2:
                        continue
                    home = teams[0].get('name', '').upper()
                    away = teams[1].get('name', '').upper()
                    key = f"{home} vs {away}"
                    all_outcomes = []
                    for line in event.get('lines', []):
                        outcomes = {}
                        for participant in line.get('participants', []):
                            name = participant.get('name', '').upper()
                            price = participant.get('odds', {}).get('decimal')
                            if price:
                                outcomes[name] = price
                        if outcomes:
                            all_outcomes.append(outcomes)
                    if all_outcomes:
                        avg = {}
                        for outcome in all_outcomes:
                            for team, price in outcome.items():
                                if team not in avg:
                                    avg[team] = []
                                avg[team].append(price)
                        final = {team: sum(prices)/len(prices) for team, prices in avg.items()}
                        cache[key] = final
                        nk = f"{normalize_name(home)} vs {normalize_name(away)}"
                        if nk != key:
                            cache[nk] = final
        _rundown_cache[sport_key] = cache
        _rundown_cache_time[sport_key] = now
        return cache
    except Exception:
        return {}

def fetch_football_data_odds():
    if not FOOTBALL_DATA_API_KEY:
        return {}
    now = time.time()
    if 'bundesliga' in _football_data_cache and now - _football_data_cache_time.get('bundesliga', 0) < CACHE_TTL:
        return _football_data_cache['bundesliga']
    try:
        url = "https://api.football-data.org/v4/competitions/BL1/matches?status=SCHEDULED"
        headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
        res = _get(url, headers=headers)
        if res.status_code != 200:
            return {}
        cache = {}
        for match in res.json().get('matches', []):
            home = match['homeTeam']['name'].upper()
            away = match['awayTeam']['name'].upper()
            key = f"{home} vs {away}"
            cache[key] = {"exists": True}
        _football_data_cache['bundesliga'] = cache
        _football_data_cache_time['bundesliga'] = now
        return cache
    except Exception:
        return {}

def normalize_name(n):
    if not n:
        return ""
    n = n.upper().strip()
    for token in ["1. FC ", "FC ", "SC ", "TSG ", "RB ", "VFB ", "1. ", "2. ", "04 ", "1899 ", " DE ", "VFL ", "ST. ", "ST ", "BORUSSIA ", "BAYER ", "EINTRACHT ", "WERDER "]:
        n = n.replace(token, "")
    n = " ".join(n.split())
    mappings = {
        "HEIDENHEIM": "HEIDENHEIM",
        "UNION BERLIN": "UNION", "UNION": "UNION",
        "AUGSBURG": "AUGSBURG",
        "LEVERKUSEN": "LEVERKUSEN",
        "BAYERN": "BAYERN", "MUNICH": "BAYERN",
        "GLADBACH": "GLADBACH", "MONCHENGLADBACH": "GLADBACH",
        "HOFFENHEIM": "HOFFENHEIM",
        "FREIBURG": "FREIBURG",
        "LEIPZIG": "LEIPZIG",
        "STUTTGART": "STUTTGART",
        "FRANKFURT": "FRANKFURT",
        "DORTMUND": "DORTMUND",
        "WOLFSBURG": "WOLFSBURG",
        "HAMBURG": "HAMBURG", "HAMBURGER SV": "HAMBURG",
        "PAULI": "PAULI", "ST PAULI": "PAULI",
        "BREMEN": "BREMEN",
        "MAINZ": "MAINZ",
        "KÖLN": "KOLN", "KOLN": "KOLN", "COLOGNE": "KOLN",
    }
    for key, val in mappings.items():
        if key in n:
            return val
    return n.split()[-1] if n else n

def find_odd(outcomes, team_name):
    if not team_name or not outcomes:
        return None
    candidates = [team_name.upper(), normalize_name(team_name), team_name.upper().split()[-1]]
    for cand in candidates:
        if cand in outcomes:
            return outcomes[cand]
    team_upper = team_name.upper()
    team_norm = normalize_name(team_name)
    for k, v in outcomes.items():
        if team_upper in k or k in team_upper:
            return v
        knorm = normalize_name(k)
        if team_norm in knorm or knorm in team_norm:
            return v
    return None

def get_win_prob(c, path):
    # 1. The Odds API (primary for Bundesliga)
    try:
        odds = fetch_odds(path)
        home_name = away_name = None
        for cmp in c.get('competitors', []):
            name = cmp['team'].get('displayName', cmp['team'].get('name', '')).upper()
            if cmp.get('homeAway') == 'home': home_name = name
            else: away_name = name
        if home_name and away_name:
            key = f"{normalize_name(home_name)} vs {normalize_name(away_name)}"
            if key in odds:
                outcomes = odds[key]
                hp = find_odd(outcomes, home_name)
                ap = find_odd(outcomes, away_name)
                if isinstance(hp, (int, float)) and isinstance(ap, (int, float)):
                    return (f"[{THEME['home']}]{round(100/hp)}%[/]",
                            f"[{THEME['away']}]{round(100/ap)}%[/]")
    except Exception:
        pass

    # 2. TheRundown
    if path in RUNDOWN_SOCCER_IDS:
        try:
            odds = fetch_rundown_odds(path)
            home_name = away_name = None
            for cmp in c.get('competitors', []):
                name = cmp['team'].get('displayName', cmp['team'].get('name', '')).upper()
                if cmp.get('homeAway') == 'home': home_name = name
                else: away_name = name
            if home_name and away_name:
                key = f"{normalize_name(home_name)} vs {normalize_name(away_name)}"
                if key in odds:
                    outcomes = odds[key]
                    hp = find_odd(outcomes, home_name)
                    ap = find_odd(outcomes, away_name)
                    if isinstance(hp, (int, float)) and isinstance(ap, (int, float)):
                        return (f"[{THEME['home']}]{round(100/hp)}%[/]",
                                f"[{THEME['away']}]{round(100/ap)}%[/]")
        except Exception:
            pass

    # 3. football-data.org
    if path == "soccer/ger.1":
        try:
            fd = fetch_football_data_odds()
            home_name = away_name = None
            for cmp in c.get('competitors', []):
                name = cmp['team'].get('displayName', cmp['team'].get('name', '')).upper()
                if cmp.get('homeAway') == 'home': home_name = name
                else: away_name = name
            if home_name and away_name:
                key = f"{home_name} vs {away_name}"
                if key in fd:
                    pass
        except Exception:
            pass

    # 4. ESPN winProbability
    try:
        for comp in c.get('competitors', []):
            wp = comp.get('winProbability')
            if isinstance(wp, (int, float)) and wp > 0:
                pct = int(wp * 100)
                if comp.get('homeAway') == 'home':
                    return f"[{THEME['home']}]{pct}%[/]", f"[{THEME['dim']}]--[/]"
                return f"[{THEME['dim']}]--[/]", f"[{THEME['away']}]{pct}%[/]"
    except Exception:
        pass

    # 5. Direct ESPN probabilities endpoint (cached)
    try:
        event_id = c.get('id') or c.get('uid', '').split(':')[-1]
        if event_id:
            prob_key = (path, event_id)
            now = time.time()
            if prob_key in _prob_cache and now - _prob_cache_time.get(prob_key, 0) < CACHE_TTL:
                cached = _prob_cache[prob_key]
                if cached:
                    hp, ap = cached
                    return (f"[{THEME['home']}]{hp}%[/]",
                            f"[{THEME['away']}]{ap}%[/]")
                return f"[{THEME['dim']}]--[/]", f"[{THEME['dim']}]--[/]"
            prob_url = f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{path.split('/')[-1]}/events/{event_id}/competitions/{event_id}/probabilities"
            res = _get(prob_url, timeout=2)
            if res.status_code == 200:
                data = res.json()
                home_prob = data.get('homeTeam', {}).get('probability', 0)
                away_prob = data.get('awayTeam', {}).get('probability', 0)
                if home_prob > 0 and away_prob > 0:
                    result = (int(home_prob*100), int(away_prob*100))
                    _prob_cache[prob_key] = result
                    _prob_cache_time[prob_key] = now
                    return (f"[{THEME['home']}]{result[0]}%[/]",
                            f"[{THEME['away']}]{result[1]}%[/]")
            _prob_cache[prob_key] = None
            _prob_cache_time[prob_key] = now
    except Exception:
        pass

    return f"[{THEME['dim']}]--[/]", f"[{THEME['dim']}]--[/]"

def _fetch_probabilities_parallel(events, path):
    """Pre-fetch ESPN probabilities for all events in parallel, populating _prob_cache."""
    ids = []
    for e in events:
        c = e['competitions'][0]
        event_id = c.get('id') or c.get('uid', '').split(':')[-1]
        if event_id:
            prob_key = (path, event_id)
            now = time.time()
            if prob_key not in _prob_cache or now - _prob_cache_time.get(prob_key, 0) >= CACHE_TTL:
                ids.append((prob_key, event_id))
    if not ids:
        return
    def _fetch_one(prob_key, event_id):
        prob_url = f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{path.split('/')[-1]}/events/{event_id}/competitions/{event_id}/probabilities"
        try:
            res = _get(prob_url, timeout=2)
            if res.status_code == 200:
                data = res.json()
                hp = data.get('homeTeam', {}).get('probability', 0)
                ap = data.get('awayTeam', {}).get('probability', 0)
                if hp > 0 and ap > 0:
                    return prob_key, (int(hp*100), int(ap*100))
        except Exception:
            pass
        return prob_key, None
    with ThreadPoolExecutor(max_workers=min(len(ids), 16)) as ex:
        futs = [ex.submit(_fetch_one, k, eid) for k, eid in ids]
        now = time.time()
        for fut in as_completed(futs):
            prob_key, result = fut.result()
            _prob_cache[prob_key] = result
            _prob_cache_time[prob_key] = now

def fmt_sc(h, a, st):
    if st != 'post':
        return f"[{THEME['text']}]{h}[/]", f"[{THEME['text']}]{a}[/]"
    hi = int(h) if h.isdigit() else -1
    ai = int(a) if a.isdigit() else -1
    if hi > ai: return f"[bold #FFFFFF]{h}[/]", f"[{THEME['muted']}]{a}[/]"
    if ai > hi: return f"[{THEME['muted']}]{h}[/]", f"[bold #FFFFFF]{a}[/]"
    return f"[{THEME['text']}]{h}[/]", f"[{THEME['text']}]{a}[/]"

def parse_events(events, is_soc, is_f1, path):
    games = {}
    if not events:
        return games

    for e in events:
        utc = datetime.strptime(e['date'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=pytz.utc).astimezone(TZ)
        ldate = utc.strftime('%Y-%m-%d')
        c, st = e['competitions'][0], e['status']['type']['state']

        ctx_parts = []
        if c.get('notes'): ctx_parts.append(c['notes'][0]['headline'].upper())
        if c.get('series') and 'summary' in c['series']: ctx_parts.append(c['series']['summary'].upper())
        ctx = " - ".join(dict.fromkeys(ctx_parts))

        if is_f1:
            home_display = f"[{THEME['text']}]{e.get('name', 'Unknown').upper()}[/]"
            away_display = ""
            scr = f"[{THEME['dim']}]-[/]"
            home_wp = away_wp = f"[{THEME['dim']}]--[/]"
        else:
            ht = at = hs = as_ = "TBD"
            for cmp in c['competitors']:
                name = cmp['team'].get('displayName', cmp['team'].get('name', 'TBD'))
                abbr = cmp['team'].get('abbreviation', '')
                prefixes = ('1.', '2.', 'TSG', 'RB', 'SC', 'VFB', 'FC ', 'Borussia', 'Bayer', 'Eintracht')
                if name and not any(name.startswith(p) for p in prefixes):
                    name = name.title()
                flag = ABBR_FLAG.get(abbr, '')
                if flag:
                    name = f"{flag} {name}"
                if cmp['homeAway'] == 'home':
                    ht, hs = name, (cmp.get('score', '-') if st != 'pre' else '-')
                else:
                    at, as_ = name, (cmp.get('score', '-') if st != 'pre' else '-')

            hsf, asf = fmt_sc(hs, as_, st)
            home_wp, away_wp = get_win_prob(c, path)
            ctx_line = f"[dim {THEME['accent']}]{ctx}[/]\n" if ctx else ""
            home_display = f"{ctx_line}[bold #FFFFFF]{ht}[/]"
            away_display = f"[bold #FFFFFF]{at}[/]"
            scr = f"{hsf} [{THEME['dim']}]-[/] {asf}" if is_soc else f"{asf} [{THEME['dim']}]-[/] {hsf}"

        if st == 'in':
            p_prefix = "H" if is_soc else "Q"
            p_num = e['status'].get('period', 0)
            clk = e['status'].get('displayClock')
            det = e['status']['type'].get('shortDetail', '').upper()
            if 'HALF' in det:
                detail = "HALF"
            elif clk and clk != '0.0':
                detail = f"{p_prefix}{p_num} {clk}"
            else:
                detail = det
            stat = f"[bold {THEME['live']}]LIVE[/] [{THEME['muted']}]{detail}[/]"
        elif st == 'post':
            stat = f"[{THEME['muted']}]FINAL[/]"
        else:
            stat = ""

        games.setdefault(ldate, []).append({
            'dt': utc,
            'dstr': utc.strftime('%d %b').upper(),
            'tstr': utc.strftime('%H:%M'),
            'home': home_display, 'away': away_display,
            'home_wp': home_wp, 'away_wp': away_wp,
            'scr': scr, 'stat': stat,
        })
    return {k: sorted(v, key=lambda x: x['dt']) for k, v in games.items()}

def header_panel(title, subtitle=""):
    t = Text()
    t.append("  ", style=THEME['accent'])
    t.append(title.upper(), style=f"bold {THEME['text']}")
    if subtitle:
        t.append("   ")
        t.append(subtitle, style=THEME['muted'])
    return Panel(t, border_style=THEME['border'], box=box.ROUNDED, padding=(0, 1))

def build_table(is_omni=False):
    cols = [("TIME", THEME['accent'], 7, "left")]
    if is_omni:
        cols.append(("SPORT", THEME['muted'], 18, "left"))
    cols += [
        ("HOME", THEME['text'], 40, "right"),
        ("H%", THEME['home'], 6, "right"),
        ("", THEME['muted'], 4, "center"),
        ("A%", THEME['away'], 6, "left"),
        ("AWAY", THEME['text'], 40, "left"),
        ("SCORE", "", 12, "center"),
        ("STATUS", "", 24, "left"),
    ]
    pad = 3 if is_omni else 2
    t = Table(box=box.SQUARE, border_style="#6A6A6A",
              header_style=f"bold {THEME['accent']}", show_lines=True,
              row_styles=["", f"on {THEME['alt_row']}"], padding=(0, pad), expand=False)
    for c, s, w, j in cols:
        t.add_column(c, style=s, width=w, justify=j, no_wrap=True)
    return t

def add_game_row(t, g, sport=None):
    vs = f"[{THEME['dim']}]vs[/]"
    row = [g['tstr']]
    if sport is not None:
        row.append(sport)
    row += [g['home'], g['home_wp'], vs, g['away_wp'], g['away'], g['scr'], g['stat']]
    t.add_row(*row)

def wrap(title, subtitle, table):
    return Align.center(Group(header_panel(title, subtitle), table, Rule(style=THEME['border'])))

def get_display_games(data, is_nba_nfl=False):
    now = datetime.now(TZ)
    today = now.strftime('%Y-%m-%d')

    if not is_nba_nfl:
        if today in data and data[today]:
            return data[today], today, None
        for d in sorted(data.keys()):
            if d >= today and data[d]:
                return data[d], d, None
        return [], today, None

    games = list(data.get(today, []))
    if (now + timedelta(days=1)).strftime('%Y-%m-%d') in data:
        games += [g for g in data[(now + timedelta(days=1)).strftime('%Y-%m-%d')] if g['dt'].hour < 11]
    games = sorted(games, key=lambda x: x['dt'])

    used_dates = {g['dt'].strftime('%Y-%m-%d') for g in games}
    next_games = None
    for d in sorted(data.keys()):
        if d not in used_dates and data[d]:
            next_games = sorted(data[d], key=lambda x: x['dt'])
            break

    return games, today, next_games

def f1_results():
    try:
        r = _get("https://api.jolpi.ca/ergast/f1/current/last/results.json")
        if r.status_code != 200:
            r = _get("https://ergast.com/api/f1/current/last/results.json")
        rc = r.json()['MRData']['RaceTable']['Races'][0]
    except Exception as e:
        console.print(Panel(f"[{THEME['error']}]F1 Error: {e}[/]", border_style=THEME['border']))
        return

    drivers = [(res['position'],
                f"{res['Driver']['givenName'][0]}. {res['Driver']['familyName']}".upper(),
                res.get('Time', {}).get('time', res['status'].upper()))
               for res in rc['Results']]
    pad = max(len(d[1]) for d in drivers) + 2
    body = "\n".join(f"  [{THEME['accent']}]{d[0]:>2}[/]  [{THEME['text']}]{d[1].ljust(pad)}[/]  [{THEME['muted']}]{d[2]}[/]" for d in drivers)
    panel = Panel(body, title=f"[bold {THEME['accent']}]{rc['raceName'].upper()} - FINAL CLASSIFICATION[/]",
                  title_align="left", border_style=THEME['border'], box=box.ROUNDED, padding=(1, 2))
    console.print(Align.center(panel))

def fetch_sport_parallel(sport_data, mode="live"):
    p, n, s, f = sport_data
    st_off = -1 if mode == "live" else -14
    end_off = 2 if mode == "live" else 0
    evs, err = fetch(p, st_off, end_off)
    if err: return None
    data = parse_events(evs, s, f, p)
    is_nba_nfl = p in ("basketball/nba", "football/nfl")
    if mode == "live":
        games, _, _ = get_display_games(data, is_nba_nfl)
    else:
        cmpl = [g for d in data.values() for g in d if "FINAL" in g['stat'] or "COMPLETED" in g['stat']]
        if not cmpl:
            return None
        now = datetime.now(TZ)
        yest_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        yest_games = [g for g in cmpl if g['dt'].strftime('%Y-%m-%d') == yest_str]
        games = sorted(yest_games, key=lambda x: x['dt']) if yest_games else []
    return (n.upper(), games) if games else None

def execute_omni(mode="live"):
    ag = []
    all_sports = list(SPORTS.values()) + list(LEAGUES.values())
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(fetch_sport_parallel, sp, mode) for sp in all_sports]
        for fut in as_completed(futures):
            try:
                result = fut.result()
                if result:
                    name, games = result
                    ag.extend({**g, 'sp': name} for g in games)
            except Exception:
                pass

    if not ag:
        msg = "No events scheduled across tracked sports today." if mode == "live" else "No completed results from yesterday."
        return Align.center(Panel(f"[{THEME['muted']}] {msg} [/]", border_style=THEME['border'], box=box.ROUNDED, padding=(1, 3)))

    if mode == "live":
        today_str = datetime.now(TZ).strftime('%Y-%m-%d')
        today_games = [g for g in ag if g['dt'].strftime('%Y-%m-%d') == today_str]
        if today_games:
            ag = today_games
        else:
            return Align.center(Panel(f"[{THEME['muted']}] No games today across tracked sports. [/]", border_style=THEME['border'], box=box.ROUNDED, padding=(1, 3)))
        sub = datetime.now(TZ).strftime('%A - %d %b %Y').upper()
    else:
        yest = (datetime.now(TZ) - timedelta(days=1)).strftime('%A - %d %b %Y').upper()
        sub = f"YESTERDAY'S RESULTS - {yest}"

    t = build_table(is_omni=True)
    for g in sorted(ag, key=lambda x: x['dt']):
        add_game_row(t, g, sport=f"[{THEME['muted']}]{g['sp']}[/]")
    return wrap("OMNI-FEED", sub, t)

def execute(path, name, soc=False, f1=False, mode="live"):
    if mode == "results" and f1:
        return f1_results()

    evs, err = fetch(path, -1 if mode == "live" else -14, 365 if mode == "live" else 0)
    if err:
        console.print(Align.center(Panel(f"[{THEME['error']}]{err}[/]", border_style=THEME['border'])))
        return

    data = parse_events(evs, soc, f1, path)

    if mode == "results":
        cmpl = sorted([g for d in data.values() for g in d if "FINAL" in g['stat'] or "COMPLETED" in g['stat']], key=lambda x: x['dt'])
        if not cmpl:
            console.print(Panel(f"[{THEME['muted']}]No data in last 14 days.[/]", border_style=THEME['border']))
            return
        t = build_table()
        for g in cmpl:
            t.add_row(g['dstr'], g['home'], g['home_wp'], f"[{THEME['dim']}]vs[/]", g['away_wp'], g['away'], g['scr'], g['stat'])
        console.print(wrap(name, "LAST 14 DAYS", t))
        return

    if mode == "live" and path in SHOW_ALL_SPORTS:
        now = datetime.now(TZ)
        today_str = now.strftime('%Y-%m-%d')
        future_data = {d: gs for d, gs in data.items() if d >= today_str}
        if not future_data:
            return Align.center(Panel(f"[{THEME['muted']}] No upcoming matches scheduled. [/]", border_style=THEME['border'], box=box.ROUNDED, padding=(1, 3)))
        sections = []
        for date_key, games in sorted(future_data.items()):
            g = games[0]
            subtitle = f"{g['dt'].strftime('%A').upper()} - {g['dt'].strftime('%d %b %Y').upper()}"
            t = build_table()
            for game in games:
                add_game_row(t, game)
            sections.append(wrap(name, subtitle, t))
        return Group(*sections)

    is_nba_nfl = path in ("basketball/nba", "football/nfl")
    games, display_date, next_games = get_display_games(data, is_nba_nfl)

    if games:
        actual_date = games[0]['dt'].strftime('%A - %d %b %Y').upper()
    else:
        actual_date = datetime.now(TZ).strftime('%A - %d %b %Y').upper()

    t = build_table()
    for g in games:
        add_game_row(t, g)
    result = wrap(name, actual_date, t)

    if next_games:
        t2 = build_table()
        first_next = next_games[0]['dt']
        eastern_dt = first_next.astimezone(ET)
        nba_day = eastern_dt.strftime('%A').lower()
        berlin_day = first_next.strftime('%A').lower()
        berlin_time = first_next.strftime('%I:%M %p').lower()
        if berlin_time.startswith('0'):
            berlin_time = berlin_time[1:]
        subtitle = f"{nba_day} {berlin_time} ({berlin_day})"
        for g in next_games:
            day_short = g['dt'].strftime('%a').upper()
            g['tstr'] = f"{g['tstr']} ({day_short})"
            add_game_row(t2, g)
        result = Group(result, wrap(f"{name} - NEXT GAMEDAY", subtitle, t2))

    return result

def live_loop(p=None, n=None, s=False, f=False, is_omni=False):
    render = (lambda: execute_omni()) if is_omni else (lambda: execute(p, n, s, f, "live"))
    try:
        with Live(render(), screen=True, transient=True, refresh_per_second=0.2) as live:
            while True:
                for attempt in range(MAX_RETRIES):
                    try:
                        live.update(render())
                        break
                    except Exception:
                        if attempt == MAX_RETRIES - 1:
                            live.update(Panel(f"[{THEME['error']}]Could not fetch data - retrying soon...[/]", border_style=THEME['error']))
                        else:
                            time.sleep(3)
                time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        console.print(f"\n[{THEME['muted']}]Closed.[/]")

def render_html(events, path, name, mode="live"):
    now = datetime.now(TZ)
    today_str = now.strftime('%Y-%m-%d')
    _fetch_probabilities_parallel(events, path)
    days = {}
    for e in events:
        utc = datetime.strptime(e['date'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=pytz.utc).astimezone(TZ)
        ldate = utc.strftime('%Y-%m-%d')
        if mode == "live" and ldate < today_str: continue
        if mode == "results" and e['status']['type']['state'] != 'post': continue
        c, st = e['competitions'][0], e['status']['type']['state']
        home_team = away_team = None
        home_abbr = away_abbr = ""
        home_score = away_score = "-"
        for cmp in c['competitors']:
            t = cmp['team']
            n = t.get('displayName', t.get('name', 'TBD'))
            a = t.get('abbreviation', '')
            s = cmp.get('score', '-') if st != 'pre' else '-'
            if cmp.get('homeAway') == 'home':
                home_team, home_abbr, home_score = n, a, s
            else:
                away_team, away_abbr, away_score = n, a, s
        flag_h = ABBR_FLAG.get(home_abbr, '')
        flag_a = ABBR_FLAG.get(away_abbr, '')
        home_disp = f"{flag_h} {home_team}" if flag_h else home_team
        away_disp = f"{flag_a} {away_team}" if flag_a else away_team
        if st == 'in':
            clk = e['status'].get('displayClock', '')
            det = e['status']['type'].get('shortDetail', '').upper()
            if clk and clk != '0.0': clock = f"H {clk}"
            else: clock = det
            status = f'<span class="live">\u25cf LIVE</span> <span class="dim">{clock}</span>'
            if st == 'post': status = '<span class="final">FINAL</span>'
        elif st == 'post':
            status = '<span class="final">FINAL</span>'
        else:
            status = '<span class="scheduled">Scheduled</span>' if ldate == today_str else ''
        scr = f"{home_score} - {away_score}" if st != 'pre' else "-"
        home_wp_raw, away_wp_raw = get_win_prob(c, path)
        wp_h = re.sub(r'\[/?[^\]]*\]', '', home_wp_raw)
        wp_a = re.sub(r'\[/?[^\]]*\]', '', away_wp_raw)
        days.setdefault(ldate, []).append({
            'time': utc.strftime('%H:%M'), 'home': home_disp, 'away': away_disp,
            'wp_h': wp_h, 'wp_a': wp_a, 'scr': scr, 'status': status, 'dt': utc,
        })
    if not days: return ""
    rows = ""
    for date_key in sorted(days.keys()):
        games = sorted(days[date_key], key=lambda x: x['dt'])
        if mode == "live" and date_key == today_str:
            header = f'{games[0]["dt"].strftime("%A").upper()} - {games[0]["dt"].strftime("%d %b %Y").upper()}'
        elif mode == "live":
            header = f'{games[0]["dt"].strftime("%A").upper()} - {games[0]["dt"].strftime("%d %b %Y").upper()}'
        else:
            header = games[0]["dt"].strftime('%d %b %Y').upper()
        rows += f'<tr class="day-header"><td colspan="8">{header}</td></tr>'
        for g in games:
            rows += (f'<tr><td>{g["time"]}</td><td class="home">{g["home"]}</td>'
                     f'<td class="wp home-wp">{g["wp_h"]}</td><td class="vs">vs</td>'
                     f'<td class="wp away-wp">{g["wp_a"]}</td><td class="away">{g["away"]}</td>'
                     f'<td class="score">{g["scr"]}</td><td>{g["status"]}</td></tr>')
    title_suffix = "Results" if mode == "results" else "Live"
    refresh_sec = 60 if mode == "results" else 30
    subtitle = "Last 14 days" if mode == "results" else "Berlin times \u2022 Auto-refreshes every 30s"
    return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta http-equiv="refresh" content="{refresh_sec}">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>{name} - {title_suffix}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#12121a;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:20px;max-width:1100px;margin:0 auto}}
h1{{color:#87afff;font-size:1.5em;margin-bottom:4px;letter-spacing:0.5px}}
.sub{{color:#949494;font-size:0.85em;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;margin-bottom:16px;font-size:0.9em}}
td,th{{padding:8px 10px;text-align:left;border-bottom:1px solid #2a2a2a}}
.day-header td{{color:#87afff;font-weight:bold;font-size:0.85em;letter-spacing:0.5px;padding:16px 10px 6px;border-bottom:1px solid #3a3a3a;background:#16162a}}
.home{{text-align:right;font-weight:600;color:#fff;width:30%}}
.away{{font-weight:600;color:#fff;width:30%}}
.wp{{font-size:0.85em;width:5%;text-align:center}}
.home-wp{{color:#00ffaa}}
.away-wp{{color:#ffaa00}}
.vs{{color:#5a5a5a;text-align:center;width:3%;font-size:0.8em}}
.score{{text-align:center;font-weight:600;letter-spacing:1px;width:10%}}
.live{{color:#5fff87;font-weight:bold}}
.final{{color:#949494}}
.scheduled{{color:#5a5a5a}}
.dim{{color:#5a5a5a;font-size:0.85em}}
.footer{{margin-top:20px;color:#5a5a5a;font-size:0.75em;text-align:center}}
.ver{{color:#3a3a3a;font-size:0.65em;text-align:center}}
@media(max-width:640px){{body{{padding:10px}}table{{font-size:.78em;display:block;overflow-x:auto;white-space:nowrap}}td,th{{padding:5px 4px}}h1{{font-size:1.1em}}.wp{{font-size:.75em}}.home,.away{{width:auto}}}}
</style>
</head>
<body><h1>{name.upper()}</h1>
<p class="sub">{subtitle}</p>
<p class="ver">v2</p>
<table>{rows}</table>
<p class="footer">sportslive</p>
<script>window.addEventListener('beforeunload',()=>navigator.sendBeacon('/shutdown'))</script>
</body></html>'''

def serve(path, name, soc, f1, serve_mode="live", cloud_mode=False):
    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
    import webbrowser, threading

    if cloud_mode:
        port = int(os.environ.get("PORT", 8080))
    else:
        port = 8081 if serve_mode == "results" else 8080

    st_off = -14 if serve_mode == "results" else -1
    end_off = 0 if serve_mode == "results" else 365
    evs, err = fetch(path, st_off, end_off)
    if evs:
        _fetch_probabilities_parallel(evs, path)

    class Handler(BaseHTTPRequestHandler):
        last_request_time = time.time()

        def do_GET(self):
            if self.path == '/':
                st_off = -14 if serve_mode == "results" else -1
                end_off = 0 if serve_mode == "results" else 365
                evs, err = fetch(path, st_off, end_off)
                if err:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(err.encode())
                    return
                html = render_html(evs, path, name, serve_mode)
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
                Handler.last_request_time = time.time()
            elif self.path == '/debug':
                import subprocess
                out = []
                out.append(f"ODDS_API_KEY set: {'YES' if os.environ.get('ODDS_API_KEY') else 'NO'}")
                out.append(f"RUNDOWN_API_KEY set: {'YES' if os.environ.get('RUNDOWN_API_KEY') else 'NO'}")
                out.append(f"FOOTBALL_DATA_API_KEY set: {'YES' if os.environ.get('FOOTBALL_DATA_API_KEY') else 'NO'}")
                out.append(f"SPORT={os.environ.get('SPORT', 'not set')}")
                for p in ('.env', '/etc/secrets/.env', '/etc/secrets/env'):
                    out.append(f"{p} exists: {os.path.exists(p)}")
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write('\n'.join(out).encode())
            elif self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'ok')
            elif self.path == '/shutdown':
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'ok')
                threading.Thread(target=Handler._server.shutdown, daemon=True).start()
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, *a): pass
    server = ThreadingHTTPServer(('', port), Handler)
    Handler._server = server

    if cloud_mode:
        print(f"Starting sportslive server on port {port}")
    else:
        url = f'http://localhost:{port}'
        webbrowser.open(url)

        def watchdog():
            timeout = 90 if serve_mode == "live" else 180
            while True:
                time.sleep(30)
                if time.time() - Handler.last_request_time > timeout:
                    server.shutdown()
                    break
        threading.Thread(target=watchdog, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

def menu_panel(title, items):
    lines = [Text()]
    for key, label in items:
        line = Text()
        line.append(f"  {key}  ", style=f"bold {THEME['accent']}")
        line.append(label, style=THEME['text'])
        lines.append(line)
    lines.append(Text())
    return Panel(Group(*lines), title=f"[bold {THEME['accent']}]{title}[/]", title_align="left", border_style=THEME['border'], box=box.ROUNDED, padding=(0, 2))

def run_app():
    # Cloud mode: auto-start serve if PORT env is set
    cloud_port = os.environ.get("PORT")
    if cloud_port:
        sport_key = os.environ.get("SPORT", "wc")
        if sport_key in SPORTS:
            path, name, soc, f1 = SPORTS[sport_key]
        elif sport_key in LEAGUES:
            path, name, soc, f1 = LEAGUES[sport_key]
        else:
            path, name, soc, f1 = SPORTS["wc"]
        serve(path, name, soc, f1, cloud_mode=True)
        return

    args, mode = sys.argv[1:], "live"
    if args and args[0].lower() in ("live", "results", "serve"):
        mode, args = args[0].lower(), args[1:]

    def process(cmd, larg=None):
        if cmd == "omni":
            if mode == "live": live_loop(is_omni=True)
            else: console.print(execute_omni("results"))
        elif cmd in SPORTS:
            p, n, s, f = SPORTS[cmd]
            if mode == "serve":
                serve_mode = larg if larg in ("live", "results") else "live"
                serve(p, n, s, f, serve_mode)
            elif mode == "live": live_loop(p, n, s, f)
            else: execute(p, n, s, f, mode)
        elif cmd == "soccer" and larg in LEAGUES:
            p, n, s, f = LEAGUES[larg]
            if mode == "serve": serve(p, n, s, f)
            elif mode == "live": live_loop(p, n, s, f)
            else: execute(p, n, s, f, mode)
        else:
            return False
        return True

    if args and process(args[0].lower(), args[1] if len(args) > 1 else None):
        return

    while True:
        console.print()
        console.print(Align.center(menu_panel(f"SPORTS - {mode.upper()}", [("1", "NBA"), ("2", "NFL"), ("3", "Soccer"), ("4", "Formula 1"), ("5", "FIFA World Cup"), ("6", "Omni-Feed")])))
        try:
            choice = console.input(f"\n  [{THEME['accent']}]>[/] Select (1-6): ").strip()
            if choice in ("1", "2", "4", "5"):
                process(["nba", "nfl", "", "f1", "wc"][int(choice) - 1])
            elif choice == "6":
                process("omni")
            elif choice == "3":
                console.print()
                console.print(Align.center(menu_panel("LEAGUES", [(k, v[1]) for k, v in LEAGUES.items()])))
                sub = console.input(f"\n  [{THEME['accent']}]>[/] Select league (1-5): ").strip()
                process("soccer", sub)
            else:
                console.print(f"[{THEME['muted']}]Invalid selection.[/]")
            if mode == "results":
                break
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    run_app()

    