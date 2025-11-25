"""
Context Service - The "Glue" for the Context Engine.
Aggregates identity, memory, codebase structure, and team info into a single context prompt.
NOW WITH RAG SUPPORT via MemoryService.
"""

import os
import json
import ast
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..config import settings
from ..database.db import SessionLocal
from ..database.models import SlackMessage
from .memory_service import MemoryService

logger = logging.getLogger(__name__)

class ContextService:
    """
    Aggregates all organizational context:
    1. Static Identity (Traverse.ai mission/values)
    2. Institutional Memory (RAG via Pinecone + Fallback to JSON)
    3. Dynamic Codebase Map (Self-awareness of project structure)
    4. Team Context (Active users from DB)
    """

    def __init__(self):
        self.base_dir = Path(settings.BASE_DIR)
        self.context_dir = self.base_dir / "backend" / "context"
        self.memory_service = MemoryService()
        
        # Cache keys
        self._identity_cache = None
        self._memory_cache = None
        self._codebase_cache = None
        self._plans_cache = None

    async def get_full_context(self, thread_messages: Optional[List[Dict[str, Any]]] = None, query: str = None) -> str:
        """
        Assemble the complete context string for the AI.
        
        Args:
            thread_messages: List of messages in current thread
            query: The specific issue/question to search memory for
        """
        identity = self._load_identity()
        codebase = self._scan_codebase()
        team = self._get_team_context()
        
        # RAG Memory Retrieval
        if query and self.memory_service.enabled:
            logger.info(f"🧠 Searching RAG memory for: {query}")
            rag_results = self.memory_service.search_memory(query)
            memory = self._format_rag_results(rag_results)
        else:
            memory = self._load_static_memory()
        
        # Load product plans/PRDs
        plans = self._load_plans()
        
        context_parts = [
            "=== COMPANY IDENTITY ===",
            identity,
            "\n=== INSTITUTIONAL MEMORY (Past Issues & Solutions) ===",
            memory,
            "\n=== PRODUCT PLANS & PRDs ===",
            plans,
            "\n=== CODEBASE STRUCTURE (Self-Awareness) ===",
            codebase,
            "\n=== TEAM CONTEXT ===",
            team
        ]
        
        if thread_messages:
            thread_context = self._format_thread_history(thread_messages)
            context_parts.append(f"\n=== THREAD HISTORY ===\n{thread_context}")
            
        return "\n".join(context_parts)

    def _format_rag_results(self, results: List[Dict[str, Any]]) -> str:
        """Format Pinecone results for the prompt."""
        if not results:
            return "No relevant past memories found."
            
        formatted = ["The following are relevant past messages/solutions from our history:"]
        for i, res in enumerate(results, 1):
            text = res.get("text", "").replace("\n", " ")
            score = res.get("score", 0)
            formatted.append(f"{i}. [Score: {score:.2f}] {text}")
            
        return "\n".join(formatted)

    def _load_identity(self) -> str:
        """Load static identity from markdown file."""
        if self._identity_cache:
            return self._identity_cache
            
        try:
            file_path = self.context_dir / "identity.md"
            if file_path.exists():
                self._identity_cache = file_path.read_text(encoding="utf-8")
            else:
                self._identity_cache = "Traverse.ai - Intelligent Slack Middleware Platform."
        except Exception as e:
            logger.error(f"Error loading identity: {e}")
            self._identity_cache = "Traverse.ai context unavailable."
            
        return self._identity_cache

    def _load_static_memory(self) -> str:
        """Fallback: Load institutional memory from JSON."""
        if self._memory_cache:
            return self._memory_cache
            
        try:
            file_path = self.context_dir / "institutional_memory.json"
            if file_path.exists():
                data = json.loads(file_path.read_text(encoding="utf-8"))
                formatted = []
                for item in data:
                    formatted.append(f"- Issue: {item['issue']}\n  Solution: {item['solution']}")
                self._memory_cache = "\n".join(formatted)
            else:
                self._memory_cache = "No institutional memory available."
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            self._memory_cache = "Error loading memory."
            
        return self._memory_cache

    def _load_plans(self) -> str:
        """Load product plans and PRDs from the plans directory."""
        if self._plans_cache:
            return self._plans_cache
            
        try:
            plans_dir = self.context_dir / "plans"
            if not plans_dir.exists():
                self._plans_cache = "No product plans available."
                return self._plans_cache
            
            formatted = []
            for plan_file in sorted(plans_dir.glob("*.md")):
                content = plan_file.read_text(encoding="utf-8")
                # Extract title (first # heading) and summary (first 200 chars after title)
                lines = content.split("\n")
                title = plan_file.stem.replace("_", " ").title()
                
                for line in lines:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                
                # Get summary - first paragraph after title
                summary_lines = []
                in_content = False
                for line in lines:
                    if line.startswith("# "):
                        in_content = True
                        continue
                    if in_content and line.strip():
                        summary_lines.append(line.strip())
                        if len(" ".join(summary_lines)) > 200:
                            break
                
                summary = " ".join(summary_lines)[:200]
                if len(summary) == 200:
                    summary += "..."
                
                formatted.append(f"📋 {title}\n   {summary}")
            
            if formatted:
                self._plans_cache = "\n\n".join(formatted)
            else:
                self._plans_cache = "No product plans available."
                
        except Exception as e:
            logger.error(f"Error loading plans: {e}")
            self._plans_cache = "Error loading plans."
            
        return self._plans_cache

    def get_plans_list(self) -> List[Dict[str, str]]:
        """Get list of plans with full content for dashboard display."""
        plans = []
        try:
            plans_dir = self.context_dir / "plans"
            if not plans_dir.exists():
                return plans
            
            for plan_file in sorted(plans_dir.glob("*.md")):
                content = plan_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                title = plan_file.stem.replace("_", " ").title()
                
                for line in lines:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                
                plans.append({
                    "filename": plan_file.name,
                    "title": title,
                    "content": content,
                    "summary": content[:300] + "..." if len(content) > 300 else content
                })
                
        except Exception as e:
            logger.error(f"Error getting plans list: {e}")
            
        return plans

    def _scan_codebase(self) -> str:
        """
        Dynamically scan the backend directory to build a map of files, classes, AND methods.
        """
        if self._codebase_cache:
            return self._codebase_cache
            
        structure = []
        backend_path = self.base_dir / "backend"
        
        try:
            for root, dirs, files in os.walk(backend_path):
                dirs[:] = [d for d in dirs if not d.startswith('__') and not d.startswith('.')]
                
                rel_path = Path(root).relative_to(self.base_dir)
                indent = "  " * (len(rel_path.parts) - 1)
                structure.append(f"{indent}📂 {rel_path.name}/")
                
                for file in sorted(files):
                    if file.endswith(".py") and not file.startswith("__"):
                        file_path = Path(root) / file
                        details = self._extract_definitions(file_path)
                        
                        structure.append(f"{indent}  📄 {file}")
                        if details:
                            for line in details:
                                structure.append(f"{indent}    {line}")
                        
            self._codebase_cache = "\n".join(structure)
        except Exception as e:
            logger.error(f"Error scanning codebase: {e}")
            self._codebase_cache = "Codebase structure unavailable."
            
        return self._codebase_cache

    def _extract_definitions(self, file_path: Path) -> List[str]:
        """Parse a python file to find class names and their method signatures."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            definitions = []
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    definitions.append(f"class {node.name}:")
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and not item.name.startswith("__"):
                            args = [arg.arg for arg in item.args.args if arg.arg != 'self']
                            definitions.append(f"  - {item.name}({', '.join(args)})")
                            
                elif isinstance(node, ast.FunctionDef) and not node.name.startswith("__"):
                    args = [arg.arg for arg in node.args.args]
                    definitions.append(f"def {node.name}({', '.join(args)})")
                    
            return definitions
        except:
            return []

    def _get_team_context(self) -> str:
        """Get active users from the database."""
        db = SessionLocal()
        try:
            users = db.query(SlackMessage.user_name, SlackMessage.user_id)\
                .distinct().limit(10).all()
            
            if not users:
                return "No active team members found in history."
                
            team_list = ["Active Team Members:"]
            for name, uid in users:
                if name and uid:
                    team_list.append(f"- {name} (ID: {uid})")
            
            return "\n".join(team_list)
        except Exception as e:
            logger.error(f"Error getting team context: {e}")
            return "Team context unavailable."
        finally:
            db.close()

    def _format_thread_history(self, messages: List[Dict[str, Any]]) -> str:
        """Format a list of thread messages for context."""
        if not messages:
            return "No thread history."
            
        formatted = []
        for msg in messages:
            user = msg.get('user_name', 'Unknown')
            text = msg.get('text', '').replace('\n', ' ')
            formatted.append(f"[{user}]: {text}")
        
        return "\n".join(formatted)
