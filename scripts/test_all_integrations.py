#!/usr/bin/env python3
"""
Comprehensive integration test script.
Tests all services before Railway deployment.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from backend.config import settings

console = Console()

class IntegrationTester:
    def __init__(self):
        self.results = {}
        
    async def test_slack_connection(self):
        """Test Slack API connection"""
        try:
            from slack_sdk import WebClient
            
            console.print("\n[cyan]Testing Slack connection...[/cyan]")
            bot_client = WebClient(token=settings.SLACK_BOT_TOKEN)
            
            # Test bot token
            response = bot_client.auth_test()
            bot_user = response.get("user", "Unknown")
            
            self.results["Slack Bot Token"] = {
                "status": "✅ PASS",
                "detail": f"Connected as {bot_user}",
                "error": None
            }
            
            # Test user token (if available)
            if settings.SLACK_USER_TOKEN:
                user_client = WebClient(token=settings.SLACK_USER_TOKEN)
                user_response = user_client.auth_test()
                user_name = user_response.get("user", "Unknown")
                self.results["Slack User Token"] = {
                    "status": "✅ PASS",
                    "detail": f"Connected as {user_name}",
                    "error": None
                }
            else:
                self.results["Slack User Token"] = {
                    "status": "⚠️  SKIP",
                    "detail": "Not configured",
                    "error": None
                }
                
        except Exception as e:
            self.results["Slack Connection"] = {
                "status": "❌ FAIL",
                "detail": "Connection failed",
                "error": str(e)
            }
    
    async def test_openai_connection(self):
        """Test OpenAI API connection"""
        try:
            from openai import AsyncOpenAI
            
            console.print("[cyan]Testing OpenAI connection...[/cyan]")
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Simple test call
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'test successful' in 2 words"}],
                max_tokens=10
            )
            
            result = response.choices[0].message.content
            
            self.results["OpenAI API"] = {
                "status": "✅ PASS",
                "detail": f"Response: {result}",
                "error": None
            }
            
        except Exception as e:
            self.results["OpenAI API"] = {
                "status": "❌ FAIL",
                "detail": "API call failed",
                "error": str(e)
            }
    
    async def test_exa_connection(self):
        """Test Exa API connection"""
        try:
            if not settings.EXA_API_KEY:
                self.results["Exa API"] = {
                    "status": "⚠️  SKIP",
                    "detail": "Not configured (optional)",
                    "error": None
                }
                return
                
            from exa_py import Exa
            
            console.print("[cyan]Testing Exa API connection...[/cyan]")
            exa = Exa(api_key=settings.EXA_API_KEY)
            
            # Simple search test
            results = exa.search("Python FastAPI", num_results=2)
            
            self.results["Exa API"] = {
                "status": "✅ PASS",
                "detail": f"Found {len(results.results)} results",
                "error": None
            }
            
        except Exception as e:
            self.results["Exa API"] = {
                "status": "❌ FAIL",
                "detail": "Search failed",
                "error": str(e)
            }
    
    async def test_jira_connection(self):
        """Test Jira API connection"""
        try:
            if not settings.JIRA_SYNC_ENABLED:
                self.results["Jira API"] = {
                    "status": "⚠️  SKIP",
                    "detail": "Not enabled (optional)",
                    "error": None
                }
                return
                
            from backend.integrations.jira_service import JiraService
            
            console.print("[cyan]Testing Jira connection...[/cyan]")
            jira_service = JiraService()
            
            # Test connection by getting project info
            project = jira_service.jira.project(settings.JIRA_PROJECT_KEY)
            
            self.results["Jira API"] = {
                "status": "✅ PASS",
                "detail": f"Connected to project: {project.name}",
                "error": None
            }
            
        except Exception as e:
            self.results["Jira API"] = {
                "status": "❌ FAIL",
                "detail": "Connection failed",
                "error": str(e)
            }
    
    async def test_notion_connection(self):
        """Test Notion API connection"""
        try:
            if not settings.NOTION_SYNC_ENABLED:
                self.results["Notion API"] = {
                    "status": "⚠️  SKIP",
                    "detail": "Not enabled (optional)",
                    "error": None
                }
                return
                
            import httpx
            
            console.print("[cyan]Testing Notion connection...[/cyan]")
            
            # Simple API test
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {settings.NOTION_API_KEY}",
                    "Notion-Version": "2022-06-28"
                }
                response = await client.get(
                    f"https://api.notion.com/v1/databases/{settings.NOTION_DATABASE_ID}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    db_name = data.get("title", [{}])[0].get("plain_text", "Unknown")
                    
                    self.results["Notion API"] = {
                        "status": "✅ PASS",
                        "detail": f"Connected to database: {db_name}",
                        "error": None
                    }
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            
        except Exception as e:
            self.results["Notion API"] = {
                "status": "❌ FAIL",
                "detail": "Connection failed",
                "error": str(e)
            }
    
    async def test_database_connection(self):
        """Test database initialization"""
        try:
            console.print("[cyan]Testing database connection...[/cyan]")
            
            from backend.database import init_db, SessionLocal
            from backend.database.models import SlackMessage
            
            # Initialize database
            init_db()
            
            # Test query
            db = SessionLocal()
            try:
                count = db.query(SlackMessage).count()
                self.results["Database (SQLite)"] = {
                    "status": "✅ PASS",
                    "detail": f"{count} messages in database",
                    "error": None
                }
            finally:
                db.close()
            
        except Exception as e:
            self.results["Database (SQLite)"] = {
                "status": "❌ FAIL",
                "detail": "Database error",
                "error": str(e)
            }
    
    async def test_ai_prioritization(self):
        """Test end-to-end prioritization"""
        try:
            console.print("[cyan]Testing AI prioritization...[/cyan]")
            
            from backend.ai.prioritizer import MessagePrioritizer
            from datetime import datetime
            
            prioritizer = MessagePrioritizer()
            
            # Create test message as dict (as expected by prioritizer)
            test_message = {
                "message_id": "test_" + datetime.now().isoformat(),
                "channel_id": "C123TEST",
                "channel_name": "test-channel",
                "user_id": "U123TEST",
                "user_name": "Test User",
                "text": "Can you help me with urgent deployment issue?",
                "timestamp": datetime.now().isoformat(),
                "thread_ts": None
            }
            
            # Prioritize
            result = await prioritizer.prioritize_batch([test_message])
            
            if result and len(result) > 0:
                score = result[0].get("priority_score")
                category = result[0].get("category")
                
                self.results["AI Prioritization"] = {
                    "status": "✅ PASS",
                    "detail": f"Score: {score}, Category: {category}",
                    "error": None
                }
            else:
                raise Exception("No prioritization result returned")
                
        except Exception as e:
            self.results["AI Prioritization"] = {
                "status": "❌ FAIL",
                "detail": "Prioritization failed",
                "error": str(e)
            }
    
    def print_results(self):
        """Print test results in a nice table"""
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]Integration Test Results[/bold cyan]",
            border_style="cyan"
        ))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Integration", style="cyan", width=20)
        table.add_column("Status", width=12)
        table.add_column("Details", width=40)
        
        for name, result in self.results.items():
            status_color = {
                "✅ PASS": "green",
                "❌ FAIL": "red",
                "⚠️  SKIP": "yellow"
            }.get(result["status"], "white")
            
            detail = result["detail"]
            if result["error"]:
                detail += f"\n[red]Error: {result['error'][:50]}...[/red]"
            
            table.add_row(
                name,
                f"[{status_color}]{result['status']}[/{status_color}]",
                detail
            )
        
        console.print(table)
        
        # Summary
        passed = sum(1 for r in self.results.values() if r["status"] == "✅ PASS")
        failed = sum(1 for r in self.results.values() if r["status"] == "❌ FAIL")
        skipped = sum(1 for r in self.results.values() if r["status"] == "⚠️  SKIP")
        
        console.print("\n")
        console.print(f"[green]✅ Passed: {passed}[/green]  ", end="")
        console.print(f"[red]❌ Failed: {failed}[/red]  ", end="")
        console.print(f"[yellow]⚠️  Skipped: {skipped}[/yellow]")
        
        if failed == 0:
            console.print("\n[bold green]🎉 All tests passed! Ready to deploy to Railway.[/bold green]")
            return True
        else:
            console.print("\n[bold red]⚠️  Some tests failed. Fix issues before deploying.[/bold red]")
            return False


async def main():
    console.print(Panel.fit(
        "[bold cyan]Slack Intelligence - Integration Test Suite[/bold cyan]\n"
        "Testing all services before Railway deployment",
        border_style="cyan"
    ))
    
    tester = IntegrationTester()
    
    # Run all tests
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        
        task = progress.add_task("Running integration tests...", total=None)
        
        await tester.test_database_connection()
        await tester.test_slack_connection()
        await tester.test_openai_connection()
        await tester.test_ai_prioritization()
        await tester.test_exa_connection()
        await tester.test_jira_connection()
        await tester.test_notion_connection()
        
        progress.update(task, completed=True)
    
    # Print results
    success = tester.print_results()
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

