"""User-facing strings for the legal engine. Urdu and Roman Urdu text are DRAFTS:
have a native speaker and the legal advisor review them before release."""

LANGS = ("en", "ur", "ur-Latn")

DISCLAIMER = {
    "en": "Legal information, not legal advice.",
    "ur-Latn": "Yeh qanooni maloomat hain, qanooni mashwara nahin.",
    "ur": "یہ قانونی معلومات ہیں، قانونی مشورہ نہیں۔",
}

NOT_OFFICIAL = {
    "en": "",
    "ur-Latn": " Yeh wazahat statute ka sarkari tarjuma nahin hai.",
    "ur": " یہ وضاحت قانون کا سرکاری ترجمہ نہیں ہے۔",
}

REFUSALS = {
    "no_match": {
        "en": "I could not find a matching section in the PPC or CrPC for this question. Please rephrase it, or speak to a lawyer.",
        "ur-Latn": "Mujhe is sawal ke liye PPC ya CrPC mein koi mutabiq dafa nahin mili. Barah-e-karam sawal dobara likhein, ya kisi wakeel se baat karein.",
        "ur": "مجھے اس سوال کے لیے PPC یا CrPC میں کوئی متعلقہ دفعہ نہیں ملی۔ براہِ کرم سوال دوبارہ لکھیں، یا کسی وکیل سے بات کریں۔",
    },
    "out_of_scope": {
        "en": "This topic is outside LegalShield's current coverage (PPC and CrPC only). Please speak to a lawyer.",
        "ur-Latn": "Yeh mauzoo LegalShield ke maujooda daayre (sirf PPC aur CrPC) se bahar hai. Barah-e-karam kisi wakeel se baat karein.",
        "ur": "یہ موضوع LegalShield کے موجودہ دائرے (صرف PPC اور CrPC) سے باہر ہے۔ براہِ کرم کسی وکیل سے بات کریں۔",
    },
    "unsafe": {
        "en": "I can't help with avoiding lawful processes. I can explain your rights if you are stopped or arrested.",
        "ur-Latn": "Main qanooni karwai se bachne mein madad nahin kar sakta. Agar aap ko roka ya giraftar kiya jaye to main aap ke huqooq bata sakta hoon.",
        "ur": "میں قانونی کارروائی سے بچنے میں مدد نہیں کر سکتا۔ اگر آپ کو روکا یا گرفتار کیا جائے تو میں آپ کے حقوق بتا سکتا ہوں۔",
    },
}

BAILABLE = {
    True: {"en": "bailable", "ur-Latn": "qabil-e-zamanat", "ur": "قابلِ ضمانت"},
    False: {"en": "non-bailable", "ur-Latn": "na-qabil-e-zamanat", "ur": "ناقابلِ ضمانت"},
}
COGNIZABLE = {
    True: {"en": "cognizable", "ur-Latn": "qabil-e-dast-andazi police", "ur": "قابلِ دست اندازی پولیس"},
    False: {"en": "non-cognizable", "ur-Latn": "na-qabil-e-dast-andazi police", "ur": "ناقابلِ دست اندازی پولیس"},
}
COMPOUNDABLE = {
    "yes": {"en": "compoundable", "ur-Latn": "qabil-e-razi-nama", "ur": "قابلِ راضی نامہ"},
    "with_court_permission": {
        "en": "compoundable with court permission",
        "ur-Latn": "adalat ki ijazat se qabil-e-razi-nama",
        "ur": "عدالت کی اجازت سے قابلِ راضی نامہ",
    },
    "no": {"en": "not compoundable", "ur-Latn": "qabil-e-razi-nama nahin", "ur": "قابلِ راضی نامہ نہیں"},
}


def disclaimer(lang: str) -> str:
    return DISCLAIMER.get(lang, DISCLAIMER["en"])
