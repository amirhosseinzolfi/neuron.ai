#!/usr/bin/env python3
"""
Comprehensive Memory Functionality Test Suite
Tests all memory operations: add, search, extract, list, stats
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

# API Configuration
API_BASE_URL = os.getenv("MEMORY_API_BASE_URL", "http://localhost:15800")
TEST_USER_ID = f"test_user_{int(time.time())}"

class MemoryTester:
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.results = []
        
    def log_test(self, name: str, passed: bool, details: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({"test": name, "passed": passed, "details": details})
        console.log(f"{status} - {name}")
        if details:
            console.log(f"  Details: {details}")
    
    def test_health(self) -> bool:
        """Test API health endpoint"""
        console.rule("[bold blue]Testing API Health")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            passed = response.status_code == 200
            self.log_test("API Health Check", passed, f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("API Health Check", False, str(e))
            return False
    
    def test_add_manual_memory(self) -> bool:
        """Test adding manual memory/note"""
        console.rule("[bold blue]Testing Add Manual Memory")
        
        test_cases = [
            {
                "content": "User loves hiking and outdoor activities",
                "memory_type": "hobby",
                "metadata": {"category": "interests"}
            },
            {
                "content": "User is an introvert who prefers quiet environments",
                "memory_type": "personality",
                "metadata": {"trait": "introversion"}
            },
            {
                "content": "User works as a software engineer",
                "memory_type": "professional",
                "metadata": {"occupation": "tech"}
            }
        ]
        
        all_passed = True
        for i, test_case in enumerate(test_cases, 1):
            try:
                response = requests.post(
                    f"{self.base_url}/memory/{self.user_id}/notes",
                    json=test_case,
                    timeout=10
                )
                
                passed = response.status_code == 200 and response.json().get("success")
                self.log_test(
                    f"Add Manual Memory #{i}",
                    passed,
                    f"Content: {test_case['content'][:50]}..."
                )
                
                if passed:
                    console.print(Panel(json.dumps(response.json(), indent=2), title="Response"))
                else:
                    console.print(f"[red]Failed: {response.text}[/red]")
                    all_passed = False
                    
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                self.log_test(f"Add Manual Memory #{i}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_store_conversation(self) -> bool:
        """Test storing conversation turns"""
        console.rule("[bold blue]Testing Store Conversation")
        
        conversations = [
            {
                "user_text": "I feel anxious about my upcoming presentation",
                "assistant_text": "It's natural to feel anxious. Let's work on some coping strategies.",
                "metadata": {"topic": "anxiety", "session": "1"}
            },
            {
                "user_text": "I've been feeling more confident lately",
                "assistant_text": "That's wonderful progress! What do you think contributed to this change?",
                "metadata": {"topic": "confidence", "session": "2"}
            }
        ]
        
        all_passed = True
        for i, conv in enumerate(conversations, 1):
            try:
                response = requests.post(
                    f"{self.base_url}/memory/{self.user_id}/store",
                    json=conv,
                    timeout=10
                )
                
                passed = response.status_code == 200 and response.json().get("success")
                self.log_test(
                    f"Store Conversation #{i}",
                    passed,
                    f"User: {conv['user_text'][:40]}..."
                )
                
                if passed:
                    console.print(Panel(json.dumps(response.json(), indent=2), title="Response"))
                else:
                    console.print(f"[red]Failed: {response.text}[/red]")
                    all_passed = False
                    
                time.sleep(0.5)
                
            except Exception as e:
                self.log_test(f"Store Conversation #{i}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_list_memories(self) -> bool:
        """Test listing all memories"""
        console.rule("[bold blue]Testing List Memories")
        
        try:
            response = requests.get(
                f"{self.base_url}/memory/{self.user_id}",
                params={"limit": 50},
                timeout=10
            )
            
            passed = response.status_code == 200
            data = response.json()
            
            if passed:
                count = data.get("count", 0)
                memories = data.get("memories", [])
                
                self.log_test(
                    "List Memories",
                    passed,
                    f"Retrieved {count} memories"
                )
                
                # Display memories in table
                if memories:
                    table = Table(title=f"Memories for {self.user_id}", show_lines=True)
                    table.add_column("ID", style="cyan")
                    table.add_column("Memory", style="white")
                    table.add_column("Source", style="yellow")
                    
                    for mem in memories[:10]:  # Show first 10
                        mem_id = str(mem.get("id", "-"))[:20]
                        content = str(mem.get("memory", mem.get("content", "")))[:60]
                        source = mem.get("source", "unknown")
                        table.add_row(mem_id, content, source)
                    
                    console.print(table)
                else:
                    console.print("[yellow]No memories found[/yellow]")
            else:
                self.log_test("List Memories", False, response.text)
            
            return passed
            
        except Exception as e:
            self.log_test("List Memories", False, str(e))
            return False
    
    def test_search_memories(self) -> bool:
        """Test semantic search"""
        console.rule("[bold blue]Testing Search Memories")
        
        search_queries = [
            {"query": "hobbies and interests", "limit": 3},
            {"query": "personality traits", "limit": 3},
            {"query": "work and career", "limit": 3},
            {"query": "anxiety and stress", "limit": 3}
        ]
        
        all_passed = True
        for i, search in enumerate(search_queries, 1):
            try:
                response = requests.post(
                    f"{self.base_url}/memory/{self.user_id}/search",
                    json=search,
                    timeout=10
                )
                
                passed = response.status_code == 200
                data = response.json()
                
                if passed:
                    count = data.get("count", 0)
                    memories = data.get("memories", [])
                    
                    self.log_test(
                        f"Search #{i}: '{search['query']}'",
                        passed,
                        f"Found {count} results"
                    )
                    
                    # Display search results
                    if memories:
                        table = Table(title=f"Search: {search['query']}", show_lines=True)
                        table.add_column("Score", style="yellow")
                        table.add_column("Content", style="white")
                        table.add_column("Source", style="cyan")
                        
                        for mem in memories:
                            score = mem.get("score", "N/A")
                            content = str(mem.get("content", mem.get("memory", "")))[:70]
                            source = mem.get("source", "unknown")
                            table.add_row(str(score), content, source)
                        
                        console.print(table)
                    else:
                        console.print(f"[yellow]No results for '{search['query']}'[/yellow]")
                else:
                    self.log_test(f"Search #{i}", False, response.text)
                    all_passed = False
                    
                time.sleep(0.5)
                
            except Exception as e:
                self.log_test(f"Search #{i}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_memory_stats(self) -> bool:
        """Test memory statistics"""
        console.rule("[bold blue]Testing Memory Stats")
        
        try:
            response = requests.get(
                f"{self.base_url}/memory/{self.user_id}/stats",
                timeout=10
            )
            
            passed = response.status_code == 200
            data = response.json()
            
            if passed:
                stats = data.get("stats", {})
                self.log_test("Memory Stats", passed, f"Stats: {json.dumps(stats)}")
                
                # Display stats in panel
                stats_text = "\n".join([f"{k}: {v}" for k, v in stats.items()])
                console.print(Panel(stats_text, title="Memory Statistics", border_style="green"))
            else:
                self.log_test("Memory Stats", False, response.text)
            
            return passed
            
        except Exception as e:
            self.log_test("Memory Stats", False, str(e))
            return False
    
    def test_edge_cases(self) -> bool:
        """Test edge cases and error handling"""
        console.rule("[bold blue]Testing Edge Cases")
        
        all_passed = True
        
        # Test 1: Empty content
        try:
            response = requests.post(
                f"{self.base_url}/memory/{self.user_id}/notes",
                json={"content": "", "memory_type": "test"},
                timeout=5
            )
            # Should fail validation
            passed = response.status_code == 422
            self.log_test("Empty Content Validation", passed, f"Status: {response.status_code}")
            if not passed:
                all_passed = False
        except Exception as e:
            self.log_test("Empty Content Validation", False, str(e))
            all_passed = False
        
        # Test 2: Invalid user ID
        try:
            response = requests.get(
                f"{self.base_url}/memory//stats",
                timeout=5
            )
            passed = response.status_code in [404, 422]
            self.log_test("Invalid User ID", passed, f"Status: {response.status_code}")
            if not passed:
                all_passed = False
        except Exception as e:
            self.log_test("Invalid User ID", False, str(e))
            all_passed = False
        
        # Test 3: Search with empty query
        try:
            response = requests.post(
                f"{self.base_url}/memory/{self.user_id}/search",
                json={"query": "", "limit": 3},
                timeout=5
            )
            # Should fail validation
            passed = response.status_code == 422
            self.log_test("Empty Search Query", passed, f"Status: {response.status_code}")
            if not passed:
                all_passed = False
        except Exception as e:
            self.log_test("Empty Search Query", False, str(e))
            all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print test summary"""
        console.rule("[bold green]Test Summary")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        summary_table = Table(title="Test Results Summary", show_header=True)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="yellow")
        
        summary_table.add_row("Total Tests", str(total))
        summary_table.add_row("Passed", f"[green]{passed}[/green]")
        summary_table.add_row("Failed", f"[red]{failed}[/red]")
        summary_table.add_row("Success Rate", f"{(passed/total*100):.1f}%")
        
        console.print(summary_table)
        
        # Show failed tests
        if failed > 0:
            console.print("\n[bold red]Failed Tests:[/bold red]")
            for result in self.results:
                if not result["passed"]:
                    console.print(f"  ❌ {result['test']}: {result['details']}")
        
        return passed == total

def main():
    console.print(Panel.fit(
        f"[bold cyan]Memory Functionality Comprehensive Test[/bold cyan]\n"
        f"API: {API_BASE_URL}\n"
        f"User ID: {TEST_USER_ID}",
        border_style="blue"
    ))
    
    tester = MemoryTester(API_BASE_URL, TEST_USER_ID)
    
    # Run all tests
    tests = [
        ("Health Check", tester.test_health),
        ("Add Manual Memory", tester.test_add_manual_memory),
        ("Store Conversation", tester.test_store_conversation),
        ("List Memories", tester.test_list_memories),
        ("Search Memories", tester.test_search_memories),
        ("Memory Stats", tester.test_memory_stats),
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
        console.print("\n[bold green]🎉 All tests passed![/bold green]")
        return 0
    else:
        console.print("\n[bold red]⚠️ Some tests failed[/bold red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
