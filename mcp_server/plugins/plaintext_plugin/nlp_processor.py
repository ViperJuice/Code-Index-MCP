"""Natural language processing features for plain text."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from .paragraph_detector import Paragraph, ParagraphDetector
from .sentence_splitter import SentenceSplitter
from .topic_extractor import Topic, TopicExtractor


class TextType(Enum):
    """Types of text content."""

    NARRATIVE = "narrative"
    TECHNICAL = "technical"
    INSTRUCTIONAL = "instructional"
    CONVERSATIONAL = "conversational"
    MIXED = "mixed"


@dataclass
class TextAnalysis:
    """Complete analysis of a text document."""

    text_type: TextType
    readability_score: float
    avg_sentence_length: float
    vocabulary_richness: float
    topics: List[Topic]
    key_phrases: List[str]
    summary_sentences: List[str]


class NLPProcessor:
    """Main NLP processing engine for plain text."""

    def __init__(self):
        self.sentence_splitter = SentenceSplitter()
        self.paragraph_detector = ParagraphDetector()
        self.topic_extractor = TopicExtractor()

    def analyze_text(self, text: str) -> TextAnalysis:
        """Perform comprehensive text analysis."""
        # Basic preprocessing
        cleaned_text = self._preprocess_text(text)

        # Extract components
        sentences = self.sentence_splitter.split_sentences(cleaned_text)
        paragraphs = self.paragraph_detector.detect_paragraphs(cleaned_text)

        # Analyze text characteristics
        text_type = self._determine_text_type(cleaned_text, sentences, paragraphs)
        readability = self._calculate_readability(sentences)
        avg_sentence_length = self._average_sentence_length(sentences)
        vocab_richness = self._vocabulary_richness(cleaned_text)

        # Extract topics and key phrases
        topics = self.topic_extractor.extract_topics(cleaned_text)
        key_phrases = self.topic_extractor.extract_key_phrases(cleaned_text)

        # Generate summary sentences
        summary = self._extract_summary_sentences(sentences, topics)

        return TextAnalysis(
            text_type=text_type,
            readability_score=readability,
            avg_sentence_length=avg_sentence_length,
            vocabulary_richness=vocab_richness,
            topics=topics,
            key_phrases=key_phrases,
            summary_sentences=summary,
        )

    def extract_semantic_chunks(self, text: str, target_size: int = 500) -> List[str]:
        """Extract semantically coherent chunks from text."""
        paragraphs = self.paragraph_detector.detect_paragraphs(text)

        # Merge small paragraphs
        merged_paragraphs = self.paragraph_detector.merge_related_paragraphs(paragraphs)

        chunks = []
        current_chunk = []
        current_size = 0

        for para in merged_paragraphs:
            para_size = len(para.text)

            # If paragraph is too large, split by sentences
            if para_size > target_size * 1.5:
                sentences = self.sentence_splitter.split_sentences(para.text)

                for sentence in sentences:
                    sentence_size = len(sentence)

                    if current_size + sentence_size > target_size and current_chunk:
                        # Save current chunk
                        chunks.append(" ".join(current_chunk))
                        current_chunk = [sentence]
                        current_size = sentence_size
                    else:
                        current_chunk.append(sentence)
                        current_size += sentence_size
            else:
                # Add whole paragraph
                if current_size + para_size > target_size and current_chunk:
                    # Save current chunk
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = [para.text]
                    current_size = para_size
                else:
                    current_chunk.append(para.text)
                    current_size += para_size

        # Don't forget the last chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def extract_structured_content(self, text: str) -> Dict[str, List[str]]:
        """Extract structured content like lists, code blocks, etc."""
        structured = {
            "headings": [],
            "lists": [],
            "code_blocks": [],
            "quotes": [],
            "definitions": [],
        }

        paragraphs = self.paragraph_detector.detect_paragraphs(text)

        for para in paragraphs:
            # Code blocks
            if para.is_code_block:
                structured["code_blocks"].append(para.text)
                continue

            # Lists
            if para.is_list_item:
                structured["lists"].append(para.text)
                continue

            # Headings (simple heuristic)
            if self._is_likely_heading(para.text):
                structured["headings"].append(para.text.strip())
                continue

            # Quotes (lines starting with > or ")
            if para.text.strip().startswith(('"', ">", '"', '"')):
                structured["quotes"].append(para.text)
                continue

            # Definitions (contains "is defined as", "means", etc.)
            if self._is_likely_definition(para.text):
                structured["definitions"].append(para.text)

        return structured

    def _preprocess_text(self, text: str) -> str:
        """Basic text preprocessing."""
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)

        # Fix common encoding issues
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(""", "'").replace(""", "'")
        text = text.replace("—", "--").replace("–", "-")

        return text.strip()

    def _determine_text_type(
        self, text: str, sentences: List[str], paragraphs: List[Paragraph]
    ) -> TextType:
        """Determine the type of text content."""
        # Count various indicators
        technical_terms = len(self.topic_extractor._extract_special_terms(text))
        code_blocks = sum(1 for p in paragraphs if p.is_code_block)
        lists = sum(1 for p in paragraphs if p.is_list_item)
        questions = sum(1 for s in sentences if s.strip().endswith("?"))
        imperatives = sum(1 for s in sentences if self._is_imperative(s))

        total_sentences = len(sentences)
        if total_sentences == 0:
            return TextType.MIXED

        # Calculate ratios
        technical_ratio = technical_terms / total_sentences
        code_ratio = code_blocks / len(paragraphs) if paragraphs else 0
        list_ratio = lists / len(paragraphs) if paragraphs else 0
        question_ratio = questions / total_sentences
        imperative_ratio = imperatives / total_sentences

        # Determine type based on ratios
        if technical_ratio > 0.3 or code_ratio > 0.2:
            return TextType.TECHNICAL
        elif imperative_ratio > 0.3 or list_ratio > 0.3:
            return TextType.INSTRUCTIONAL
        elif question_ratio > 0.2:
            return TextType.CONVERSATIONAL
        elif technical_ratio < 0.1 and question_ratio < 0.1:
            return TextType.NARRATIVE
        else:
            return TextType.MIXED

    def _calculate_readability(self, sentences: List[str]) -> float:
        """Calculate readability score (simplified Flesch Reading Ease)."""
        if not sentences:
            return 0.0

        total_words = 0
        total_syllables = 0

        for sentence in sentences:
            words = sentence.split()
            total_words += len(words)

            for word in words:
                # Simple syllable counting
                syllables = max(1, len(re.findall(r"[aeiouAEIOU]", word)))
                total_syllables += syllables

        if total_words == 0:
            return 0.0

        avg_sentence_length = total_words / len(sentences)
        avg_syllables_per_word = total_syllables / total_words

        # Simplified Flesch Reading Ease formula
        score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word

        # Normalize to 0-100
        return max(0, min(100, score))

    def _average_sentence_length(self, sentences: List[str]) -> float:
        """Calculate average sentence length in words."""
        if not sentences:
            return 0.0

        total_words = sum(len(s.split()) for s in sentences)
        return total_words / len(sentences)

    def _vocabulary_richness(self, text: str) -> float:
        """Calculate vocabulary richness (type-token ratio)."""
        words = text.lower().split()
        if not words:
            return 0.0

        unique_words = set(words)
        return len(unique_words) / len(words)

    def _is_imperative(self, sentence: str) -> bool:
        """Check if sentence is likely imperative."""
        # Simple heuristic: starts with verb
        imperative_starts = [
            "do",
            "don't",
            "please",
            "let",
            "make",
            "take",
            "give",
            "get",
            "put",
            "keep",
            "turn",
            "start",
            "stop",
            "try",
            "use",
            "add",
            "remove",
            "check",
            "verify",
            "ensure",
        ]

        first_word = sentence.strip().split()[0].lower() if sentence.strip() else ""
        return first_word in imperative_starts

    def _is_likely_heading(self, text: str) -> bool:
        """Check if text is likely a heading."""
        text = text.strip()

        # Short and no ending punctuation
        if len(text.split()) <= 10 and not text.endswith((".", "!", "?")):
            # Starts with capital or number
            if text and (text[0].isupper() or text[0].isdigit()):
                return True

        # All caps
        if text.isupper():
            return True

        # Markdown heading
        if text.startswith("#"):
            return True

        return False

    def _is_likely_definition(self, text: str) -> bool:
        """Check if text is likely a definition."""
        definition_patterns = [
            r"\bis defined as\b",
            r"\bmeans\b",
            r"\brefers to\b",
            r"\bis\s+(?:a|an|the)\b",
            r":\s*(?:a|an|the)\s+\w+",
            r"—\s*(?:a|an|the)\s+\w+",
        ]

        text_lower = text.lower()
        for pattern in definition_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _extract_summary_sentences(
        self, sentences: List[str], topics: List[Topic], max_sentences: int = 5
    ) -> List[str]:
        """Extract sentences that best summarize the text."""
        if not sentences:
            return []

        # Score sentences based on keyword coverage
        topic_keywords = set()
        for topic in topics:
            topic_keywords.update(topic.keywords)

        sentence_scores = []

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Count topic keyword occurrences
            keyword_count = sum(1 for kw in topic_keywords if kw in sentence_lower)

            # Prefer sentences that are not too short or too long
            length_score = 1.0
            word_count = len(sentence.split())
            if word_count < 5:
                length_score = 0.5
            elif word_count > 30:
                length_score = 0.8

            # Calculate final score
            score = keyword_count * length_score

            # Boost first and last sentences slightly
            if sentence == sentences[0] or sentence == sentences[-1]:
                score *= 1.2

            sentence_scores.append((sentence, score))

        # Sort by score and return top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)

        # Get top sentences but maintain their original order
        top_sentences = [s for s, _ in sentence_scores[:max_sentences]]

        # Reorder to maintain narrative flow
        summary = []
        for sentence in sentences:
            if sentence in top_sentences:
                summary.append(sentence)

        return summary
