#!/usr/bin/env python3
"""
Automatic Task Generator for Worker Pool

Generates new tasks when pool runs low, focusing on:
- Code quality and testing (80% of tasks)
- Validation of claims (15% of tasks)
- Documentation (5% of tasks, only technical)

NO marketing, NO commercial deployment, ONLY bulletproof engineering.

🚨 CRITICAL: AGTAG TASK GENERATION PAUSED (2025-10-30)

Due to two corruption incidents (REVIEW-009 + SIMPLE-002), ALL tasks
involving AGTAG block generation/modification are BLOCKED until the
hybrid LLM-parser system is implemented.

Incidents:
- REVIEW-009: Invalid AGTAG syntax broke 128 Python files
- SIMPLE-002: sed commands corrupted worker_pool.py to 23 bytes

AGTAG tasks will resume when:
✅ LLM-parser system implemented (ARCHITECTURE_DECISION_AGTAG_VS_LLM_PARSER.md)
✅ Validation tools deployed (tools/validate_agtag_syntax.py)
✅ Git repository initialized (for rollback capability)
"""

import json
import os
import glob
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class AutoTaskGenerator:
    """Automatically generates worker tasks based on codebase analysis."""

    def __init__(self, project_root: str = "/home/gontrand/ActiveProjects/agentdb-mvp"):
        self.project_root = Path(project_root)
        self.queue_file = self.project_root / "WORKER_TASK_QUEUE.json"
        self.task_counter = {"TEST": 1, "CODE": 1, "VALID": 1, "PERF": 1, "REFACTOR": 1}

        # 🚨 CRITICAL: AGTAG task generation PAUSED
        # See INCIDENT_REPORT_FILE_CORRUPTION_WORKER_POOL.md
        self.blocked_keywords = [
            "agtag", "AGTAG", "<!--",  # AGTAG syntax
            "sed -i", "awk -i",         # Dangerous in-place edits
            "rm -rf",                   # Destructive operations
        ]

    def load_queue(self) -> Dict:
        """Load current task queue."""
        with open(self.queue_file, 'r') as f:
            return json.load(f)

    def save_queue(self, queue: Dict):
        """Save updated task queue."""
        queue['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        with open(self.queue_file, 'w') as f:
            json.dump(queue, f, indent=2)

    def is_task_safe(self, task: Dict) -> bool:
        """
        Validate task doesn't contain blocked/dangerous operations.

        🚨 CRITICAL SAFETY CHECK (2025-10-30)
        Blocks tasks that could cause file corruption or system damage.

        Blocked operations:
        - AGTAG generation/modification (syntax incompatibility incidents)
        - sed -i/awk -i (in-place edits that corrupted worker_pool.py)
        - rm -rf (destructive file operations)

        Returns:
            True if task is safe, False if blocked
        """
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        full_text = f"{title} {description}"

        for keyword in self.blocked_keywords:
            if keyword.lower() in full_text:
                print(f"⚠️  BLOCKED unsafe task: {task.get('title', 'unknown')}")
                print(f"   Reason: Contains blocked keyword '{keyword}'")
                print(f"   See: INCIDENT_REPORT_FILE_CORRUPTION_WORKER_POOL.md")
                return False

        return True

    def count_available_tasks(self, queue: Dict) -> int:
        """Count tasks that are available to claim."""
        return sum(1 for t in queue['tasks'] if t['status'] == 'available')

    def get_next_task_id(self, prefix: str) -> str:
        """Generate next task ID for given prefix."""
        task_id = f"{prefix}-{self.task_counter[prefix]:03d}"
        self.task_counter[prefix] += 1
        return task_id

    def analyze_codebase(self) -> Dict[str, Any]:
        """Analyze codebase to identify task opportunities."""
        analysis = {
            'python_files': [],
            'test_files': [],
            'untested_files': [],
            'complex_functions': [],
            'missing_type_hints': [],
            'long_functions': [],
            'high_complexity': []
        }

        # Find all Python files
        for py_file in self.project_root.glob('**/*.py'):
            if '.venv' in str(py_file) or '__pycache__' in str(py_file):
                continue

            rel_path = py_file.relative_to(self.project_root)
            analysis['python_files'].append(str(rel_path))

            if 'test' in py_file.name or py_file.parent.name == 'tests':
                analysis['test_files'].append(str(rel_path))

        # Find files without corresponding tests
        src_files = [f for f in analysis['python_files']
                     if 'src/agentdb' in f and f not in analysis['test_files']]

        for src_file in src_files:
            test_name = f"test_{Path(src_file).name}"
            has_test = any(test_name in str(t) for t in analysis['test_files'])
            if not has_test:
                analysis['untested_files'].append(src_file)

        return analysis

    def generate_test_tasks(self, analysis: Dict) -> List[Dict]:
        """Generate testing tasks (highest priority)."""
        tasks = []

        # Test coverage expansion for untested files
        for untested_file in analysis['untested_files'][:10]:  # Limit to 10
            task_id = self.get_next_task_id('TEST')
            tasks.append({
                "task_id": task_id,
                "title": f"Create Test Suite for {Path(untested_file).name}",
                "description": f"Create comprehensive test suite for {untested_file} with 90%+ coverage.",
                "priority": "high",
                "estimated_hours": 2.0,
                "required_capabilities": ["python", "testing"],
                "optional_capabilities": ["pytest"],
                "dependencies": [],
                "status": "available",
                "deliverables": [
                    f"Test file: tests/test_{Path(untested_file).stem}.py",
                    "90%+ code coverage for module",
                    "All functions tested",
                    "Edge cases covered",
                    "Fixtures and mocks where appropriate"
                ],
                "success_criteria": [
                    "All tests pass",
                    "Coverage >= 90%",
                    "Edge cases documented",
                    "No test warnings"
                ],
                "provenance_spec": {
                    "creation_prompt": f"AUTO-GENERATED: Test coverage for {untested_file}",
                    "design_rationale": "File lacks test coverage; need comprehensive test suite",
                    "requirements": ["test_creation", "coverage_validation"]
                },
                "auto_generated": True,
                "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
            })

        # Integration test tasks
        tasks.append({
            "task_id": self.get_next_task_id('TEST'),
            "title": "Integration Test: CLI End-to-End Workflows",
            "description": "Create integration tests covering complete CLI workflows (init → ingest → focus → zoom).",
            "priority": "critical",
            "estimated_hours": 3.0,
            "required_capabilities": ["python", "testing", "integration_testing"],
            "optional_capabilities": [],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Integration test suite (10+ workflows)",
                "Temporary database cleanup",
                "Full workflow validation",
                "Performance measurements"
            ],
            "success_criteria": [
                "All workflows pass",
                "No database corruption",
                "Performance acceptable",
                "Cleanup verified"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Integration testing for CLI workflows",
                "design_rationale": "Need end-to-end validation of complete workflows",
                "requirements": ["integration_testing", "workflow_validation"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        # Stress test task
        tasks.append({
            "task_id": self.get_next_task_id('TEST'),
            "title": "Stress Test: 10K Symbols Performance",
            "description": "Stress test system with 10,000+ symbols to validate scalability claims.",
            "priority": "high",
            "estimated_hours": 2.5,
            "required_capabilities": ["python", "testing", "performance_testing"],
            "optional_capabilities": [],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Stress test suite",
                "10K+ symbol dataset",
                "Performance benchmarks",
                "Bottleneck identification"
            ],
            "success_criteria": [
                "10K symbols ingested successfully",
                "Query performance < 500ms",
                "No memory leaks",
                "Database stable"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Stress testing for scalability validation",
                "design_rationale": "Validate system handles large-scale data without degradation",
                "requirements": ["stress_testing", "scalability_validation"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        # Edge case testing
        tasks.append({
            "task_id": self.get_next_task_id('TEST'),
            "title": "Edge Case Test Suite: Malformed Inputs",
            "description": "Test system resilience with malformed AGTAGs, corrupted databases, invalid handles.",
            "priority": "high",
            "estimated_hours": 2.0,
            "required_capabilities": ["python", "testing"],
            "optional_capabilities": [],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Edge case test suite (20+ cases)",
                "Malformed AGTAG handling",
                "Invalid handle handling",
                "Database corruption recovery",
                "Error message validation"
            ],
            "success_criteria": [
                "All edge cases handled gracefully",
                "No crashes on invalid input",
                "Error messages clear",
                "Recovery mechanisms work"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Edge case testing for robustness",
                "design_rationale": "Production systems must handle malformed inputs gracefully",
                "requirements": ["edge_case_testing", "error_handling_validation"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        return tasks

    def generate_code_quality_tasks(self) -> List[Dict]:
        """Generate code quality improvement tasks."""
        tasks = []

        # Type annotation task
        tasks.append({
            "task_id": self.get_next_task_id('CODE'),
            "title": "Add Type Annotations to Core Module",
            "description": "Add complete type annotations to src/agentdb/core.py with mypy validation.",
            "priority": "medium",
            "estimated_hours": 2.0,
            "required_capabilities": ["python", "type_annotations"],
            "optional_capabilities": ["mypy"],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Type annotations for all functions",
                "Type annotations for all classes",
                "mypy --strict passes",
                "Type stubs for external APIs"
            ],
            "success_criteria": [
                "100% function coverage",
                "mypy --strict passes",
                "No type: ignore comments",
                "Type hints accurate"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Type annotation improvement",
                "design_rationale": "Type safety prevents bugs; need complete annotation coverage",
                "requirements": ["type_annotation", "mypy_validation"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        # Error handling task
        tasks.append({
            "task_id": self.get_next_task_id('CODE'),
            "title": "Enhance Error Handling in Ingestion Pipeline",
            "description": "Add comprehensive error handling, logging, and recovery mechanisms to ingestion pipeline.",
            "priority": "high",
            "estimated_hours": 2.5,
            "required_capabilities": ["python", "error_handling"],
            "optional_capabilities": [],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Try-catch for all file operations",
                "Detailed error messages",
                "Logging at appropriate levels",
                "Graceful failure recovery",
                "Transaction rollback on errors"
            ],
            "success_criteria": [
                "No unhandled exceptions",
                "Error messages actionable",
                "Logs include context",
                "Recovery mechanisms tested"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Error handling enhancement",
                "design_rationale": "Production code needs robust error handling and recovery",
                "requirements": ["error_handling", "logging", "recovery"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        # Logging improvement
        tasks.append({
            "task_id": self.get_next_task_id('CODE'),
            "title": "Implement Structured Logging",
            "description": "Replace print statements with structured logging (JSON format) for better observability.",
            "priority": "medium",
            "estimated_hours": 1.5,
            "required_capabilities": ["python", "logging"],
            "optional_capabilities": [],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Structured logging configuration",
                "JSON log format",
                "Log levels properly set",
                "No print() statements",
                "Correlation IDs for tracking"
            ],
            "success_criteria": [
                "All print() replaced",
                "Logs parseable as JSON",
                "Log levels appropriate",
                "Performance impact minimal"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Structured logging implementation",
                "design_rationale": "Structured logs enable better monitoring and debugging",
                "requirements": ["structured_logging", "json_format"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        return tasks

    def generate_validation_tasks(self) -> List[Dict]:
        """Generate claim validation tasks."""
        tasks = []

        # Validate all architectural claims
        tasks.append({
            "task_id": self.get_next_task_id('VALID'),
            "title": "Validate ALL Architecture Claims with Real Data",
            "description": "Systematically validate every claim in architecture docs with measured data (no estimates!).",
            "priority": "critical",
            "estimated_hours": 4.0,
            "required_capabilities": ["validation", "data_analysis"],
            "optional_capabilities": ["statistical_analysis"],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Every claim validated or marked false",
                "Actual measurements vs claimed",
                "Statistical significance proven",
                "Claims updated with real data",
                "False claims removed"
            ],
            "success_criteria": [
                "100% claims validated",
                "Real data measurements",
                "No unvalidated claims remain",
                "Documentation updated"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Comprehensive claim validation",
                "design_rationale": "Bulletproof product requires proving every claim with real data",
                "requirements": ["claim_validation", "measurement", "honesty"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        # Database integrity validation
        tasks.append({
            "task_id": self.get_next_task_id('VALID'),
            "title": "Database Integrity Constraint Validation",
            "description": "Validate all foreign keys, indexes, and constraints are enforced correctly.",
            "priority": "high",
            "estimated_hours": 2.0,
            "required_capabilities": ["database_validation"],
            "optional_capabilities": ["sql"],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "All foreign keys validated",
                "All indexes verified",
                "Constraint enforcement tested",
                "Orphaned records identified",
                "Integrity violation tests"
            ],
            "success_criteria": [
                "All constraints enforced",
                "No orphaned records",
                "Indexes used correctly",
                "Violations caught"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Database integrity validation",
                "design_rationale": "Database integrity critical for data reliability",
                "requirements": ["integrity_validation", "constraint_testing"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        return tasks

    def generate_performance_tasks(self) -> List[Dict]:
        """Generate performance testing and optimization tasks."""
        tasks = []

        # Query performance profiling
        tasks.append({
            "task_id": self.get_next_task_id('PERF'),
            "title": "Profile and Optimize Top 10 Slowest Queries",
            "description": "Identify 10 slowest queries, profile them, and optimize for 2x speed improvement minimum.",
            "priority": "high",
            "estimated_hours": 3.0,
            "required_capabilities": ["performance_optimization", "sql"],
            "optional_capabilities": ["profiling"],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Top 10 slow queries identified",
                "Profiling data for each",
                "Optimization implemented",
                "Before/after benchmarks",
                "2x speed improvement proven"
            ],
            "success_criteria": [
                "10 queries optimized",
                "2x speed improvement minimum",
                "No functionality broken",
                "Benchmarks documented"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Query performance optimization",
                "design_rationale": "Fast queries = better user experience",
                "requirements": ["profiling", "optimization", "benchmarking"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        # Memory leak detection
        tasks.append({
            "task_id": self.get_next_task_id('PERF'),
            "title": "Memory Leak Detection and Prevention",
            "description": "Profile memory usage under load to detect and fix memory leaks.",
            "priority": "critical",
            "estimated_hours": 2.5,
            "required_capabilities": ["performance_testing", "profiling"],
            "optional_capabilities": [],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Memory profiling under load",
                "Leak detection report",
                "Leaks fixed",
                "Long-running stability test",
                "Memory usage monitoring"
            ],
            "success_criteria": [
                "No memory leaks detected",
                "Memory stable over 24h run",
                "Profiling data clean",
                "Monitoring in place"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Memory leak detection",
                "design_rationale": "Memory leaks cause production failures; must be eliminated",
                "requirements": ["memory_profiling", "leak_detection"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        return tasks

    def generate_refactoring_tasks(self) -> List[Dict]:
        """Generate code refactoring tasks for maintainability."""
        tasks = []

        # Complexity reduction
        tasks.append({
            "task_id": self.get_next_task_id('REFACTOR'),
            "title": "Reduce Cyclomatic Complexity in Core Module",
            "description": "Identify and refactor functions with cyclomatic complexity > 10 in core.py.",
            "priority": "medium",
            "estimated_hours": 2.0,
            "required_capabilities": ["python", "refactoring"],
            "optional_capabilities": ["complexity_analysis"],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Functions with complexity > 10 identified",
                "Refactoring plan",
                "Complexity reduced to < 10",
                "Tests still pass",
                "Functionality preserved"
            ],
            "success_criteria": [
                "All functions complexity < 10",
                "Tests pass",
                "No functionality lost",
                "Code more readable"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Complexity reduction refactoring",
                "design_rationale": "High complexity = hard to maintain; need simplification",
                "requirements": ["complexity_analysis", "refactoring"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        # Dead code elimination
        tasks.append({
            "task_id": self.get_next_task_id('REFACTOR'),
            "title": "Dead Code Elimination",
            "description": "Identify and remove unused functions, imports, and variables.",
            "priority": "low",
            "estimated_hours": 1.5,
            "required_capabilities": ["python"],
            "optional_capabilities": ["static_analysis"],
            "dependencies": [],
            "status": "available",
            "deliverables": [
                "Unused code identified (vulture/pylint)",
                "Dead code removed",
                "Tests still pass",
                "Imports cleaned",
                "Code size reduced"
            ],
            "success_criteria": [
                "No unused imports",
                "No unused functions",
                "Tests pass",
                "Code cleaner"
            ],
            "provenance_spec": {
                "creation_prompt": "AUTO-GENERATED: Dead code elimination",
                "design_rationale": "Dead code increases maintenance burden; should be removed",
                "requirements": ["static_analysis", "code_cleanup"]
            },
            "auto_generated": True,
            "generation_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        return tasks

    def generate_tasks(self, min_available: int = 20) -> int:
        """
        Generate new tasks if pool is below minimum threshold.

        Returns: Number of tasks generated
        """
        queue = self.load_queue()
        available = self.count_available_tasks(queue)

        if available >= min_available:
            print(f"Pool has {available} available tasks (>= {min_available}). No generation needed.")
            return 0

        print(f"Pool has {available} available tasks (< {min_available}). Generating tasks...")

        # Analyze codebase
        analysis = self.analyze_codebase()

        # Generate tasks by category (prioritize testing and code quality)
        new_tasks = []

        # 50% testing tasks
        new_tasks.extend(self.generate_test_tasks(analysis))

        # 25% code quality tasks
        new_tasks.extend(self.generate_code_quality_tasks())

        # 15% validation tasks
        new_tasks.extend(self.generate_validation_tasks())

        # 7% performance tasks
        new_tasks.extend(self.generate_performance_tasks())

        # 3% refactoring tasks
        new_tasks.extend(self.generate_refactoring_tasks())

        # 🚨 CRITICAL SAFETY FILTER (2025-10-30)
        # Remove tasks with blocked keywords (AGTAG, sed -i, etc.)
        # See: INCIDENT_REPORT_FILE_CORRUPTION_WORKER_POOL.md
        tasks_before_filter = len(new_tasks)
        new_tasks = [task for task in new_tasks if self.is_task_safe(task)]
        tasks_after_filter = len(new_tasks)

        if tasks_before_filter > tasks_after_filter:
            blocked_count = tasks_before_filter - tasks_after_filter
            print(f"⚠️  FILTERED OUT {blocked_count} unsafe tasks (AGTAG/destructive operations)")
            print(f"   Safe tasks remaining: {tasks_after_filter}")

        # Add to queue
        queue['tasks'].extend(new_tasks)

        # Update statistics
        queue['statistics']['total_tasks'] = len(queue['tasks'])
        queue['statistics']['available'] = sum(1 for t in queue['tasks'] if t['status'] == 'available')
        queue['statistics']['total_estimated_hours'] = sum(t['estimated_hours'] for t in queue['tasks'])

        # Save
        self.save_queue(queue)

        print(f"✅ Generated {len(new_tasks)} new tasks!")
        print(f"📊 Pool now has {queue['statistics']['available']} available tasks")

        return len(new_tasks)


def main():
    """Generate tasks if pool is low."""
    generator = AutoTaskGenerator()
    generated = generator.generate_tasks(min_available=20)

    if generated > 0:
        print(f"\n🎯 Task Distribution:")
        print(f"  50% Testing (TEST-XXX)")
        print(f"  25% Code Quality (CODE-XXX)")
        print(f"  15% Validation (VALID-XXX)")
        print(f"   7% Performance (PERF-XXX)")
        print(f"   3% Refactoring (REFACTOR-XXX)")


if __name__ == '__main__':
    main()
