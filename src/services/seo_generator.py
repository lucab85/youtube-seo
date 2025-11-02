"""SEO generation service using AI/LLM for optimized metadata."""

import json
import re
from typing import Dict, List, Optional, Any
import openai
from anthropic import Anthropic
import google.generativeai as genai

from ..utils.config import Config
from ..utils.logger import get_logger
from ..utils.validators import enforce_character_limits, parse_tags_input, format_tags_output

logger = get_logger('seo_generator')


class SEOGenerator:
    """Generate SEO-optimized YouTube metadata using LLMs."""
    
    def __init__(self):
        """Initialize SEO generator with configured LLM provider."""
        self.provider = Config.get_llm_provider()
        
        if self.provider == 'openai':
            openai.api_key = Config.OPENAI_API_KEY
            self.model = Config.OPENAI_MODEL
            self.temperature = Config.OPENAI_TEMPERATURE
        elif self.provider == 'anthropic':
            self.anthropic_client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            self.model = Config.ANTHROPIC_MODEL
        elif self.provider == 'google':
            genai.configure(api_key=Config.GOOGLE_AI_API_KEY)
            self.model = Config.GOOGLE_AI_MODEL
            self.google_model = genai.GenerativeModel(self.model)
        
        logger.info(f"Initialized SEO generator with {self.provider} provider")
    
    def generate_metadata(
        self,
        transcript: str,
        video_title: Optional[str] = None,
        channel_description: Optional[str] = None,
        target_keywords: Optional[List[str]] = None,
        brand_config: Optional[Dict[str, Any]] = None,
        policy_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate optimized title, description, and tags.
        
        Args:
            transcript: Video transcript text
            video_title: Current video title (for context)
            channel_description: Channel description (for brand voice)
            target_keywords: List of target keywords
            brand_config: Brand configuration dict
            policy_config: Policy configuration dict
        
        Returns:
            Dict with 'title', 'description', 'tags' keys
        """
        logger.info("Generating SEO metadata")
        
        # Build prompt
        prompt = self._build_prompt(
            transcript=transcript,
            video_title=video_title,
            channel_description=channel_description,
            target_keywords=target_keywords,
            brand_config=brand_config,
            policy_config=policy_config
        )
        
        # Generate with LLM
        if self.provider == 'openai':
            raw_output = self._generate_with_openai(prompt)
        elif self.provider == 'anthropic':
            raw_output = self._generate_with_anthropic(prompt)
        elif self.provider == 'google':
            raw_output = self._generate_with_google(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        
        # Parse and validate output
        metadata = self._parse_llm_output(raw_output)
        
        # Enforce character limits and strip hashtags
        metadata = enforce_character_limits(
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            strict=True
        )
        
        # Apply policy filters
        if policy_config:
            metadata = self._apply_policy_filters(metadata, policy_config)
        
        logger.info("Successfully generated metadata")
        return metadata
    
    def _build_prompt(
        self,
        transcript: str,
        video_title: Optional[str],
        channel_description: Optional[str],
        target_keywords: Optional[List[str]],
        brand_config: Optional[Dict[str, Any]],
        policy_config: Optional[Dict[str, Any]]
    ) -> str:
        """Build comprehensive prompt for LLM."""
        
        # Truncate transcript if too long (keep first ~3000 words for context)
        transcript_words = transcript.split()
        if len(transcript_words) > 3000:
            transcript = ' '.join(transcript_words[:3000]) + '...'
        
        # Extract brand settings
        tone = brand_config.get('tone', 'professional') if brand_config else 'professional'
        style = brand_config.get('style', 'educational') if brand_config else 'educational'
        cta_template = brand_config.get('cta_template', '') if brand_config else ''
        allow_emojis = brand_config.get('allow_emojis', False) if brand_config else False
        
        # Extract policy settings
        required_disclosures = []
        if policy_config:
            required_disclosures = policy_config.get('required_disclosures', [])
        
        # Primary keyword
        primary_keyword = target_keywords[0] if target_keywords else "main topic"
        secondary_keywords = ', '.join(target_keywords[1:5]) if target_keywords and len(target_keywords) > 1 else ""
        
        prompt = f"""You are a senior YouTube SEO strategist with 10+ years of experience optimizing video content for maximum discoverability and engagement.

CRITICAL CONSTRAINTS:
- Title: EXACTLY ≤{Config.MAX_TITLE_LENGTH} characters (strict limit)
- Description: EXACTLY ≤{Config.MAX_DESCRIPTION_LENGTH} characters (strict limit)
- Tags: EXACTLY ≤{Config.MAX_TAGS_LENGTH} characters total, comma-separated list (strict limit)
- ABSOLUTELY NO hashtags (#) anywhere in title, description, or tags
- Use natural, conversational language
- Avoid keyword stuffing (keep density ~1-2%)
- Front-load primary keyword in first 10 words of description
- Be compelling but accurate (no misleading clickbait)

INPUTS:
- Primary Keyword: "{primary_keyword}"
- Secondary Keywords: "{secondary_keywords}"
- Brand Voice/Tone: {tone}
- Content Style: {style}
- Allow Emojis: {"Yes" if allow_emojis else "No"}

VIDEO TRANSCRIPT (cleaned, truncated):
\"\"\"
{transcript}
\"\"\"
"""

        if channel_description:
            prompt += f"""
CHANNEL CONTEXT:
{channel_description[:500]}
"""

        if video_title:
            prompt += f"""
CURRENT TITLE (for context):
{video_title}
"""

        prompt += """
TASK:
Generate YouTube metadata that maximizes:
1. Click-through rate (CTR) from search and suggested videos
2. Watch time and audience retention
3. Discoverability via YouTube and Google search

DESCRIPTION REQUIREMENTS:
- Target length: 3500-4500 characters (use FULL description space!)
- Must be comprehensive and detailed
- Must include multiple sections for better engagement
- CRITICAL: Use double line breaks (\\n\\n) between ALL sections for readability
- CRITICAL: Use single line breaks (\\n) within bullet lists
- CRITICAL: DO NOT include placeholder links like [Twitter] [LinkedIn] [Website]

DESCRIPTION STRUCTURE WITH PROPER FORMATTING:
1. Hook (first 150 chars): Include primary keyword + compelling value proposition
   [Double line break]

2. Overview (200-300 chars): Detailed summary of video content and key takeaways
   [Double line break]

3. What You'll Learn:
   Use this exact format with line breaks:
   • Point 1
   • Point 2
   • Point 3
   [Double line break]

4. TIMESTAMPS/CHAPTERS (REQUIRED):
   Extract from transcript with single line breaks between each:
   0:00 Introduction
   2:15 Topic 1
   5:30 Topic 2
   [Double line break]

5. Detailed Topics Covered (400-800 chars): In-depth explanation of each major topic discussed
   [Double line break]

6. Key Insights & Takeaways (200-400 chars): Summarize the most valuable information
   [Double line break]

7. Additional Resources:
   Only include if specific URLs or resources are mentioned in the video
   Format: "Resource Name: [leave space for manual URL addition]"
   DO NOT use placeholder text like [Link] or [Website]
   [Double line break]

8. About This Channel (100-200 chars): Brief channel description and content focus
   [Double line break]

9. Call-to-Action: """

        if cta_template:
            prompt += f"\"{cta_template}\""
        else:
            prompt += "Encourage subscription, likes, comments, and notifications. Keep it natural and conversational."

        prompt += """

IMPORTANT FORMATTING RULES:
- Use \\n\\n (double line break) between major sections
- Use \\n (single line break) between bullet points or timestamps
- DO NOT include any placeholder links or social media placeholders
- Make the description flow naturally and be easy to read
- Ensure proper spacing for YouTube's description format
"""

        if required_disclosures:
            prompt += f"""
11. Required Disclosures (MUST INCLUDE):
{chr(10).join(['   - ' + d for d in required_disclosures])}
"""

        prompt += """

TAGS STRATEGY:
- Include exactly 25-30 highly relevant tags (YouTube's maximum is 30 tags)
- MUST optimize for maximum 500 character total length AND 30 tag count limit
- Mix of:
  * Primary keyword variations (3-5 tags)
  * Broad category terms (3-5 tags)
  * Specific technical topics (5-7 tags)
  * Long-tail phrases (4-6 tags)
  * Related concepts, tools, and technologies (6-8 tags)
  * Common search queries (2-4 tags)
- Balance between longer descriptive tags and shorter high-volume search terms
- Include common misspellings if highly searched
- NO brand name spam
- NO hashtags (# symbols)
- Focus on search intent and related queries
- Prioritize tags that viewers would actually search for
- Include technical terms, tools, frameworks, and related technologies mentioned in the video

OUTPUT FORMAT (valid JSON only):
{
  "title": "Your optimized title here",
  "description": "Your optimized description here...",
  "tags": "tag one, tag two, tag three, tag four"
}

VALIDATION CHECKLIST (ensure these before responding):
✓ Title has primary keyword in first 5 words
✓ Description hook is compelling and includes primary keyword
✓ All character limits respected (Title≤100, Description≤5000, Tags≤500)
✓ No hashtags anywhere
✓ Natural language (not robotic or keyword-stuffed)
✓ CTA included in description
✓ Required disclosures included (if any)
✓ Tags are relevant and specific

Now generate the optimized metadata as JSON:
"""
        
        return prompt
    
    def _generate_with_openai(self, prompt: str) -> str:
        """Generate content using OpenAI API."""
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert YouTube SEO specialist. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info(f"Generated content with OpenAI (tokens: {response.usage.total_tokens})")
            return content
        
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    def _generate_with_anthropic(self, prompt: str) -> str:
        """Generate content using Anthropic Claude API."""
        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            logger.info(f"Generated content with Anthropic")
            return content
        
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise
    
    def _generate_with_google(self, prompt: str) -> str:
        """Generate content using Google AI (Gemini) API."""
        try:
            # Add JSON output instruction to prompt
            json_prompt = prompt + "\n\nIMPORTANT: Your response must be valid JSON only, no other text."
            
            response = self.google_model.generate_content(json_prompt)
            
            content = response.text
            logger.info(f"Generated content with Google AI (Gemini)")
            return content
        
        except Exception as e:
            logger.error(f"Google AI generation failed: {e}")
            raise
    
    def _parse_llm_output(self, raw_output: str) -> Dict[str, str]:
        """
        Parse LLM output and extract title, description, tags.
        
        Args:
            raw_output: Raw LLM response
        
        Returns:
            Dict with 'title', 'description', 'tags' keys
        """
        try:
            # Try to parse as JSON
            data = json.loads(raw_output)
            
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            tags = data.get('tags', '').strip()
            
            if not title or not description or not tags:
                raise ValueError("Missing required fields in LLM output")
            
            return {
                'title': title,
                'description': description,
                'tags': tags
            }
        
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_output, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    return {
                        'title': data.get('title', '').strip(),
                        'description': data.get('description', '').strip(),
                        'tags': data.get('tags', '').strip()
                    }
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Try to extract fields manually
            logger.warning("Failed to parse JSON, attempting manual extraction")
            
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', raw_output)
            desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', raw_output, re.DOTALL)
            tags_match = re.search(r'"tags"\s*:\s*"([^"]+)"', raw_output)
            
            if title_match and desc_match and tags_match:
                return {
                    'title': title_match.group(1).strip(),
                    'description': desc_match.group(1).strip(),
                    'tags': tags_match.group(1).strip()
                }
            
            raise ValueError("Could not parse LLM output")
    
    def _apply_policy_filters(
        self,
        metadata: Dict[str, str],
        policy_config: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Apply policy filters (prohibited terms, etc.).
        
        Args:
            metadata: Generated metadata dict
            policy_config: Policy configuration
        
        Returns:
            Filtered metadata dict
        """
        prohibited_terms = policy_config.get('prohibited_terms', [])
        
        # Check for prohibited terms
        for term in prohibited_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            
            # Check title
            if pattern.search(metadata['title']):
                logger.warning(f"Prohibited term '{term}' found in title, removing")
                metadata['title'] = pattern.sub('', metadata['title']).strip()
            
            # Check description
            if pattern.search(metadata['description']):
                logger.warning(f"Prohibited term '{term}' found in description, removing")
                metadata['description'] = pattern.sub('', metadata['description']).strip()
            
            # Check tags
            if pattern.search(metadata['tags']):
                logger.warning(f"Prohibited term '{term}' found in tags, removing")
                # Parse tags, filter out prohibited, and rejoin
                tags_list = parse_tags_input(metadata['tags'])
                filtered_tags = [tag for tag in tags_list if not pattern.search(tag)]
                metadata['tags'] = format_tags_output(filtered_tags)
        
        return metadata
    
    def extract_keywords(self, transcript: str, top_n: int = 20) -> List[str]:
        """
        Extract key phrases from transcript using NLP.
        
        Args:
            transcript: Video transcript
            top_n: Number of top keywords to return
        
        Returns:
            List of keywords
        """
        try:
            from keybert import KeyBERT
            
            kw_model = KeyBERT()
            keywords = kw_model.extract_keywords(
                transcript,
                keyphrase_ngram_range=(1, 3),
                stop_words='english',
                top_n=top_n,
                use_maxsum=True,
                nr_candidates=50
            )
            
            # Extract just the keyword strings
            keyword_list = [kw[0] for kw in keywords]
            
            logger.info(f"Extracted {len(keyword_list)} keywords")
            return keyword_list
        
        except ImportError:
            logger.warning("KeyBERT not available, using simple extraction")
            # Simple fallback: most common words
            words = re.findall(r'\b\w+\b', transcript.lower())
            from collections import Counter
            common_words = Counter(words).most_common(top_n)
            return [word for word, count in common_words]
        
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
