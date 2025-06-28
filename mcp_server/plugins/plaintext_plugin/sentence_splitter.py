"""Accurate sentence boundary detection for plain text."""

import re
from typing import List, Tuple


class SentenceSplitter:
    """Handles intelligent sentence boundary detection."""

    def __init__(self):
        # Common abbreviations that don't end sentences
        self.abbreviations = {
            "mr",
            "mrs",
            "ms",
            "dr",
            "prof",
            "sr",
            "jr",
            "ph.d",
            "md",
            "ba",
            "ma",
            "phd",
            "mba",
            "inc",
            "ltd",
            "co",
            "corp",
            "eg",
            "ie",
            "etc",
            "al",
            "st",
            "ave",
            "blvd",
            "vs",
            "viz",
            "cf",
            "op",
            "cit",
            "ibid",
            "jan",
            "feb",
            "mar",
            "apr",
            "jun",
            "jul",
            "aug",
            "sep",
            "sept",
            "oct",
            "nov",
            "dec",
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
            "sun",
        }

        # Compile regex patterns for efficiency
        self.sentence_end_pattern = re.compile(r"[.!?]+")
        self.decimal_pattern = re.compile(r"\d+\.\d+")
        self.ellipsis_pattern = re.compile(r"\.{3,}")
        self.url_pattern = re.compile(r"https?://[^\s]+|www\.[^\s]+")
        self.email_pattern = re.compile(r"\S+@\S+\.\S+")

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with intelligent boundary detection."""
        if not text:
            return []

        # Preserve URLs and emails by replacing them temporarily
        preserved_items = []

        # Preserve URLs
        for match in self.url_pattern.finditer(text):
            placeholder = f"<<URL_{len(preserved_items)}>>"
            preserved_items.append(match.group())
            text = text[: match.start()] + placeholder + text[match.end() :]

        # Preserve emails
        for match in self.email_pattern.finditer(text):
            placeholder = f"<<EMAIL_{len(preserved_items)}>>"
            preserved_items.append(match.group())
            text = text[: match.start()] + placeholder + text[match.end() :]

        # Preserve decimal numbers
        for match in self.decimal_pattern.finditer(text):
            placeholder = f"<<DECIMAL_{len(preserved_items)}>>"
            preserved_items.append(match.group())
            text = text[: match.start()] + placeholder + text[match.end() :]

        # Preserve ellipsis
        for match in self.ellipsis_pattern.finditer(text):
            placeholder = f"<<ELLIPSIS_{len(preserved_items)}>>"
            preserved_items.append(match.group())
            text = text[: match.start()] + placeholder + text[match.end() :]

        sentences = []
        current_sentence = []
        words = text.split()

        for i, word in enumerate(words):
            current_sentence.append(word)

            # Check if word ends with sentence terminator
            if self.sentence_end_pattern.search(word):
                # Check if it's an abbreviation
                word_lower = word.lower().rstrip(".!?")
                if word_lower in self.abbreviations:
                    continue

                # Check if next word starts with lowercase (likely continuation)
                if i + 1 < len(words) and words[i + 1][0].islower():
                    continue

                # Check if it's a single letter followed by period (e.g., "A.")
                if len(word_lower) == 1 and word.endswith("."):
                    continue

                # This is likely a sentence boundary
                sentence = " ".join(current_sentence)

                # Restore preserved items
                for j, item in enumerate(preserved_items):
                    sentence = sentence.replace(f"<<URL_{j}>>", item)
                    sentence = sentence.replace(f"<<EMAIL_{j}>>", item)
                    sentence = sentence.replace(f"<<DECIMAL_{j}>>", item)
                    sentence = sentence.replace(f"<<ELLIPSIS_{j}>>", item)

                sentences.append(sentence.strip())
                current_sentence = []

        # Add remaining words as last sentence
        if current_sentence:
            sentence = " ".join(current_sentence)

            # Restore preserved items
            for j, item in enumerate(preserved_items):
                sentence = sentence.replace(f"<<URL_{j}>>", item)
                sentence = sentence.replace(f"<<EMAIL_{j}>>", item)
                sentence = sentence.replace(f"<<DECIMAL_{j}>>", item)
                sentence = sentence.replace(f"<<ELLIPSIS_{j}>>", item)

            sentences.append(sentence.strip())

        return [s for s in sentences if s]

    def get_sentence_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """Get character offsets for sentence boundaries."""
        sentences = self.split_sentences(text)
        boundaries = []
        current_pos = 0

        for sentence in sentences:
            # Find the sentence in the original text
            start = text.find(sentence, current_pos)
            if start != -1:
                end = start + len(sentence)
                boundaries.append((start, end))
                current_pos = end

        return boundaries
