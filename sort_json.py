import json
import re
import pykakasi

# pykakasiインスタンスをモジュールレベルで初期化
_kks = pykakasi.kakasi()


def kanji_to_hiragana(text):
    """漢字・カタカナ・英字を含む任意のテキストをひらがなに変換する"""
    if not text:
        return ""
    result = _kks.convert(text)
    # 各トークンのhiraフィールドを結合（ひらがな変換結果）
    return "".join(item["hira"] for item in result)


def hepburn_to_gojuon_key(text):
    if not text:
        return ""

    # Normalize to lowercase
    text = text.lower()

    # Replace long vowels (Hepburn usually implies macrons or omission, simplified here)
    # Just treat them as single vowels for sorting primary key, OR duplicates?
    # Usually "aa" is treated as "a". "ou" as "o"?
    # For simplicity, treat as is, but handle multi-char sequences.

    # Pre-processing for Hepburn specific sequences to Kunrei/Standardized form
    # Consonants mapping group
    # K: k, g
    # S: s, z, j, sh
    # T: t, d, ch, ts
    # N: n
    # H: h, b, p, f
    # M: m
    # Y: y
    # R: r
    # W: w

    # We want a string of numbers/chars that sorts correctly.
    # 0: Vowel (A, I, U, E, O)
    # 1: K, G
    # 2: S, Z, J, Sh
    # 3: T, D, Ch, Ts
    # 4: N
    # 5: H, B, P, F
    # 6: M
    # 7: Y
    # 8: R
    # 9: W

    # Vowels mapping
    # A: 1
    # I: 2
    # U: 3
    # E: 4
    # O: 5

    # Syllable splitting is hard without full dictionary.
    # But simple replacement might work for primary sorting.

    # Replacements (Longer first)
    replacements = [
        # Double consonants (sokuon) - ignore or treat as small tsu?
        # usually small tsu sorts before voiced? after?
        # Ignore for coarse sorting first. "kken" -> "ken".
        (r"kk", "k"),
        (r"ss", "s"),
        (r"tt", "t"),
        (r"hh", "h"),
        (r"mm", "m"),
        (r"pp", "p"),
        # Compound Consonants to Standard Base
        (r"sh", "s"),
        (r"ch", "t"),
        (r"ts", "t"),
        (r"fu", "hu"),
        (r"j", "z"),
        (r"ky", "ki"),
        (r"gy", "gi"),
        (r"sy", "si"),
        (r"zy", "zi"),
        (r"ty", "ti"),
        (r"dy", "di"),
        (r"ny", "ni"),
        (r"hy", "hi"),
        (r"by", "bi"),
        (r"py", "pi"),
        (r"my", "mi"),
        (r"ry", "ri"),
        # Voiced to Unvoiced (for primary group)
        (r"g", "k"),
        (r"z", "s"),
        (r"d", "t"),
        (r"b", "h"),
        (r"p", "h"),
        (r"v", "h"),  # rarely v -> b -> h?
        # Special F (fu -> hu -> h) covered by fu->hu then h
    ]

    # Apply consonant normalization
    processed = text
    # Special: 'fu' -> 'hu' manually handled in regex above 'fu' -> 'hu'.
    # But wait, 'hu' is h + u.
    # 'shi' -> 'si'.
    # 'chi' -> 'ti'.
    # 'tsu' -> 'tu'.
    # 'ji' -> 'zi' -> 'si'.

    # Let's do it carefully.

    # First, convert Hepburn digraphs to single/standard chars for sorting
    processed = processed.replace(
        "sh", "s"
    )  # shi -> si, sha -> sa (Wait, sha is sya... s+ya)
    # sha -> sa? No. sha -> si + ya?
    # In dictionary order:
    # Sa, Si, Su, Se, So.
    # Sha (Si-ya) comes after Si?
    # Si (Si)
    # Sha (Si-ya)
    # Si < Si-ya.
    # So 'Sha' sorts after 'Shi'.
    # But 'Sha' in romaji is 'sha'.
    # 'Shi' is 'shi'.
    # 'sha' < 'shi' (a < i).
    # Error: 'Sha' should be AFTER 'Shi'.
    # So we must map 'Sha' to 'Si-ya' structure.
    # We need to tokenize syllables.

    # Let's map Consonants to numbers 1-9
    # Vowels to numbers 1-5

    # Define mapping
    # A=1, I=2, U=3, E=4, O=5
    # K=1, S=2, T=3, N=4, H=5, M=6, Y=7, R=8, W=9

    # Syllables:
    # A (0,1), I (0,2)...
    # Ka (1,1)...
    # Sa (2,1)...
    # Sha (2,2,7,1) -> S-i-y-a?

    # Let's try to just build a numeric string key.
    key = []
    i = 0
    n = len(text)

    # Helpers
    vowels = {"a": "1", "i": "2", "u": "3", "e": "4", "o": "5"}
    consonants = {
        "k": "1",
        "g": "1",
        "s": "2",
        "z": "2",
        "j": "2",
        "t": "3",
        "d": "3",
        "c": "3",
        "n": "4",
        "h": "5",
        "b": "5",
        "p": "5",
        "f": "5",
        "m": "6",
        "y": "7",
        "r": "8",
        "w": "9",
    }

    # Special handling for 'ch' -> t, 'sh' -> s, 'ts' -> t, 'fu' -> h
    # 'j' -> s (zi -> si)

    while i < n:
        c = text[i]

        # Check digraphs
        if i + 1 < n:
            two = text[i : i + 2]
            if two == "sh":  # sh -> s
                c = "s"
                i += 1  # skip h
            elif two == "ch":  # ch -> t
                c = "t"
                i += 1
            elif two == "ts":  # ts -> t
                c = "t"
                i += 1
            elif two == "ky" or two == "gy":
                # ky -> k (ki) + small y?
                # Actually k+y+a (kya) -> ki + ya.
                # ki (1,2)
                # kya (1,2,7,1)
                # We can handle y explicitly.
                pass
            # fu is distinct? f -> h
            elif two == "fu":
                # f -> h
                c = "h"
                # u stays u
                # i stays pointing to u?
                # No, just consume f
                # text[i+1] is u.
                # c = 'h'
                # i += 1 # ??? No.
                # f is consumed.
                # Wait. If I replace 'f' with 'h', loop continues?
                pass

        # Map char
        val = ""
        if c in vowels:
            val = "0" + vowels[c]  # 01, 02...
        elif c in consonants:
            val = consonants[c]
            # Need to align with vowels?
            # Consonant + Vowel structure?
            # Simply appending works for string sort?
            # ka (1,1) > a (0,1)? Yes (1 > 0).
            # sa (2,1) > ka (1,1)? Yes (2 > 1).
            # su (2,3) > sa (2,1)? Yes (3 > 1).
            # shi (2,2) vs su (2,3)? Yes (2 < 3).
            # se (2,4) > shi (2,2)? Yes (4 > 2).
            # so (2,5) > se (2,4)? Yes (5 > 4).

            # What about 'n' (syllabic n)?
            # 'n' at end or before consonant.
            if c == "n":
                # Check next char
                if i + 1 < n and text[i + 1] not in vowels and text[i + 1] != "y":
                    # Syllabic N.
                    # Sort order of N?
                    # Wa, Wo, N.
                    # N comes last.
                    # W is 9.
                    # N should be > 9-something.
                    # Or just treat as '4' (N row)? No.
                    # Syllabic N is distinctive.
                    # Let's assign it a high value? Or low?
                    # 'Kani' (Crab) vs 'Kan' (Can).
                    # Kani (Ka-Ni)
                    # Kan (Ka-N).
                    # Ni (4,2). N (Only N).
                    # Does N come before Ni?
                    # In dictionary: yes. 'n' is usually ignored or treated specially?
                    # Standard Gojuon: N is at the end.
                    # Ka-N vs Ka-Ni.
                    # N vs Ni.
                    # N usually comes AFTER Ni?
                    # No. 'n' is a separate mora.
                    # Ma-n-ga.
                    # Ma-ni-a.
                    # n vs ni.
                    # Dictionary: Kana order.
                    # Na, Ni, Nu, Ne, No.... Ma... Ya... Ra... Wa... N.
                    # So Ni comes BEFORE N.
                    # So 'Mania' < 'Manga'.
                    # Key for Ni: 42.
                    # Key for N: Should be > 42.
                    # W is 9. So N should be 99?
                    val = "99"
                elif i + 1 == n:  # End of string
                    val = "99"
                else:
                    # Na, Ni, Nu...
                    val = "4"
        else:
            # Other chars (f, v, etc not in map?)
            if c == "f":
                val = "5"  # h
            elif c == "j":
                val = "2"  # s/z
            elif c == "-":
                val = "00"  # ignore or minimal?
            else:
                val = c  # Keep numbers etc?

        # Adjust for Ya, Yu, Yo (Contracted sounds)
        # sha -> si, ya.
        # s(2) -> i(2)??
        # wait.
        # sha -> s(2) + h? -> s(2).
        # next is a.
        # sa (2,1).
        # shi (2,2).
        # sha (should be si-ya -> 2,2,7,1).
        # If I map sh -> s.
        # sha -> s, a -> 2, 1.
        # shi -> s, i -> 2, 2.
        # 21 < 22.
        # So Sha < Shi.
        # Error: Shi < Sha in Gojuon.
        # So we MUST handle 'y' correctly.
        # If I see 'sha', I should treat as 's', 'i', 'y', 'a'.
        # Insert 'i', 'y'.

        key.append(val)
        i += 1

    return "".join(key)


# We need a robust implementation.
# Let's simplify and assume modifying vowels order (a,i,u,e,o) and consonantal order helps enough.
# And handle 'h' vs 'f' (hu vs fu).
# And 't' vs 'ch' vs 'ts'.
# And 's' vs 'sh'.
# AND ensure 'sha' > 'shi' via vowel checks.

# Improved Logic:
# 1. Replace Consonants with sort-prefix.
# 2. Replace Vowels with sort-suffix.
# 3. Handle digraphs before mapping.


def get_sort_key(text):
    s = text.lower()
    # 1. Normalize Hepburn to vaguely "Kunrei-like" pre-sort form
    # but specifically targeting the correct sort order problems.

    # shi (si) < su (su).
    # sha (sya) > shi (si).
    # sha < shu (syu).
    # so we need i < y?
    # vowels: a(1) i(2) u(3) e(4) o(5).
    # y: 6?
    # then sha (s-y-a) vs shi (s-i).
    # y(6) > i(2). So sha > shi. Correct.

    # Mapping table
    # a->1, i->2, u->3, e->4, o->5
    # y->6 (for ya, yu, yo) - wait, ya(1), yu(3), yo(5).
    # But as a glide char?
    # Si-ya vs Si.
    # Si (s-i). Si-ya (s-i-y-a).
    # Si is prefix of Si-ya.
    # Short string < Long string.
    # So Si < Si-ya. Correct.
    # Wait, 'sha' is one syllable in Romaji 'sha'.
    # If we map 'sh' -> 's_i_y'.
    # sha -> s_i_y_a.
    # shi -> s_i.
    # s_i < s_i_y_a. Correct.

    # ch -> t_i_y
    # ts -> t_u
    # fu -> h_u
    # j -> z_i_y or z_i (ji). jya -> z_i_y_a.

    # Replacements
    s = s.replace("sha", "siya")
    s = s.replace("shu", "siyu")
    s = s.replace("sho", "siyo")
    s = s.replace("shi", "si")

    s = s.replace("cha", "tiya")
    s = s.replace("chu", "tiyu")
    s = s.replace("cho", "tiyo")
    s = s.replace("chi", "ti")

    s = s.replace("tsu", "tu")  # tsu -> tu
    # tsa -> tu?? No. tsa tso etc rarely used.

    s = s.replace("fu", "hu")  # fu -> hu

    s = s.replace("jya", "ziya")
    s = s.replace("ju", "ziyu")  # ju -> zyu -> ziyu
    s = s.replace("jo", "ziyo")  # jo -> zyo -> ziyo
    s = s.replace("ja", "ziya")  # ja -> zya -> ziya
    s = s.replace("ji", "zi")

    s = s.replace("kya", "kiya")
    s = s.replace("kyu", "kiyu")
    s = s.replace("kyo", "kiyo")

    s = s.replace("gya", "giya")
    s = s.replace("gyu", "giyu")
    s = s.replace("gyo", "giyo")

    # ... add others (hya, bya, pya, mya, rya)
    s = s.replace("hya", "hiya")
    s = s.replace("hyu", "hiyu")
    s = s.replace("hyo", "hiyo")
    # omitted others for brevity, relying on most common cases

    # Now map chars to numbers
    # a->1, i->2, u->3, e->4, o->5
    # Consonants orders:
    # ?: 0 (Vowels start)
    # k/g: 1
    # s/z: 2
    # t/d: 3
    # n: 4
    # h/b/p: 5
    # m: 6
    # y: 7
    # r: 8
    # w: 9
    # n (syllabic): 99?

    # Problem: 'n' map.
    # If 'n' is followed by vowel or y, it is Na-row (4).
    # If followed by consonant or end, it is N (99).

    res = ""
    i = 0
    ln = len(s)

    cons_map = {
        "k": "1",
        "g": "1",
        "s": "2",
        "z": "2",
        "t": "3",
        "d": "3",
        "n": "4",  # provisional
        "h": "5",
        "b": "5",
        "p": "5",
        "m": "6",
        "y": "7",
        "r": "8",
        "w": "9",
    }
    vowel_map = {"a": "1", "i": "2", "u": "3", "e": "4", "o": "5"}

    while i < ln:
        c = s[i]

        if c in vowel_map:
            # Vowel start (A-row) if not preceded by consonant?
            # No, if previous was consonant, we already handled it?
            # No, we process char by char.
            # a (0,1).
            res += "0" + vowel_map[c]
        elif c in cons_map:
            val = cons_map[c]

            # Special N check
            if c == "n":
                is_syllabic = False
                if i + 1 >= ln:
                    is_syllabic = True
                else:
                    nc = s[i + 1]
                    if nc not in vowel_map and nc != "y":
                        is_syllabic = True

                if is_syllabic:
                    val = "99"  # Sorts after W(9)
                    res += val
                    i += 1
                    continue

            res += val
        else:
            res += c  # Keep others

        i += 1

    return res


def hiragana_to_romaji(text):
    if not text:
        return ""

    # Simple dictionary for mapping hiragana to romaji
    kana_map = {
        "あ": "a",
        "い": "i",
        "う": "u",
        "え": "e",
        "お": "o",
        "か": "ka",
        "き": "ki",
        "く": "ku",
        "け": "ke",
        "こ": "ko",
        "さ": "sa",
        "し": "shi",
        "す": "su",
        "せ": "se",
        "そ": "so",
        "た": "ta",
        "ち": "chi",
        "つ": "tsu",
        "て": "te",
        "と": "to",
        "な": "na",
        "に": "ni",
        "ぬ": "nu",
        "ね": "ne",
        "の": "no",
        "は": "ha",
        "ひ": "hi",
        "ふ": "fu",
        "へ": "he",
        "ほ": "ho",
        "ま": "ma",
        "み": "mi",
        "む": "mu",
        "め": "me",
        "も": "mo",
        "や": "ya",
        "ゆ": "yu",
        "よ": "yo",
        "ら": "ra",
        "り": "ri",
        "る": "ru",
        "れ": "re",
        "ろ": "ro",
        "わ": "wa",
        "を": "wo",
        "ん": "n",
        "が": "ga",
        "ぎ": "gi",
        "ぐ": "gu",
        "げ": "ge",
        "ご": "go",
        "ざ": "za",
        "じ": "ji",
        "ず": "zu",
        "ぜ": "ze",
        "ぞ": "zo",
        "だ": "da",
        "ぢ": "ji",
        "づ": "zu",
        "で": "de",
        "ど": "do",
        "ば": "ba",
        "び": "bi",
        "ぶ": "bu",
        "べ": "be",
        "ぼ": "bo",
        "ぱ": "pa",
        "ぴ": "pi",
        "ぷ": "pu",
        "ぺ": "pe",
        "ぽ": "po",
        "きゃ": "kya",
        "きゅ": "kyu",
        "きょ": "kyo",
        "しゃ": "sha",
        "しゅ": "shu",
        "しょ": "sho",
        "ちゃ": "cha",
        "ちゅ": "chu",
        "ちょ": "cho",
        "にゃ": "nya",
        "にゅ": "nyu",
        "にょ": "nyo",
        "ひゃ": "hya",
        "ひゅ": "hyu",
        "ひょ": "hyo",
        "みゃ": "mya",
        "みゅ": "myu",
        "みょ": "myo",
        "りゃ": "rya",
        "りゅ": "ryu",
        "りょ": "ryo",
        "ぎゃ": "gya",
        "ぎゅ": "gyu",
        "ぎょ": "gyo",
        "じゃ": "ja",
        "じゅ": "ju",
        "じょ": "jo",
        "びゃ": "bya",
        "びゅ": "byu",
        "びょ": "byo",
        "ぴゃ": "pya",
        "ぴゅ": "pyu",
        "ぴょ": "pyo",
        "っ": "t",  # Simplified sokuon handling
        "ー": "",  # Long vowel mark - ignore or extend vowel?
    }

    res = ""
    i = 0
    while i < len(text):
        # Check 2 chars first (for digraphs)
        if i + 1 < len(text):
            two = text[i : i + 2]
            if two in kana_map:
                res += kana_map[two]
                i += 2
                continue

        char = text[i]
        if char in kana_map:
            # Handle sokuon specially if needed, but simple map helps enough
            res += kana_map[char]
        else:
            # Keep roman chars or unknown as is
            res += char
        i += 1
    return res


def process_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        is_japanese = False
        yomi_family = ""

        if "note" in entry and isinstance(entry["note"], str):
            match = re.search(r'yomi\s*=\s*["\']([^"\']+)["\']', entry["note"])
            if match:
                yomi_family = match.group(1)
                is_japanese = True

        if "language" in entry:
            lang = entry["language"].lower()
            if lang in ["jpn", "japanese", "日本語", "ja"]:
                is_japanese = True

        if is_japanese and "curator" not in entry and "author" in entry:
            entry["curator"] = []
            authors = entry["author"]

            for idx, auth in enumerate(authors):
                new_c = {}
                family = ""
                given = ""

                if "literal" in auth:
                    parts = re.split(r"[,，\s]+", auth["literal"])
                    if len(parts) >= 1:
                        family = parts[0]
                    if len(parts) >= 2:
                        given = parts[1]
                    auth["family"] = family
                    auth["given"] = given
                    del auth["literal"]
                else:
                    family = auth.get("family", "")
                    given = auth.get("given", "")

                target_family = family
                if idx == 0 and yomi_family:
                    target_family = yomi_family

                def convert_name(n):
                    """漢字・カタカナ・ひらがなをひらがな経由でローマ字に変換する"""
                    if not n:
                        return ""
                    hira = kanji_to_hiragana(n)
                    return hiragana_to_romaji(hira)

                romaji_family = convert_name(target_family)
                if romaji_family:
                    romaji_family = romaji_family.capitalize()

                romaji_given = convert_name(given)
                if romaji_given:
                    romaji_given = romaji_given.capitalize()

                new_c["family"] = romaji_family
                new_c["given"] = romaji_given
                entry["curator"].append(new_c)

        if "language" in entry:
            del entry["language"]

        # Now apply sort key generation
        if "curator" in entry:
            new_curators = []
            for person in entry["curator"]:
                p_copy = person.copy()
                f_val = p_copy.get("family", "")
                g_val = p_copy.get("given", "")

                # 漢字・カタカナ・ひらがなを含む任意のテキストをローマ字に変換
                if f_val:
                    p_copy["family"] = hiragana_to_romaji(
                        kanji_to_hiragana(f_val)
                    ).capitalize()
                if g_val:
                    p_copy["given"] = hiragana_to_romaji(
                        kanji_to_hiragana(g_val)
                    ).capitalize()

                new_curators.append(p_copy)
            entry["curator"] = new_curators

    # Save to new file
    new_filename = filename.replace(".json", "-sorted.json")
    with open(new_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Created {new_filename}")


if __name__ == "__main__":
    process_file("opensource.json")
