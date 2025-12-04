"""
Code Bug Analyzer Service

Provides actionable debugging context for bug reports by:
1. Extracting error patterns from messages (using LLM for accuracy)
2. Searching the codebase for related code
3. Matching against institutional memory for past solutions
4. Generating specific debugging steps
"""

import re
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
from openai import OpenAI

from ..config import settings

logger = logging.getLogger(__name__)


class CodeBugAnalyzer:
    """Analyzes bug reports to provide actionable debugging context."""
    
    # Fallback regex patterns (used if LLM fails)
    FILE_PATTERN = r'\b(\w+(?:_\w+)*\.py)\b'
    STATUS_CODE_PATTERN = r'\b(4\d{2}|5\d{2})\b'
    
    def __init__(self):
        self.base_dir = Path(settings.BASE_DIR)
        self.backend_dir = self.base_dir / "backend"
        self.context_dir = self.backend_dir / "context"
        self._memory_cache = None
        
        # Initialize OpenAI client for LLM-based extraction
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ CodeBugAnalyzer: OpenAI client initialized")
        else:
            self.openai_client = None
            logger.warning("⚠️ CodeBugAnalyzer: OpenAI not available, using regex fallback")
    
    async def analyze(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform bug analysis on a message.
        
        Simplified flow:
        1. Extract error patterns (LLM) - identifies errors, files, likely cause
        2. Find mentioned files (simple file find) - dogfooding the codebase
        3. Generate PM summary (LLM) - plain-language context for delegation
        
        Returns:
            Dict with pm_summary (high-level) and engineer_context (detailed)
        """
        message_text = message.get('text', '')
        
        logger.info(f"🔍 Analyzing bug report: {message_text[:50]}...")
        
        # Step 1: Extract error patterns using LLM
        patterns = await self.extract_error_patterns_llm(message_text)
        logger.info(f"📋 Extracted patterns: {len(patterns.get('exception_types', []))} exceptions, "
                   f"{len(patterns.get('status_codes', []))} status codes, "
                   f"{len(patterns.get('file_mentions', []))} files")
        
        # Step 2: Find mentioned files (simple, no LLM)
        codebase_matches = self.find_mentioned_files(patterns)
        logger.info(f"📂 Found {len(codebase_matches)} file(s) in codebase")
        
        # Step 3: Generate PM summary
        pm_summary = await self.generate_pm_summary(patterns, codebase_matches, [], message_text)
        logger.info(f"📝 Generated PM summary")
        
        # Structure output for dual audiences
        return {
            "pm_summary": pm_summary,
            "engineer_context": {
                "patterns": patterns,
                "affected_files": [m.get("file") for m in codebase_matches],
                "codebase_matches": codebase_matches
            },
            # Keep legacy fields for backward compatibility
            "patterns": patterns,
            "codebase_matches": codebase_matches,
            "memory_matches": [],
            "summary": pm_summary
        }
    
    async def extract_error_patterns_llm(self, message_text: str) -> Dict[str, List[str]]:
        """
        Extract error patterns using LLM for better accuracy.
        Understands natural language descriptions of errors, not just exact exception names.
        Falls back to regex if LLM is unavailable.
        """
        if not self.openai_client:
            logger.warning("OpenAI not available, falling back to regex extraction")
            return self._extract_error_patterns_regex(message_text)
        
        try:
            prompt = f"""Analyze this bug report and extract error information.

Bug Report:
"{message_text}"

Extract the following (return empty arrays if not found):
1. exception_types: Python exception names mentioned or implied (e.g., "TypeError", "IntegrityError", "ValidationError")
2. status_codes: HTTP status codes mentioned or implied (e.g., "500", "404", "429")  
3. file_mentions: Python file names mentioned (e.g., "cache_service.py", "routes.py")
4. class_mentions: Class or service names mentioned (e.g., "CacheService", "SlackIngester")
5. error_description: A brief description of what went wrong (1 sentence)
6. likely_cause: What might be causing this issue (1 sentence)

Respond with ONLY valid JSON (no markdown):
{{
  "exception_types": [],
  "status_codes": [],
  "file_mentions": [],
  "class_mentions": [],
  "error_description": "",
  "likely_cause": ""
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior Python engineer analyzing bug reports. Extract error information accurately. Only include items explicitly mentioned or clearly implied."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            # Ensure all expected keys exist
            patterns = {
                "exception_types": result.get("exception_types", []),
                "status_codes": [str(c) for c in result.get("status_codes", [])],
                "file_mentions": result.get("file_mentions", []),
                "class_mentions": result.get("class_mentions", []),
                "error_description": result.get("error_description", ""),
                "likely_cause": result.get("likely_cause", ""),
                "keywords": []  # Will be populated below
            }
            
            # Add keywords based on extracted info
            if patterns["exception_types"]:
                patterns["keywords"].append("exception")
            if patterns["status_codes"]:
                patterns["keywords"].append("http error")
            if any(code in ["500", "502", "503"] for code in patterns["status_codes"]):
                patterns["keywords"].append("server error")
            if any(code == "429" for code in patterns["status_codes"]):
                patterns["keywords"].append("rate limit")
            
            logger.info(f"🤖 LLM extracted: {patterns['exception_types']}, {patterns['status_codes']}, {patterns['file_mentions']}")
            return patterns
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}, falling back to regex")
            return self._extract_error_patterns_regex(message_text)
    
    def _extract_error_patterns_regex(self, message_text: str) -> Dict[str, List[str]]:
        """Fallback regex-based extraction if LLM is unavailable."""
        patterns = {
            "status_codes": [],
            "exception_types": [],
            "file_mentions": [],
            "class_mentions": [],
            "error_description": "",
            "likely_cause": "",
            "keywords": []
        }
        
        # Extract HTTP status codes
        status_matches = re.findall(self.STATUS_CODE_PATTERN, message_text)
        patterns["status_codes"] = list(set(status_matches))
        
        # Extract common exception types
        exception_patterns = [
            r'\b(TypeError|ValueError|KeyError|AttributeError|IndexError)\b',
            r'\b(IntegrityError|OperationalError|ProgrammingError)\b',
            r'\b(ValidationError|HTTPException|RequestValidationError)\b',
            r'\b(SlackApiError|BoltError|ClientError|TimeoutError|ConnectionError)\b',
        ]
        for pattern in exception_patterns:
            matches = re.findall(pattern, message_text, re.IGNORECASE)
            patterns["exception_types"].extend(matches)
        patterns["exception_types"] = list(set(patterns["exception_types"]))
        
        # Extract file mentions
        file_matches = re.findall(self.FILE_PATTERN, message_text)
        patterns["file_mentions"] = list(set(file_matches))
        
        # Extract class/service mentions
        class_pattern = r'\b([A-Z][a-zA-Z]+(?:Service|Handler|Client|Manager|Ingester|Parser))\b'
        class_matches = re.findall(class_pattern, message_text)
        patterns["class_mentions"] = list(set(class_matches))
        
        return patterns
    
    def find_mentioned_files(self, patterns: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Find files mentioned in the bug report.
        Simple approach: if a file is mentioned, find it in the codebase.
        No LLM, no complex grep - just file finding for dogfooding.
        """
        matches = []
        
        # Find files explicitly mentioned
        for file_name in patterns.get("file_mentions", []):
            file_match = self._find_file(file_name)
            if file_match:
                matches.append(file_match)
                logger.info(f"📁 Found mentioned file: {file_name}")
        
        return matches
    
    async def generate_pm_summary(
        self,
        patterns: Dict[str, List[str]],
        codebase_matches: List[Dict[str, Any]],
        memory_matches: List[Dict[str, Any]],
        message_text: str
    ) -> str:
        """
        Generate a high-level PM summary using LLM.
        Provides context for triage without requiring code knowledge.
        """
        if not self.openai_client:
            return self._generate_summary_fallback(patterns, codebase_matches, memory_matches)
        
        try:
            # Build context for LLM
            affected_files = list(set(m.get("file", "").split("/")[-1] for m in codebase_matches[:5] if m.get("file")))
            past_issues = [{"issue": m.get("issue"), "solution": m.get("solution")[:150]} for m in memory_matches[:2]]
            
            prompt = f"""Generate a 2-3 sentence summary of this bug for a Product Manager to understand and triage.

Bug Report: "{message_text}"

Analysis found:
- Error patterns: {patterns.get('exception_types', [])} {patterns.get('status_codes', [])}
- Likely cause: {patterns.get('likely_cause', 'Unknown')}
- Affected files: {affected_files}
- Similar past issues: {past_issues if past_issues else 'None found'}

Write a clear, non-technical summary that answers:
1. What's the issue? (in plain language)
2. Have we seen this before? (if yes, mention the past solution exists)
3. What area of the product is affected?

Keep it under 100 words. No bullet points, just flowing sentences."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a technical writer helping PMs understand engineering issues. Be clear and concise."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"📝 Generated PM summary: {summary[:100]}...")
            return summary
            
        except Exception as e:
            logger.warning(f"LLM PM summary generation failed: {e}")
            return self._generate_summary_fallback(patterns, codebase_matches, memory_matches)
    
    def _generate_summary_fallback(
        self,
        patterns: Dict[str, List[str]],
        codebase_matches: List[Dict[str, Any]],
        memory_matches: List[Dict[str, Any]]
    ) -> str:
        """Fallback summary when LLM is unavailable."""
        parts = []
        
        if patterns.get("error_description"):
            parts.append(patterns["error_description"])
        elif patterns.get("status_codes"):
            parts.append(f"HTTP {', '.join(patterns['status_codes'])} error detected.")
        elif patterns.get("exception_types"):
            parts.append(f"{', '.join(patterns['exception_types'])} error detected.")
        
        if memory_matches:
            parts.append(f"Similar to past issue: '{memory_matches[0].get('issue', 'Unknown')}' - solution exists.")
        
        if codebase_matches:
            files = list(set(m.get("file", "").split("/")[-1] for m in codebase_matches[:2]))
            parts.append(f"Affects: {', '.join(files)}.")
        
        return " ".join(parts) if parts else "Bug report received. No specific patterns detected."
    
    def _find_file(self, file_name: str) -> Optional[Dict[str, Any]]:
        """Find a specific file in the backend directory."""
        try:
            result = subprocess.run(
                ['find', str(self.backend_dir), '-name', file_name, '-type', 'f'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                file_path = result.stdout.strip().split('\n')[0]
                rel_path = Path(file_path).relative_to(self.base_dir)
                
                # Read first few lines to show context
                with open(file_path, 'r') as f:
                    lines = f.readlines()[:20]
                    preview = ''.join(lines)
                
                return {
                    "file": str(rel_path),
                    "line": 1,
                    "match_type": "file_reference",
                    "snippet": preview[:300] + "..." if len(preview) > 300 else preview
                }
        except Exception as e:
            logger.debug(f"Error finding file {file_name}: {e}")
        
        return None
    
    def _grep_codebase(self, term: str, context_lines: int = 2) -> List[Dict[str, Any]]:
        """Grep the codebase for a term."""
        matches = []
        
        try:
            result = subprocess.run(
                ['grep', '-rn', '-C', str(context_lines), '--include=*.py', term, str(self.backend_dir)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse grep output
                current_match = None
                for line in result.stdout.split('\n'):
                    if not line:
                        continue
                    
                    # Match format: file:line:content or file-line-content (context)
                    match = re.match(r'^(.+?)[:\-](\d+)[:\-](.*)$', line)
                    if match:
                        file_path, line_num, content = match.groups()
                        rel_path = str(Path(file_path).relative_to(self.base_dir))
                        
                        if ':' in line:  # Actual match line
                            matches.append({
                                "file": rel_path,
                                "line": int(line_num),
                                "match_type": "grep_match",
                                "term": term,
                                "snippet": content.strip()[:200]
                            })
        except subprocess.TimeoutExpired:
            logger.warning(f"Grep timeout for term: {term}")
        except Exception as e:
            logger.debug(f"Error grepping for {term}: {e}")
        
        return matches[:3]  # Limit per term
    
    def match_institutional_memory(
        self, 
        patterns: Dict[str, List[str]], 
        message_text: str
    ) -> List[Dict[str, Any]]:
        """Match against institutional memory for similar past issues."""
        memory = self._load_institutional_memory()
        if not memory:
            return []
        
        matches = []
        message_lower = message_text.lower()
        
        # Combine all patterns into search terms
        search_terms = (
            patterns.get("exception_types", []) +
            patterns.get("status_codes", []) +
            patterns.get("file_mentions", []) +
            patterns.get("class_mentions", []) +
            patterns.get("keywords", [])
        )
        
        for item in memory:
            issue = item.get("issue", "").lower()
            context = item.get("context", "").lower()
            solution = item.get("solution", "")
            
            # Calculate relevance score
            relevance = 0.0
            matched_terms = []
            
            # Check for term matches
            for term in search_terms:
                term_lower = term.lower()
                if term_lower in issue or term_lower in context:
                    relevance += 0.3
                    matched_terms.append(term)
            
            # Check for fuzzy similarity
            issue_similarity = SequenceMatcher(None, message_lower[:100], issue).ratio()
            if issue_similarity > 0.3:
                relevance += issue_similarity * 0.4
            
            # Boost for keyword matches in issue title
            for keyword in patterns.get("keywords", []):
                if keyword in issue:
                    relevance += 0.2
            
            if relevance > 0.2:  # Threshold for relevance
                matches.append({
                    "issue": item.get("issue"),
                    "context": item.get("context"),
                    "solution": solution,
                    "relevance": min(relevance, 1.0),
                    "matched_terms": matched_terms[:3]
                })
        
        # Sort by relevance and return top matches
        matches.sort(key=lambda x: x["relevance"], reverse=True)
        return matches[:3]
    
    def _load_institutional_memory(self) -> List[Dict[str, Any]]:
        """Load institutional memory from JSON file."""
        if self._memory_cache is not None:
            return self._memory_cache
        
        try:
            memory_file = self.context_dir / "institutional_memory.json"
            if memory_file.exists():
                with open(memory_file, 'r') as f:
                    self._memory_cache = json.load(f)
                    return self._memory_cache
        except Exception as e:
            logger.error(f"Error loading institutional memory: {e}")
        
        return []
    
    def generate_debugging_steps(
        self,
        patterns: Dict[str, List[str]],
        codebase_matches: List[Dict[str, Any]],
        memory_matches: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate specific debugging steps based on the analysis."""
        steps = []
        
        # Add steps based on exception types
        exception_steps = {
            "IntegrityError": [
                "Check database foreign key constraints",
                "Verify unique constraint violations",
                "Review recent database migrations"
            ],
            "TypeError": [
                "Check function parameter types",
                "Verify None values are handled",
                "Review type hints and validate input"
            ],
            "KeyError": [
                "Check dictionary key existence before access",
                "Use .get() with default values",
                "Verify JSON/dict structure matches expectations"
            ],
            "AttributeError": [
                "Verify object type before attribute access",
                "Check for None values",
                "Ensure proper initialization of objects"
            ],
            "ValidationError": [
                "Review Pydantic model field definitions",
                "Check input data format and types",
                "Verify API request body structure"
            ],
            "SlackApiError": [
                "Check Slack API token validity",
                "Verify required OAuth scopes",
                "Review Slack API rate limits"
            ],
        }
        
        for exc_type in patterns.get("exception_types", []):
            if exc_type in exception_steps:
                steps.extend(exception_steps[exc_type][:2])
        
        # Add steps based on status codes
        status_steps = {
            "429": [
                "Implement exponential backoff for API calls",
                "Check for Retry-After header and honor it",
                "Review API rate limit settings"
            ],
            "500": [
                "Check server logs for stack traces",
                "Verify database connectivity",
                "Review recent deployments for breaking changes"
            ],
            "404": [
                "Verify API endpoint path matches frontend calls",
                "Check route definitions in routes.py",
                "Ensure resource exists before access"
            ],
            "401": [
                "Check authentication token validity",
                "Verify API key or credentials",
                "Review OAuth token expiration"
            ],
            "400": [
                "Validate request payload format",
                "Check required fields in API request",
                "Review API documentation for expected format"
            ],
        }
        
        for code in patterns.get("status_codes", []):
            if code in status_steps:
                steps.extend(status_steps[code][:2])
        
        # Add file-specific steps
        for file_name in patterns.get("file_mentions", [])[:2]:
            steps.append(f"Review code in {file_name} for recent changes")
        
        # Add steps from memory matches
        for match in memory_matches[:2]:
            if match.get("solution"):
                solution_preview = match["solution"][:100]
                steps.append(f"Past solution for '{match['issue']}': {solution_preview}...")
        
        # Add generic steps if we don't have specific ones
        if not steps:
            steps = [
                "Check application logs for error details",
                "Review recent code changes in git history",
                "Verify environment variables and configuration",
                "Test the failing scenario locally"
            ]
        
        # Add codebase-specific steps
        if codebase_matches:
            top_file = codebase_matches[0].get("file", "")
            if top_file:
                steps.append(f"Start debugging from {top_file}")
        
        # Deduplicate while preserving order
        seen = set()
        unique_steps = []
        for step in steps:
            if step not in seen:
                seen.add(step)
                unique_steps.append(step)
        
        return unique_steps[:8]  # Limit to 8 steps
    
    def _generate_summary(
        self,
        patterns: Dict[str, List[str]],
        codebase_matches: List[Dict[str, Any]],
        memory_matches: List[Dict[str, Any]]
    ) -> str:
        """Generate a brief summary of the analysis."""
        parts = []
        
        # Summarize what was found
        if patterns.get("exception_types"):
            parts.append(f"Detected exceptions: {', '.join(patterns['exception_types'])}")
        
        if patterns.get("status_codes"):
            parts.append(f"HTTP errors: {', '.join(patterns['status_codes'])}")
        
        if patterns.get("file_mentions"):
            parts.append(f"Related files: {', '.join(patterns['file_mentions'])}")
        
        if codebase_matches:
            files = list(set(m.get("file", "").split("/")[-1] for m in codebase_matches[:3]))
            parts.append(f"Found references in: {', '.join(files)}")
        
        if memory_matches:
            parts.append(f"Similar past issues: {len(memory_matches)} found")
            if memory_matches[0].get("issue"):
                parts.append(f"Most relevant: '{memory_matches[0]['issue']}'")
        
        return " | ".join(parts) if parts else "No specific patterns detected"
