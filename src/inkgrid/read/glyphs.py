"""Glyph names no Unicode mapping defines, read without guessing (spec 13 section 3). Pure.

MuPDF reads a glyph name outside the Adobe Glyph List from its digits (`a71` is `G`, `a50` is `2`),
which invents a letter the page does not draw. The Adobe Glyph List specification applies the
ZapfDingbats glyph list to Zapf Dingbats fonts only: there, such a name is that list's character;
anywhere else, it is a glyph with no Unicode (U+FFFD).

`ZAPF_DINGBATS` is Adobe's ITC Zapf Dingbats Glyph List, table version 2.0 (2002-09-20), from
https://github.com/adobe-type-tools/agl-aglfn at commit 4036a9ca80a62f64f9de4f7321a9a045ad0ecfd6
(`zapfdingbats.txt`, SHA-256 f6394e3cb8a447e84a1dad75d4baaf2aa7f45dc104faf369f4720e1a774ef2dc),
under the license below.
"""

# Copyright 2002-2019 Adobe (http://www.adobe.com/).
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the
# following conditions are met:
#
# Redistributions of source code must retain the above
# copyright notice, this list of conditions and the following
# disclaimer.
#
# Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials
# provided with the distribution.
#
# Neither the name of Adobe nor the names of its contributors
# may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

REPLACEMENT = "\ufffd"
# A name MuPDF reads from its digits: `a71`, `50`, with any `.suffix`.
DIGIT_NAME: Final = re.compile(r"a?[0-9]+")
DINGBATS = "Dingbats"
_NAME = re.compile(r"/([^\s/\[\]<>(){}%]+)")

ZAPF_DINGBATS: Final[Mapping[str, int]] = MappingProxyType(
    {
        "a100": 0x275E,
        "a101": 0x2761,
        "a102": 0x2762,
        "a103": 0x2763,
        "a104": 0x2764,
        "a105": 0x2710,
        "a106": 0x2765,
        "a107": 0x2766,
        "a108": 0x2767,
        "a109": 0x2660,
        "a10": 0x2721,
        "a110": 0x2665,
        "a111": 0x2666,
        "a112": 0x2663,
        "a117": 0x2709,
        "a118": 0x2708,
        "a119": 0x2707,
        "a11": 0x261B,
        "a120": 0x2460,
        "a121": 0x2461,
        "a122": 0x2462,
        "a123": 0x2463,
        "a124": 0x2464,
        "a125": 0x2465,
        "a126": 0x2466,
        "a127": 0x2467,
        "a128": 0x2468,
        "a129": 0x2469,
        "a12": 0x261E,
        "a130": 0x2776,
        "a131": 0x2777,
        "a132": 0x2778,
        "a133": 0x2779,
        "a134": 0x277A,
        "a135": 0x277B,
        "a136": 0x277C,
        "a137": 0x277D,
        "a138": 0x277E,
        "a139": 0x277F,
        "a13": 0x270C,
        "a140": 0x2780,
        "a141": 0x2781,
        "a142": 0x2782,
        "a143": 0x2783,
        "a144": 0x2784,
        "a145": 0x2785,
        "a146": 0x2786,
        "a147": 0x2787,
        "a148": 0x2788,
        "a149": 0x2789,
        "a14": 0x270D,
        "a150": 0x278A,
        "a151": 0x278B,
        "a152": 0x278C,
        "a153": 0x278D,
        "a154": 0x278E,
        "a155": 0x278F,
        "a156": 0x2790,
        "a157": 0x2791,
        "a158": 0x2792,
        "a159": 0x2793,
        "a15": 0x270E,
        "a160": 0x2794,
        "a161": 0x2192,
        "a162": 0x27A3,
        "a163": 0x2194,
        "a164": 0x2195,
        "a165": 0x2799,
        "a166": 0x279B,
        "a167": 0x279C,
        "a168": 0x279D,
        "a169": 0x279E,
        "a16": 0x270F,
        "a170": 0x279F,
        "a171": 0x27A0,
        "a172": 0x27A1,
        "a173": 0x27A2,
        "a174": 0x27A4,
        "a175": 0x27A5,
        "a176": 0x27A6,
        "a177": 0x27A7,
        "a178": 0x27A8,
        "a179": 0x27A9,
        "a17": 0x2711,
        "a180": 0x27AB,
        "a181": 0x27AD,
        "a182": 0x27AF,
        "a183": 0x27B2,
        "a184": 0x27B3,
        "a185": 0x27B5,
        "a186": 0x27B8,
        "a187": 0x27BA,
        "a188": 0x27BB,
        "a189": 0x27BC,
        "a18": 0x2712,
        "a190": 0x27BD,
        "a191": 0x27BE,
        "a192": 0x279A,
        "a193": 0x27AA,
        "a194": 0x27B6,
        "a195": 0x27B9,
        "a196": 0x2798,
        "a197": 0x27B4,
        "a198": 0x27B7,
        "a199": 0x27AC,
        "a19": 0x2713,
        "a1": 0x2701,
        "a200": 0x27AE,
        "a201": 0x27B1,
        "a202": 0x2703,
        "a203": 0x2750,
        "a204": 0x2752,
        "a205": 0x276E,
        "a206": 0x2770,
        "a20": 0x2714,
        "a21": 0x2715,
        "a22": 0x2716,
        "a23": 0x2717,
        "a24": 0x2718,
        "a25": 0x2719,
        "a26": 0x271A,
        "a27": 0x271B,
        "a28": 0x271C,
        "a29": 0x2722,
        "a2": 0x2702,
        "a30": 0x2723,
        "a31": 0x2724,
        "a32": 0x2725,
        "a33": 0x2726,
        "a34": 0x2727,
        "a35": 0x2605,
        "a36": 0x2729,
        "a37": 0x272A,
        "a38": 0x272B,
        "a39": 0x272C,
        "a3": 0x2704,
        "a40": 0x272D,
        "a41": 0x272E,
        "a42": 0x272F,
        "a43": 0x2730,
        "a44": 0x2731,
        "a45": 0x2732,
        "a46": 0x2733,
        "a47": 0x2734,
        "a48": 0x2735,
        "a49": 0x2736,
        "a4": 0x260E,
        "a50": 0x2737,
        "a51": 0x2738,
        "a52": 0x2739,
        "a53": 0x273A,
        "a54": 0x273B,
        "a55": 0x273C,
        "a56": 0x273D,
        "a57": 0x273E,
        "a58": 0x273F,
        "a59": 0x2740,
        "a5": 0x2706,
        "a60": 0x2741,
        "a61": 0x2742,
        "a62": 0x2743,
        "a63": 0x2744,
        "a64": 0x2745,
        "a65": 0x2746,
        "a66": 0x2747,
        "a67": 0x2748,
        "a68": 0x2749,
        "a69": 0x274A,
        "a6": 0x271D,
        "a70": 0x274B,
        "a71": 0x25CF,
        "a72": 0x274D,
        "a73": 0x25A0,
        "a74": 0x274F,
        "a75": 0x2751,
        "a76": 0x25B2,
        "a77": 0x25BC,
        "a78": 0x25C6,
        "a79": 0x2756,
        "a7": 0x271E,
        "a81": 0x25D7,
        "a82": 0x2758,
        "a83": 0x2759,
        "a84": 0x275A,
        "a85": 0x276F,
        "a86": 0x2771,
        "a87": 0x2772,
        "a88": 0x2773,
        "a89": 0x2768,
        "a8": 0x271F,
        "a90": 0x2769,
        "a91": 0x276C,
        "a92": 0x276D,
        "a93": 0x276A,
        "a94": 0x276B,
        "a95": 0x2774,
        "a96": 0x2775,
        "a97": 0x275B,
        "a98": 0x275C,
        "a99": 0x275D,
        "a9": 0x2720,
    }
)


def stem(name: str) -> str:
    """The glyph name without its `.suffix`."""
    return name.split(".", 1)[0]


def glyph_reading(name: str, *, font: str, in_agl: bool) -> str | None:
    """The character a glyph named `name` in `font` reads as, or None to keep MuPDF's reading.

    `in_agl` says whether the Adobe Glyph List maps the name's stem; `font` is the font's name
    without its subset tag.
    """
    base = stem(name)
    if in_agl or DIGIT_NAME.fullmatch(base) is None:
        return None
    if DINGBATS in font and base in ZAPF_DINGBATS:
        return chr(ZAPF_DINGBATS[base])
    return REPLACEMENT


def differences_names(encoding: str) -> set[str]:
    """The glyph names of an `/Encoding` dictionary's `/Differences` array, as PDF text."""
    start = encoding.find("/Differences")
    if start < 0:
        return set()
    body = encoding[start + len("/Differences") :]
    close = body.find("]")
    return set(_NAME.findall(body[: close if close >= 0 else len(body)]))


def charset_names(charset: str) -> set[str]:
    """The glyph names of a font descriptor's `/CharSet` string."""
    return set(_NAME.findall(charset))
