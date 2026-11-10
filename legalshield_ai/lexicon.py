"""Roman Urdu / Urdu -> English search-term expansion (offline fallback for query rewriting)."""
import re

LEXICON = {
    # Roman Urdu
    "dafa": "section", "dafah": "section", "dafaat": "section",
    "zamanat": "bail bailable", "zamanti": "bail bailable", "zamant": "bail",
    "giraftar": "arrest arrested", "girftar": "arrest arrested", "giraftari": "arrest",
    "pakra": "arrest arrested", "pakar": "arrest", "pakre": "arrest", "pakrna": "arrest", "pakda": "arrest",
    "thana": "police station", "thane": "police station", "police": "police",
    "hawalat": "custody detain", "hirasat": "custody detain", "band": "detain",
    "rakh": "detain detained", "rakha": "detain detained", "rakhna": "detain detained",
    "ghante": "hours twenty four", "ghanta": "hour", "ghantay": "hours twenty four",
    "chori": "theft", "chor": "theft", "dhamki": "criminal intimidation threat", "dhamkiyan": "criminal intimidation threat",
    "dhoka": "cheating", "dhokha": "cheating", "fraud": "cheating",
    "qatal": "murder qatl", "qatl": "murder qatl", "katal": "murder qatl", "qatil": "murder qatl",
    "wakeel": "lawyer", "wakil": "lawyer", "adalat": "court magistrate", "magistrate": "magistrate",
    "warrant": "warrant", "bagair": "without", "baghair": "without",
    "pareshan": "harassment", "hirasani": "harassment", "hirasan": "harassment",
    "shikayat": "complaint", "fir": "FIR information cognizable", "ittila": "information",
    "zakhmi": "hurt", "zakhm": "hurt", "mara": "hurt", "marpeet": "hurt",
    "huqooq": "rights", "haq": "right", "razi": "compound", "nama": "compound", "razinama": "compound",
    # Urdu script
    "دفعہ": "section", "ضمانت": "bail bailable", "گرفتار": "arrest arrested", "گرفتاری": "arrest",
    "پکڑا": "arrest arrested", "پولیس": "police", "تھانہ": "police station", "تھانے": "police station",
    "حراست": "custody detain", "گھنٹے": "hours twenty four", "چوری": "theft", "دھمکی": "criminal intimidation threat",
    "دھوکہ": "cheating", "دھوکا": "cheating", "قتل": "murder qatl", "وکیل": "lawyer", "عدالت": "court magistrate",
    "مجسٹریٹ": "magistrate", "وارنٹ": "warrant", "ہراسانی": "harassment", "شکایت": "complaint",
    "زخمی": "hurt", "حقوق": "rights", "راضی": "compound", "نامہ": "compound",
}

# Words that indicate Roman Urdu when written in Latin script (none of these are common English words).
ROMAN_URDU_MARKERS = {
    "mujhe", "mujhey", "mera", "meri", "mere", "hai", "hain", "kya", "kaise", "kese", "nahi", "nahin", "aur",
    "pakra", "pakar", "giraftar", "girftar", "giraftari", "dafa", "dafah", "zamanat", "zamanti", "thana", "thane",
    "kia", "kiya", "mein", "kyun", "kyon", "agar", "tha", "thi", "gaya", "gayi", "liya", "karna", "chahiye",
    "chori", "dhamki", "wakeel", "wakil", "adalat", "sirf", "bhi", "koi", "kab", "kahan", "kaun", "humein",
    "hamein", "apni", "apna", "ghalat", "jhoota", "ghante", "ghantay", "zyada", "sakte", "sakta", "sakti", "huqooq",
    "hirasani", "pareshan", "shikayat", "dhoka", "dhokha", "qatal", "katal",
}

_TOKEN = re.compile(r"[A-Za-z0-9]+|[\u0600-\u06FF]+")


def tokenize_raw(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def normalise_query(text: str) -> str:
    """Return an English-ish bag of words usable for BM25 retrieval."""
    out: list[str] = []
    for tok in tokenize_raw(text):
        out.append(LEXICON.get(tok, tok))
    return " ".join(out)
