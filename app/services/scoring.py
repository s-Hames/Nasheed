import re
from app.core.config import settings

# Strong indicators — these strongly suggest the content IS a nasheed (+20 each)
STRONG_NASHEED_INDICATORS = [
    "nasheed", "anasheed", "نشيد", "نشید",
    "naat", "hamd", "qasida", "qaseedah", "munajat",
    "ilahi", "ilahee",
]

# Moderate boost words — suggest islamic/vocal content (+10 each)
BOOST_WORDS = [
    "no music", "vocals only", "vocal only", "without music",
    "islamic", "islam", "muslim", "prophet", "muhammad", "allah",
    "quran", "sunnah", "halal", "deen", "ummah", "dawah",
    "ramadan", "eid", "hijab", "jannah", "taqwa", "dhikr", "zikr",
    "arabic vocal", "islamic song", "islamic vocal",
    "omar esa", "siedd", "muhammad al muqit", "mishary rashid",
    "maher zain", "sami yusuf", "ahmed bukhatir",
    "one path network", "mercifulservant",
]

# Blacklist words — strong negative signals, heavy penalty (-100 each)
BLACKLIST_WORDS = [
    # Music/remix culture
    "remix", "slowed", "reverb", "lofi", "lo-fi", "bass boosted",
    "8d audio", "nightcore", "phonk", "trap", "beat drop",
    "music video", "official video", "lyrics video",
    # Explicit / inappropriate
    "explicit", "uncensored", "18+", "nsfw", "sexy", "twerk",
    "horny", "porn", "xxx", "nude", "naked",
    # Entertainment / non-nasheed
    "dj", "club", "rave", "edm", "hip hop", "rap", "rock",
    "pop music", "k-pop", "kpop", "reggaeton",
    "movie", "film", "trailer", "gameplay", "gaming", "reaction",
    "prank", "meme", "funny", "comedy", "roast", "asmr",
    "mukbang", "unboxing", "haul", "vlog",
    "edit", "status", "whatsapp status", "ringtone",
    "shorts", "tiktok",
]

# Short words that need word-boundary matching to avoid false positives
# (e.g. 'dj' in 'adjacent', 'rap' in 'wrapped', 'pop' in 'popular')
_BOUNDARY_MATCH_WORDS = {
    "dj", "edit", "lofi", "rap", "edm", "pop", "rock", "horny",
    "rave", "nude", "meme", "haul", "vlog", "xxx",
}


def calculate_score(title: str, channel: str, trusted_channels: list[str]) -> int:
    """
    Calculate a suitability score for a YouTube video based on its title and channel name.
    
    Scoring breakdown:
      - Strong nasheed indicators: +20 each
      - Moderate boost words:      +10 each
      - Trusted channel match:     +25
      - Blacklist words:          -100 each
    
    Returns:
        int: The calculated suitability score.
    """
    title_lower = title.lower()
    channel_lower = channel.lower()
    combined = f"{title_lower} {channel_lower}"

    score = 0

    # Strong nasheed indicators (+20 each)
    for word in STRONG_NASHEED_INDICATORS:
        if word in combined:
            score += 20

    # Moderate boost words (+10 each)
    for word in BOOST_WORDS:
        if word in combined:
            score += 10

    # Blacklist words (-100 each)
    for word in BLACKLIST_WORDS:
        if word in _BOUNDARY_MATCH_WORDS:
            # Use word-boundary matching for short terms
            pattern = rf"\b{re.escape(word)}\b"
            if re.search(pattern, combined):
                score -= 100
        else:
            if word in combined:
                score -= 100

    # Trusted channel bonus (+25)
    if channel_lower in [tc.lower() for tc in trusted_channels]:
        score += 25

    return score


def is_valid_nasheed(score: int) -> bool:
    """
    Determine if a calculated score meets the configured threshold.
    Default threshold is 10 (requires at least one positive signal).
    """
    return score >= settings.SCORE_THRESHOLD
