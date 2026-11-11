# Canonical counting — character/word gate V2.0

Script is UTF-8 and normalized to Unicode NFC. Lines use LF. Numbered `PART n — name` headings are mandatory. `visible_characters` counts every Unicode code point in **visible script** including spaces/punctuation/Part headings and excluding CR/LF line separators; it is not ASCII count and not the same as the special ADAS Pure Character Count. Spoken `words` count ASCII letters/digits with optional single internal apostrophe/hyphen (regular expression `[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*`) **inside Part bodies only**, excluding heading words. Code applies the same algorithm every time.

Release: 44,000–48,000 visible characters AND 7,400–7,650 spoken words, with strict words <8,000 and chars 40,000–55,000 absolute envelope. Exact 8,000 words FAIL. Legacy “visible characters” documents do not define all Unicode edge cases; this V2 count is an explicit reproducible operational definition.

This counter is a mechanical release gate. It cannot validate TTS playback duration, audience retention or whether the prose is useful. Avoid filler to hit length.
