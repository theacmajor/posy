"""Static configuration: category folders, keyword maps, collection routing.

Everything that defines *how* items are categorized lives here so it can be
tuned without touching parsing/organizing logic.
"""

# ---------------------------------------------------------------------------
# Folder layout for the organized library.
# Order matters: the leading numbers keep folders sorted in Finder/Explorer.
# ---------------------------------------------------------------------------
LIBRARY_DIRNAME = "Instagram Saved Library"
INBOX = "01 Inbox"
METADATA_DIRNAME = "_metadata"
LOGS_DIRNAME = "logs"

# Maps a logical category -> its destination folder name.
# "Uncategorized" is the fallback when confidence is too low.
# The extra categories (Motivation, AI Claude, …) exist so large saved folders
# that don't fit the original ten keep their items together instead of being
# scattered by caption guessing. Folder names are filesystem-safe (no slashes).
CATEGORY_FOLDERS = {
    "Fitness": "02 Fitness",
    "Product Design": "03 Product Design",
    "UI UX Ideas": "04 UI UX Ideas",
    "Product Thinking": "05 Product Thinking",
    "Food": "06 Food",
    "Travel": "07 Travel",
    "Business": "08 Business",
    "Editing References": "09 Editing References",
    "Funny": "10 Funny",
    "Motivation": "11 Motivation",
    "AI Claude": "12 AI Claude",
    "Content Creation": "13 Content Creation",
    "Wallpapers": "14 Wallpapers",
    "Books": "15 Books",
    "Career": "16 Career",
    "Uncategorized": "17 Uncategorized",
}

# Every folder that must exist inside the library (Inbox + categories).
ALL_FOLDERS = [INBOX] + list(CATEGORY_FOLDERS.values())

# ---------------------------------------------------------------------------
# Keyword maps. Each keyword is a lowercase substring searched in captions,
# hashtags, usernames, collection names, urls and filenames.
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "Fitness": [
        "gym", "workout", "fat loss", "fatloss", "protein", "diet", "calorie",
        "bodybuilding", "muscle", "cardio", "strength", "physique", "abs",
        "back pain", "backpain", "fitness", "weight loss", "shredded", "lean",
        "pushup", "pull up", "deadlift", "squat", "biceps", "shoulder",
    ],
    "Product Design": [
        "product design", "ux", "ui", "case study", "portfolio",
        "interaction design", "user research", "design system", "figma",
        "wireframe", "prototype", "design process", "ux designer",
    ],
    "UI UX Ideas": [
        "landing page", "website", "mobile app", "interface", "layout",
        "visual design", "micro interaction", "microinteraction", "onboarding",
        "dashboard", "ui design", "ui inspiration", "web design", "app design",
        "components", "design inspiration",
    ],
    "Product Thinking": [
        "retention", "activation", "conversion", "growth", "funnel",
        "monetization", "user behavior", "aarrr", "strategy", "product manager",
        "product thinking", "north star", "engagement", "churn", "metrics",
    ],
    "Food": [
        "recipe", "chicken", "rice", "protein meal", "restaurant", "cooking",
        "food", "meal", "homemade", "paneer", "breakfast", "dinner", "lunch",
        "healthy recipe", "snack", "curry", "biryani", "egg",
    ],
    "Travel": [
        "places", "trip", "hotel", "resort", "road trip", "roadtrip",
        "bike ride", "mountains", "beach", "itinerary", "travel", "bali",
        "manali", "kedarkantha", "lonavala", "munnar", "trek", "backpack",
        "vacation", "tourist", "weekend getaway", "hill station",
    ],
    "Business": [
        "startup", "money", "marketing", "sales", "founder", "pricing",
        "client", "agency", "freelancing", "freelance", "lead", "funnel",
        "business", "revenue", "entrepreneur", "income", "cold email", "saas",
    ],
    "Editing References": [
        "photo edit", "cinematic", "color grade", "color grading", "lighting",
        "lightroom", "photoshop", "reel edit", "transition", "gym edit",
        "video editing", "editing", "vfx", "after effects", "premiere pro",
        "b-roll", "broll", "video style",
    ],
    "Funny": [
        "meme", "comedy", "funny", "relatable", "joke", "jokes", "lol",
        "humour", "humor", "shitpost", "sarcasm", "trolling",
    ],
}

# ---------------------------------------------------------------------------
# Direct routing for the user's real saved folders (collections). A user-curated
# folder is the single strongest signal we have, so a folder match is
# AUTHORITATIVE — it wins over caption keyword scoring entirely.
#
# Every one of the 49 saved folders in this export is mapped here. "Today" is
# Instagram's default auto-save bucket (a junk drawer that holds everything), so
# it is intentionally NOT mapped — items that live only in "Today" or in no
# folder fall through to keyword scoring.
#
# Folders that genuinely don't fit any category map to "Uncategorized" on
# purpose, so caption guessing doesn't invent a wrong category for them.
# Keys are lowercase + stripped.
# ---------------------------------------------------------------------------
COLLECTION_CATEGORY = {
    # Fitness
    "workout": "Fitness",
    "abs": "Fitness",
    "backpain": "Fitness",
    # Food
    "chicken": "Food",
    "heathy home made recipie": "Food",
    "food recipes and services": "Food",
    "alco": "Food",
    "daaru": "Food",
    # Travel
    "travel": "Travel",
    "bali": "Travel",
    "delhi gurgaon": "Travel",
    "pune": "Travel",
    "lonavala": "Travel",
    "kedarkantha": "Travel",
    "mumbai": "Travel",
    # Design / UI
    "figma": "Product Design",
    "ui": "UI UX Ideas",
    # Business
    "design business": "Business",
    "leads": "Business",
    "finances": "Business",
    "sales": "Business",
    "funnels": "Business",
    "informational": "Business",
    "issurance": "Business",
    "legal": "Business",
    # Career
    "job": "Career",
    "linkedin": "Career",
    # Content creation
    "content creation": "Content Creation",
    "hook lines and scripting": "Content Creation",
    "post material": "Content Creation",
    # Editing references
    "personal edit": "Editing References",
    "video style": "Editing References",
    "trendy songs": "Editing References",
    # Motivation
    "motivated": "Motivation",
    # AI
    "claude": "AI Claude",
    # Funny
    "jokes": "Funny",
    # Standalone faithful categories
    "wallpapers": "Wallpapers",
    "books": "Books",
    # Genuine misfits — kept out of keyword guessing on purpose.
    "move on": "Uncategorized",
    "sarojini": "Uncategorized",
    "dil": "Uncategorized",
    "skin": "Uncategorized",
    "date": "Uncategorized",
    "office outfits": "Uncategorized",
    "dream": "Uncategorized",
    "69 days": "Uncategorized",
    "buying guide": "Business",
}

# Minimum keyword score required to assign a category. Below this -> Uncategorized.
MIN_CONFIDENCE = 1

# Field weights used during keyword scoring (higher = stronger signal).
WEIGHTS = {
    "collection_name": 4,
    "hashtags": 3,
    "caption": 2,
    "username": 1,
    "url": 1,
    "local_file_path": 1,
}

# Media file extensions we recognize in the Inbox.
MEDIA_EXTENSIONS = {".mp4", ".mov", ".jpg", ".jpeg", ".png", ".webp"}
