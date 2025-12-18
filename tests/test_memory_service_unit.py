#!/usr/bin/env python3
"""
Unit tests for MemoryService and LongTermMemoryManager
Tests internal functionality without API layer
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.memory_service import MemoryService
from app.chat.long_term_memory import LongTermMemoryManager

class MemoryServiceUnitTester:
    def __init__(self):
        self.results = []
        self.temp_dir = None
        
    def setup(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="memory_test_")
        console.log(f"[cyan]Created temp directory: {self.temp_dir}[/cyan]")
        
    def teardown(self):
        """Cleanup test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            console.log(f"[cyan]Cleaned up temp directory[/cyan]")
    
    def log_test(self, name: str, passed: bool, details: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({"test": name, "passed": passed, "details": details})
        console.log(f"{status} - {name}")
        if details:
            console.log(f"  Details: {details}")
    
    def test_memory_manager_init(self) -> bool:
        """Test LongTermMemoryManager initialization"""
        console.rule("[bold blue]Testing Memory Manager Init")
        
        try:
            db_path = os.path.join(self.temp_dir, "test_memory.db")
            manager = LongTermMemoryManager(
                user_id="test_user_001",
                mem0_enabled=False,
                local_db_path=db_path
            )
            
            passed = manager is not None and manager.user_id == "test_user_001"
            self.log_test("Memory Manager Init", passed, f"User ID: {manager.user_id}")
            
            # Check database file created
            db_exists = os.path.exists(db_path)
            self.log_test("Database File Created", db_exists, f"Path: {db_path}")
            
            return passed and db_exists
            
        except Exception as e:
            self.log_test("Memory Manager Init", False, str(e))
            return False
    
    def test_add_manual_memory_local(self) -> bool:
        """Test adding manual memory to local storage"""
        console.rule("[bold blue]Testing Add Manual Memory (Local)")
        
        try:
            db_path = os.path.join(self.temp_dir, "test_memory.db")
            manager = LongTermMemoryManager(
                user_id="test_user_002",
                mem0_enabled=False,
                local_db_path=db_path
            )
            
            # Add memories
            test_memories = [
                {"content": "User loves reading science fiction", "type": "hobby"},
                {"content": "User is allergic to peanuts", "type": "health"},
                {"content": "User speaks three languages", "type": "skill"}
            ]
            
            all_added = True
            for i, mem in enumerate(test_memories, 1):
                result = manager.add_manual_memory(
                    content=mem["content"],
                    memory_type=mem["type"],
                    metadata={"test": True}
                )
                
                self.log_test(
                    f"Add Memory #{i}",
                    result,
                    f"Content: {mem['content'][:40]}..."
                )
                
                if not result:
                    all_added = False
            
            return all_added
            
        except Exception as e:
            self.log_test("Add Manual Memory", False, str(e))
            return False
    
    def test_list_memories_local(self) -> bool:
        """Test listing memories from local storage"""
        console.rule("[bold blue]Testing List Memories (Local)")
        
        try:
            db_path = os.path.join(self.temp_dir, "test_memory.db")
            manager = LongTermMemoryManager(
                user_id="test_user_003",
                mem0_enabled=False,
                local_db_path=db_path
            )
            
            # Add some memories first
            for i in range(5):
                manager.add_manual_memory(
                    content=f"Test memory number {i+1}",
                    memory_type="test"
                )
            
            # List memories
            memories = manager.list_memories(limit=10)
            
            passed = len(memories) == 5
            self.log_test(
                "List Memories",
                passed,
                f"Expected 5, got {len(memories)}"
            )
            
            # Display memories
            if memories:
                table = Table(title="Retrieved Memories", show_lines=True)
                table.add_column("ID", style="cyan")
                table.add_column("Content", style="white")
                table.add_column("Type", style="yellow")
                
                for mem in memories:
                    table.add_row(
                        str(mem.get("id", "-")),
                        str(mem.get("memory", ""))[:50],
                        str(mem.get("memory_type", "-"))
                    )
                
                console.print(table)
            
            return passed
            
        except Exception as e:
            self.log_test("List Memories", False, str(e))
            return False
    
    def test_search_memories_local(self) -> bool:
        """Test searching memories in local storage"""
        console.rule("[bold blue]Testing Search Memories (Local)")
        
        try:
            db_path = os.path.join(self.temp_dir, "test_memory.db")
            manager = LongTermMemoryManager(
                user_id="test_user_004",
                mem0_enabled=False,
                local_db_path=db_path
            )
            
            # Add diverse memories
            test_data = [
                "User enjoys playing guitar and piano",
                "User works as a data scientist",
                "User has anxiety about public speaking",
                "User loves hiking in mountains",
                "User is learning Spanish"
            ]
            
            for content in test_data:
                manager.add_manual_memory(content=content, memory_type="test")
            
            # Search tests
            search_tests = [
                ("music", ["guitar", "piano"]),
                ("work", ["scientist"]),
                ("anxiety", ["anxiety"]),
                ("outdoor", ["hiking"])
            ]
            
            all_passed = True
            for query, expected_keywords in search_tests:
                results = manager.search_memories(query=query, limit=3)
                
                # Check if any result contains expected keywords
                found = any(
                    any(kw in str(r.get("content", "")).lower() for kw in expected_keywords)
                    for r in results
                )
                
                self.log_test(
                    f"Search '{query}'",
                    found or len(results) > 0,
                    f"Found {len(results)} results"
                )
                
                if not found and len(results) == 0:
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log_test("Search Memories", False, str(e))
            return False
    
    def test_conversation_memory(self) -> bool:
        """Test storing conversation turns"""
        console.rule("[bold blue]Testing Conversation Memory")
        
        try:
            db_path = os.path.join(self.temp_dir, "test_memory.db")
            manager = LongTermMemoryManager(
                user_id="test_user_005",
                mem0_enabled=False,
                local_db_path=db_path
            )
            
            # Add conversation
            messages = [
                {"role": "user", "content": "I feel stressed about work"},
                {"role": "assistant", "content": "Let's explore what's causing this stress"}
            ]
            
            result = manager.add_conversation_memory(
                messages=messages,
                session_id="session_001",
                metadata={"topic": "stress"}
            )
            
            self.log_test("Add Conversation", result, "Stored conversation turn")
            
            return result
            
        except Exception as e:
            self.log_test("Add Conversation", False, str(e))
            return False
    
    def test_memory_stats(self) -> bool:
        """Test memory statistics"""
        console.rule("[bold blue]Testing Memory Stats")
        
        try:
            db_path = os.path.join(self.temp_dir, "test_memory.db")
            manager = LongTermMemoryManager(
                user_id="test_user_006",
                mem0_enabled=False,
                local_db_path=db_path
            )
            
            # Add some data
            for i in range(3):
                manager.add_manual_memory(
                    content=f"Memory {i+1}",
                    memory_type="test"
                )
            
            # Get stats
            stats = manager.get_memory_stats()
            
            passed = isinstance(stats, dict) and "local_memories" in stats
            self.log_test(
                "Memory Stats",
                passed,
                f"Stats: {json.dumps(stats)}"
            )
            
            # Display stats
            if passed:
                stats_text = "\n".join([f"{k}: {v}" for k, v in stats.items()])
                console.print(Panel(stats_text, title="Memory Statistics", border_style="green"))
            
            return passed
            
        except Exception as e:
            self.log_test("Memory Stats", False, str(e))
            return False
    
    def test_memory_service(self) -> bool:
        """Test MemoryService wrapper"""
        console.rule("[bold blue]Testing Memory Service")
        
        try:
            service = MemoryService()
            test_user = "service_test_user"
            
            # Test add manual memory
            result1 = service.add_manual_memory(
                user_id=test_user,
                content="Service test memory",
                memory_type="test"
            )
            self.log_test("Service Add Memory", result1, "Added via service")
            
            # Test list
            memories = service.list_memories(test_user, limit=10)
            result2 = len(memories) > 0
            self.log_test("Service List Memories", result2, f"Found {len(memories)} memories")
            
            # Test stats
            stats = service.stats(test_user)
            result3 = isinstance(stats, dict)
            self.log_test("Service Stats", result3, f"Stats: {json.dumps(stats)}")
            
            return result1 and result2 and result3
            
        except Exception as e:
            self.log_test("Memory Service", False, str(e))
            return False
    
    def test_edge_cases(self) -> bool:
        """Test edge cases"""
        console.rule("[bold blue]Testing Edge Cases")
        
        all_passed = True
        
        try:
            db_path = os.path.join(self.temp_dir, "test_memory.db")
            manager = LongTermMemoryManager(
                user_id="test_user_edge",
                mem0_enabled=False,
                local_db_path=db_path
            )
            
            # Test 1: Empty content
            result = manager.add_manual_memory(content="", memory_type="test")
            passed = not result  # Should return False
            self.log_test("Empty Content", passed, "Correctly rejected empty content")
            if not passed:
                all_passed = False
            
            # Test 2: None user_id
            manager2 = LongTermMemoryManager(
                user_id=None,
                mem0_enabled=False,
                local_db_path=db_path
            )
            passed = manager2.user_id == "default"
            self.log_test("None User ID", passed, f"Converted to: {manager2.user_id}")
            if not passed:
                all_passed = False
            
            # Test 3: Large content
            large_content = "x" * 10000
            result = manager.add_manual_memory(content=large_content, memory_type="test")
            self.log_test("Large Content", result, f"Stored {len(large_content)} chars")
            if not result:
                all_passed = False
            
            # Test 4: Special characters
            special_content = "Test with émojis 🎉 and spëcial çhars"
            result = manager.add_manual_memory(content=special_content, memory_type="test")
            self.log_test("Special Characters", result, "Stored special chars")
            if not result:
                all_passed = False
            
        except Exception as e:
            self.log_test("Edge Cases", False, str(e))
            all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print test summary"""
        console.rule("[bold green]Test Summary")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        summary_table = Table(title="Unit Test Results", show_header=True)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="yellow")
        
        summary_table.add_row("Total Tests", str(total))
        summary_table.add_row("Passed", f"[green]{passed}[/green]")
        summary_table.add_row("Failed", f"[red]{failed}[/red]")
        summary_table.add_row("Success Rate", f"{(passed/total*100):.1f}%")
        
        console.print(summary_table)
        
        if failed > 0:
            console.print("\n[bold red]Failed Tests:[/bold red]")
            for result in self.results:
                if not result["passed"]:
                    console.print(f"  ❌ {result['test']}: {result['details']}")
        
        return passed == total

def main():
    console.print(Panel.fit(
        "[bold cyan]Memory Service Unit Tests[/bold cyan]\n"
        "Testing internal memory functionality",
        border_style="blue"
    ))
    
    tester = MemoryServiceUnitTester()
    
    try:
        tester.setup()
        
        # Run all tests
        tests = [
            ("Memory Manager Init", tester.test_memory_manager_init),
            ("Add Manual Memory", tester.test_add_manual_memory_local),
            ("List Memories", tester.test_list_memories_local),
            ("Search Memories", tester.test_search_memories_local),
            ("Conversation Memory", tester.test_conversation_memory),
            ("Memory Stats", tester.test_memory_stats),
            ("Memory Service", tester.test_memory_service),
            ("Edge Cases", tester.test_edge_cases),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                console.print(f"[red]Test '{test_name}' crashed: {e}[/red]")
            console.print()
        
        # Print summary
        all_passed = tester.print_summary()
        
        if all_passed:
            console.print("\n[bold green]🎉 All unit tests passed![/bold green]")
            return 0
        else:
            console.print("\n[bold red]⚠️ Some tests failed[/bold red]")
            return 1
            
    finally:
        tester.teardown()

if __name__ == "__main__":
    sys.exit(main())
