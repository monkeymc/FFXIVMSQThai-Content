"""key_ja: the lookup key of a Japanese dialogue line.

The plugin has to reproduce this byte for byte in C#. Apply the rules in this order:

1. Delete SE control payloads and stray control characters: every match of
       [\\x02][\\s\\S]{1,4}[\\x03]|[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]
   This is the pattern ToPureAlphanumericKey uses. Run it on the raw text, before
   rule 2, because normalization can change the length of a payload.
2. Normalize to Unicode NFKC (C#: text.Normalize(NormalizationForm.FormKC)).
   Full-width Latin letters and digits become ASCII, half-width kana become full-width.
3. Delete every occurrence of the player-name placeholders, case-sensitive, in this
   order: "Forename", "Surname", "Player". "Player" is the datamining form,
   "Forename" and "Surname" the project form; both forms of a line give the same key.
4. Keep only the code points whose Unicode general category starts with L, M or N
   (letters, marks, numbers), in their original order. That drops whitespace (ASCII,
   full-width, newlines), punctuation (P*: 「」、。！？・…), symbols (S*: ～ ─ *) and
   every control, format and private-use character. It keeps kana, kanji, ー, 々,
   Latin letters and digits.

There is no case folding. Classify by code point, not by UTF-16 unit
(C#: text.EnumerateRunes() with Rune.GetUnicodeCategory).
Text read from the game client holds the real character name where these sources hold
a placeholder; the caller deletes that name before keying.
A line made only of punctuation ("……") has an empty key and cannot be looked up.
"""
import re
import unicodedata

CONTROL = re.compile(r"[\x02][\s\S]{1,4}[\x03]|[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
PLACEHOLDERS = ("Forename", "Surname", "Player")

# Inputs the quest text does not contain, with the key each must give.
EDGE_CASES = {
    "\x02\x10\x01\x03こんにちは\x1f世界": "こんにちは世界",
    "ＡＢＣ１２３ ｶﾞｲｱ": "ABC123ガイア",
    "Forename Surname……「暁」のリンクパール？": "暁のリンクパール",
    "本ッ当～にありがとう　ございまっす！！": "本ッ当にありがとうございまっす",
    "……！？": "",
}


def key_ja(text):
    text = unicodedata.normalize("NFKC", CONTROL.sub("", text))
    for placeholder in PLACEHOLDERS:
        text = text.replace(placeholder, "")
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in "LMN")
