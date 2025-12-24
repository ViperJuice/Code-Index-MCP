"""Topic modeling and keyword extraction for plain text."""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Topic:
    """Represents an extracted topic."""

    keywords: List[str]
    score: float
    related_terms: List[str]


class TopicExtractor:
    """Extracts topics and keywords from plain text."""

    def __init__(self):
        # Common English stop words
        self.stop_words = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "been",
            "by",
            "for",
            "from",
            "has",
            "have",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "ought",
            "used",
            "had",
            "having",
            "do",
            "does",
            "did",
            "doing",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "them",
            "their",
            "this",
            "that",
            "these",
            "those",
            "am",
            "is",
            "are",
            "was",
            "were",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "shall",
            "ought",
            "need",
            "dare",
            "used",
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "if",
            "because",
            "as",
            "until",
            "while",
            "of",
            "at",
            "by",
            "for",
            "with",
            "about",
            "against",
            "between",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "to",
            "from",
            "up",
            "down",
            "in",
            "out",
            "on",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
        }

        # Patterns for different types of terms
        self.camel_case_pattern = re.compile(r"[A-Z][a-z]+(?:[A-Z][a-z]+)*")
        self.snake_case_pattern = re.compile(r"[a-z]+(?:_[a-z]+)+")
        self.kebab_case_pattern = re.compile(r"[a-z]+(?:-[a-z]+)+")
        self.acronym_pattern = re.compile(r"\b[A-Z]{2,}\b")
        self.word_pattern = re.compile(r"\b\w+\b")

    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[Tuple[str, float]]:
        """Extract keywords using TF-IDF-like scoring."""
        # Tokenize and clean
        words = self.word_pattern.findall(text.lower())
        words = [w for w in words if w not in self.stop_words and len(w) > 2]

        # Also extract special terms (camelCase, snake_case, etc.)
        special_terms = self._extract_special_terms(text)

        # Calculate term frequency
        tf = Counter(words)

        # Add special terms with boost
        for term in special_terms:
            tf[term.lower()] = tf.get(term.lower(), 0) + 2

        # Calculate scores (simplified TF-IDF)
        total_words = sum(tf.values())
        scores = {}

        for word, count in tf.items():
            # Term frequency
            term_freq = count / total_words

            # Inverse document frequency approximation (boost rare terms)
            idf = math.log(1 + (total_words / count))

            # Combined score
            scores[word] = term_freq * idf

            # Boost technical terms
            if self._is_technical_term(word):
                scores[word] *= 1.5

        # Sort by score and return top keywords
        sorted_keywords = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_keywords[:max_keywords]

    def extract_topics(self, text: str, num_topics: int = 5) -> List[Topic]:
        """Extract main topics from text using co-occurrence analysis."""
        # Get sentences for co-occurrence analysis
        sentences = text.split(".")

        # Build co-occurrence matrix
        cooccurrence = defaultdict(lambda: defaultdict(int))
        keywords = [kw for kw, _ in self.extract_keywords(text, max_keywords=50)]
        _ = set(keywords)

        for sentence in sentences:
            sentence_lower = sentence.lower()
            found_keywords = [kw for kw in keywords if kw in sentence_lower]

            # Count co-occurrences
            for i, kw1 in enumerate(found_keywords):
                for kw2 in found_keywords[i + 1 :]:
                    cooccurrence[kw1][kw2] += 1
                    cooccurrence[kw2][kw1] += 1

        # Cluster keywords into topics using simple greedy clustering
        topics = []
        used_keywords = set()

        for seed_keyword in keywords:
            if seed_keyword in used_keywords:
                continue

            # Find related keywords
            related = []
            if seed_keyword in cooccurrence:
                related_scores = sorted(
                    cooccurrence[seed_keyword].items(), key=lambda x: x[1], reverse=True
                )
                related = [kw for kw, _ in related_scores[:5] if kw not in used_keywords]

            if len(related) >= 2:  # Only create topic if we have related terms
                topic_keywords = [seed_keyword] + related[:4]
                used_keywords.update(topic_keywords)

                # Calculate topic score based on keyword frequencies
                topic_score = sum(
                    next(
                        (score for kw, score in self.extract_keywords(text, 50) if kw == k),
                        0,
                    )
                    for k in topic_keywords
                ) / len(topic_keywords)

                topics.append(
                    Topic(
                        keywords=topic_keywords,
                        score=topic_score,
                        related_terms=self._find_related_terms(text, topic_keywords),
                    )
                )

            if len(topics) >= num_topics:
                break

        # Sort by score
        topics.sort(key=lambda t: t.score, reverse=True)
        return topics[:num_topics]

    def extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract multi-word key phrases."""
        # Simple n-gram approach for key phrases
        phrases = []
        sentences = text.split(".")

        for sentence in sentences:
            words = self.word_pattern.findall(sentence.lower())

            # Extract 2-grams and 3-grams
            for n in [2, 3]:
                for i in range(len(words) - n + 1):
                    ngram = words[i : i + n]

                    # Filter out n-grams with too many stop words
                    stop_count = sum(1 for w in ngram if w in self.stop_words)
                    if stop_count <= n // 2:  # At most half can be stop words
                        phrase = " ".join(ngram)
                        phrases.append(phrase)

        # Count and rank phrases
        phrase_counts = Counter(phrases)

        # Filter out rare phrases
        phrase_counts = {p: c for p, c in phrase_counts.items() if c > 1}

        # Sort by count
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
        return [phrase for phrase, _ in sorted_phrases[:max_phrases]]

    def _extract_special_terms(self, text: str) -> List[str]:
        """Extract special terms like CamelCase, snake_case, etc."""
        special_terms = []

        # CamelCase
        special_terms.extend(self.camel_case_pattern.findall(text))

        # snake_case
        special_terms.extend(self.snake_case_pattern.findall(text))

        # kebab-case
        special_terms.extend(self.kebab_case_pattern.findall(text))

        # Acronyms
        special_terms.extend(self.acronym_pattern.findall(text))

        return list(set(special_terms))

    def _is_technical_term(self, word: str) -> bool:
        """Check if word appears to be a technical term."""
        # Contains numbers
        if any(c.isdigit() for c in word):
            return True

        # Contains special characters (but not just punctuation)
        if "_" in word or "-" in word:
            return True

        # Common technical suffixes
        tech_suffixes = ["tion", "ment", "ize", "ise", "ify", "ate", "able", "ible"]
        for suffix in tech_suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 3:
                return True

        return False

    def _find_related_terms(self, text: str, keywords: List[str]) -> List[str]:
        """Find terms related to given keywords."""
        related = set()
        text_lower = text.lower()

        for keyword in keywords:
            # Find words that often appear near this keyword
            pattern = re.compile(rf"\b(\w+)\s+{re.escape(keyword)}|{re.escape(keyword)}\s+(\w+)\b")
            matches = pattern.findall(text_lower)

            for match in matches:
                for word in match:
                    if word and word not in self.stop_words and len(word) > 2:
                        related.add(word)

        # Remove the keywords themselves
        related -= set(keywords)

        return list(related)[:10]  # Limit to 10 related terms

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts based on keywords."""
        keywords1 = set(kw for kw, _ in self.extract_keywords(text1, 20))
        keywords2 = set(kw for kw, _ in self.extract_keywords(text2, 20))

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard similarity
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        return len(intersection) / len(union)
