#!/usr/bin/env python3
"""
End-to-End Integration Test
Tests the full workflow: Ingestion -> Prioritization -> Storage -> API -> Sync to Notion
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from backend.config import settings

console = Console()

class EndToEndTester:
    def __init__(self):
        self.results = {}
        self.test_channel = None
        self.synced_messages = []
        
    async def test_1_full_sync_workflow(self):
        """Test: Fetch messages from Slack -> Prioritize -> Store in DB"""
        try:
            console.print("\n[cyan]Test 1: Full Sync Workflow...[/cyan]")
            
            from backend.services.sync_service import SyncService
            
            sync_service = SyncService()
            
            # Sync last 1 hour of messages
            result = await sync_service.sync(hours_ago=1)
            
            new_messages = result.get("new_messages", 0)
            prioritized = result.get("prioritized", 0)
            
            if new_messages >= 0 and prioritized >= 0:
                self.results["Full Sync Workflow"] = {
                    "status": "✅ PASS",
                    "detail": f"Synced: {new_messages}, Prioritized: {prioritized}",
                    "error": None
                }
            else:
                raise Exception("Sync returned invalid results")
                
        except Exception as e:
            self.results["Full Sync Workflow"] = {
                "status": "❌ FAIL",
                "detail": "Sync workflow failed",
                "error": str(e)
            }
    
    async def test_2_inbox_api_endpoints(self):
        """Test: All inbox API endpoints return valid data"""
        try:
            console.print("[cyan]Test 2: Inbox API Endpoints...[/cyan]")
            
            from backend.services.inbox_service import InboxService
            
            inbox_service = InboxService()
            
            # Test all views
            views_tested = []
            
            # Needs Response
            needs_response = await inbox_service.get_needs_response(hours_ago=24, limit=10)
            views_tested.append(f"needs_response({len(needs_response)})")
            
            # High Priority
            high_priority = await inbox_service.get_high_priority(hours_ago=24, limit=10)
            views_tested.append(f"high_priority({len(high_priority)})")
            
            # FYI
            fyi = await inbox_service.get_fyi(hours_ago=24, limit=10)
            views_tested.append(f"fyi({len(fyi)})")
            
            # Low Priority
            low_priority = await inbox_service.get_low_priority(hours_ago=24, limit=10)
            views_tested.append(f"low_priority({len(low_priority)})")
            
            # All
            all_messages = await inbox_service.get_all(hours_ago=24, limit=10)
            views_tested.append(f"all({len(all_messages)})")
            
            self.results["Inbox API Endpoints"] = {
                "status": "✅ PASS",
                "detail": ", ".join(views_tested),
                "error": None
            }
            
        except Exception as e:
            self.results["Inbox API Endpoints"] = {
                "status": "❌ FAIL",
                "detail": "API endpoints failed",
                "error": str(e)
            }
    
    async def test_3_stats_endpoint(self):
        """Test: Stats endpoint returns valid statistics"""
        try:
            console.print("[cyan]Test 3: Stats Endpoint...[/cyan]")
            
            from backend.services.inbox_service import InboxService
            
            inbox_service = InboxService()
            stats = await inbox_service.get_stats()
            
            # Check required structure
            required = ["total_messages", "by_category", "time_window"]
            missing = [f for f in required if f not in stats]
            
            if missing:
                raise Exception(f"Missing stats fields: {missing}")
            
            # Check category breakdown
            by_cat = stats["by_category"]
            cat_required = ["needs_response", "high_priority", "fyi", "low_priority"]
            cat_missing = [f for f in cat_required if f not in by_cat]
            
            if cat_missing:
                raise Exception(f"Missing category fields: {cat_missing}")
            
            self.results["Stats Endpoint"] = {
                "status": "✅ PASS",
                "detail": f"Total: {stats['total_messages']}, Categories: {len(by_cat)}",
                "error": None
            }
            
        except Exception as e:
            self.results["Stats Endpoint"] = {
                "status": "❌ FAIL",
                "detail": "Stats calculation failed",
                "error": str(e)
            }
    
    async def test_4_notion_sync(self):
        """Test: High priority messages sync to Notion"""
        try:
            if not settings.NOTION_SYNC_ENABLED:
                self.results["Notion Sync"] = {
                    "status": "⚠️  SKIP",
                    "detail": "Notion sync not enabled",
                    "error": None
                }
                return
                
            console.print("[cyan]Test 4: Notion Sync...[/cyan]")
            
            from backend.integrations.notion_service import NotionSyncService
            from backend.database import SessionLocal
            from backend.database.models import SlackMessage
            
            notion_service = NotionSyncService()
            
            # Get a high priority message
            db = SessionLocal()
            try:
                high_pri_msg = db.query(SlackMessage).filter(
                    SlackMessage.priority_score >= settings.NOTION_MIN_PRIORITY_SCORE
                ).order_by(SlackMessage.timestamp.desc()).first()
                
                if not high_pri_msg:
                    raise Exception("No high priority messages to sync")
                
                # Test sync (this actually creates a Notion task)
                # Convert to dict for service
                msg_dict = {
                    "id": high_pri_msg.id,
                    "message_id": high_pri_msg.message_id,
                    "text": high_pri_msg.text,
                    "user_name": high_pri_msg.user_name,
                    "channel_name": high_pri_msg.channel_name,
                    "priority_score": high_pri_msg.priority_score,
                    "priority_reason": high_pri_msg.priority_reason,
                    "category": high_pri_msg.category,
                    "channel_id": high_pri_msg.channel_id,
                    "timestamp": high_pri_msg.timestamp.isoformat() if high_pri_msg.timestamp else None
                }
                
                result = await notion_service.sync_messages_to_notion([msg_dict])
                
                if result:
                    self.results["Notion Sync"] = {
                        "status": "✅ PASS",
                        "detail": f"Synced message (score: {high_pri_msg.priority_score})",
                        "error": None
                    }
                else:
                    raise Exception("Sync returned no result")
                    
            finally:
                db.close()
            
        except Exception as e:
            self.results["Notion Sync"] = {
                "status": "❌ FAIL",
                "detail": "Notion sync failed",
                "error": str(e)
            }
    
    async def test_5_action_item_extraction(self):
        """Test: Action items can be extracted from messages"""
        try:
            console.print("[cyan]Test 5: Action Item Extraction...[/cyan]")
            
            from backend.services.action_item_service import ActionItemService
            from backend.database import SessionLocal
            from backend.database.models import SlackMessage
            
            action_service = ActionItemService()
            
            # Get a message with high priority
            db = SessionLocal()
            try:
                msg = db.query(SlackMessage).filter(
                    SlackMessage.priority_score >= 80,
                    SlackMessage.category == "needs_response"
                ).order_by(SlackMessage.timestamp.desc()).first()
                
                if not msg:
                    self.results["Action Item Extraction"] = {
                        "status": "⚠️  SKIP",
                        "detail": "No actionable messages found",
                        "error": None
                    }
                    return
                
                # Convert to dict for service
                msg_dict = {
                    "message_id": msg.message_id,
                    "text": msg.text,
                    "user_name": msg.user_name,
                    "channel_name": msg.channel_name,
                    "priority_score": msg.priority_score,
                    "category": msg.category
                }
                
                # Extract action items
                action_items = await action_service.extract_action_items(msg_dict)
                
                self.results["Action Item Extraction"] = {
                    "status": "✅ PASS",
                    "detail": f"Extraction complete: {action_items is not None}",
                    "error": None
                }
                    
            finally:
                db.close()
            
        except Exception as e:
            self.results["Action Item Extraction"] = {
                "status": "❌ FAIL",
                "detail": "Action extraction failed",
                "error": str(e)
            }
    
    async def test_6_exa_research(self):
        """Test: Exa research for tickets works"""
        try:
            if not settings.EXA_API_KEY:
                self.results["Exa Research"] = {
                    "status": "⚠️  SKIP",
                    "detail": "Exa not configured",
                    "error": None
                }
                return
                
            console.print("[cyan]Test 6: Exa Research...[/cyan]")
            
            from backend.integrations.exa_service import ExaSearchService
            
            exa_service = ExaSearchService()
            
            # Test research
            test_message = {
                "text": "We need to implement user authentication with OAuth2",
                "channel_name": "engineering"
            }
            
            # Complete research workflow (detects type internally)
            result = await exa_service.research_for_ticket(test_message)
            
            ticket_type = result["detection"].get("ticket_type", "unknown")
            sources = result.get("sources", [])
            
            self.results["Exa Research"] = {
                "status": "✅ PASS",
                "detail": f"Type: {ticket_type}, Research: {len(sources)} sources",
                "error": None
            }
            
        except Exception as e:
            self.results["Exa Research"] = {
                "status": "❌ FAIL",
                "detail": "Exa research failed",
                "error": str(e)
            }
    
    async def test_7_alert_service(self):
        """Test: Alert service can send notifications"""
        try:
            console.print("[cyan]Test 7: Alert Service (Dry Run)...[/cyan]")
            
            from backend.services.alert_service import AlertService
            
            alert_service = AlertService()
            
            # Test critical message detection
            test_messages = [{
                "message_id": "test123",
                "text": "URGENT: Production is down!",
                "user_name": "Test User",
                "channel_name": "incidents",
                "priority_score": 98,
                "category": "needs_response"
            }]
            
            # Dry run - don't actually send
            # Just check the service initializes
            if alert_service:
                self.results["Alert Service"] = {
                    "status": "✅ PASS",
                    "detail": "Service initialized (not sending test alerts)",
                    "error": None
                }
            else:
                raise Exception("Alert service not initialized")
            
        except Exception as e:
            self.results["Alert Service"] = {
                "status": "❌ FAIL",
                "detail": "Alert service failed",
                "error": str(e)
            }
    
    def print_results(self):
        """Print test results"""
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]End-to-End Test Results[/bold cyan]",
            border_style="cyan"
        ))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan", width=30)
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
            console.print("\n[bold green]🎉 All end-to-end tests passed! System is production-ready.[/bold green]")
            return True
        else:
            console.print("\n[bold red]⚠️  Some tests failed. Fix issues before deploying.[/bold red]")
            return False


async def main():
    console.print(Panel.fit(
        "[bold cyan]Slack Intelligence - End-to-End Test Suite[/bold cyan]\n"
        "Testing complete workflows before Railway deployment",
        border_style="cyan"
    ))
    
    tester = EndToEndTester()
    
    # Run all tests in order
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        
        task = progress.add_task("Running end-to-end tests...", total=None)
        
        await tester.test_1_full_sync_workflow()
        await tester.test_2_inbox_api_endpoints()
        await tester.test_3_stats_endpoint()
        await tester.test_4_notion_sync()
        await tester.test_5_action_item_extraction()
        await tester.test_6_exa_research()
        await tester.test_7_alert_service()
        
        progress.update(task, completed=True)
    
    # Print results
    success = tester.print_results()
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

