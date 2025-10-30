#!/usr/bin/env python3

"""
AgentDB Full Indexing Script

Complete end-to-end indexing workflow:
1. Scan project files with Dashboard FileIndex
2. Generate AGTAG blocks for code files
3. Ingest to Core AgentDB
4. Populate gap database with TODOs
5. Generate sync report

Usage:
    python3 scripts/agentdb_full_index.py
    python3 scripts/agentdb_full_index.py --directory src --max-files 10
"""
    python3 scripts/agentdb_full_index.py --skip-gaps


import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "dashboard"))

from dashboard.app.utils.agtag_generator import AGTAGGenerator
from dashboard.app.autonomous.gap_scanner import GapScanner


class FullIndexer:
    """Complete indexing workflow orchestrator."""

    def __init__(self, project_root: Path):
        """
        Initialize full indexer.

        Args:
            project_root: Path to project root
        """
        self.project_root = project_root
        self.agtag_gen = AGTAGGenerator()
        self.gap_scanner = GapScanner(project_root=str(project_root))

        # Paths
        self.core_agentdb_dir = project_root / ".agentdb"
        self.core_agentdb = self.core_agentdb_dir / "agent.sqlite"
        self.dashboard_db = project_root / "dashboard" / "agentdb.db"

    def scan_project_files(self, directory: Path, pattern: str = "*.py") -> List[Path]:
        """
        Scan project for files matching pattern.

        Args:
            directory: Root directory to scan
            pattern: Glob pattern (default: *.py)

        Returns:
            List of file paths
        """
        print(f"\n📂 Scanning {directory} for {pattern}")

        files = []
        for file_path in directory.rglob(pattern):
            # Skip common directories
            if any(skip in str(file_path) for skip in ['__pycache__', '.venv', 'node_modules', '.git']):
                continue

            files.append(file_path)

        print(f"   Found {len(files)} files")
        return files

    def generate_agtags_batch(self, files: List[Path]) -> Dict[str, Any]:
        """
        Generate AGTAG blocks for multiple files.

        Args:
            files: List of file paths

        Returns:
            Results summary
        """
        print(f"\n🏷️  Generating AGTAG blocks for {len(files)} files...")

        results = {
            "total": len(files),
            "succeeded": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for idx, file_path in enumerate(files, 1):
            if idx % 10 == 0:
                print(f"   Progress: {idx}/{len(files)}")

            # Check if AGTAG already exists
            try:
                content = file_path.read_text()
                if '<!--AGTAG v1 START-->' in content:
                    results["skipped"] += 1
                    continue
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{file_path}: Read error - {e}")
                continue

            # Generate AGTAG
            agtag = self.agtag_gen.generate_for_file(file_path)

            if agtag is None:
                results["failed"] += 1
                results["errors"].append(f"{file_path}: Generation failed")
                continue

            # Append to file
            if self.agtag_gen.append_agtag_to_file(file_path, agtag):
                results["succeeded"] += 1
            else:
                results["skipped"] += 1

        print(f"\n   ✅ Generated: {results['succeeded']}")
        print(f"   ⏭️  Skipped: {results['skipped']}")
        print(f"   ❌ Failed: {results['failed']}")

        return results

    def init_core_agentdb(self) -> bool:
        """
        Initialize Core AgentDB if needed.

        Returns:
            True if initialized or exists, False otherwise
        """
        if self.core_agentdb.exists():
            print(f"\n✅ Core AgentDB exists: {self.core_agentdb}")
            return True

        print(f"\n🔨 Initializing Core AgentDB at {self.core_agentdb_dir}")

        import subprocess

        try:
            result = subprocess.run(
                ["python3", "-m", "src.agentdb.core", "init"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"✅ Core AgentDB initialized")
                return True
            else:
                print(f"❌ Failed to initialize")
                print(f"STDERR: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def ingest_to_core_batch(self, files: List[Path]) -> Dict[str, Any]:
        """
        Ingest files to Core AgentDB in batch.

        Args:
            files: List of file paths

        Returns:
            Results summary
        """
        print(f"\n📥 Ingesting {len(files)} files to Core AgentDB...")

        results = {
            "total": len(files),
            "succeeded": 0,
            "failed": 0,
            "errors": []
        }

        import subprocess

        for idx, file_path in enumerate(files, 1):
            if idx % 10 == 0:
                print(f"   Progress: {idx}/{len(files)}")

            # Make path relative to project root
            try:
                rel_path = file_path.relative_to(self.project_root)
            except ValueError:
                results["failed"] += 1
                results["errors"].append(f"{file_path}: Not under project root")
                continue

            # Run: agentdb ingest --path <rel_path> < <file>
            try:
                with open(file_path, 'r') as f:
                    result = subprocess.run(
                        ["python3", "-m", "src.agentdb.core", "ingest", "--path", str(rel_path)],
                        cwd=self.project_root,
                        stdin=f,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                if result.returncode == 0:
                    results["succeeded"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{rel_path}: {result.stderr[:100]}")

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{rel_path}: {str(e)[:100]}")

        print(f"\n   ✅ Ingested: {results['succeeded']}")
        print(f"   ❌ Failed: {results['failed']}")

        return results

    def scan_gaps(self) -> Dict[str, Any]:
        """
        Scan project for gaps and populate database.

        Returns:
            Gap scan results
        """
        print(f"\n🔍 Scanning for gaps (TODOs, placeholders, missing implementations)...")

        # Run gap scanner
        results = self.gap_scanner.scan_codebase()

        print(f"\n   Found {results['total_gaps']} gaps:")
        print(f"   🔴 Critical: {results['by_severity']['critical']}")
        print(f"   🟠 High: {results['by_severity']['high']}")
        print(f"   🟡 Medium: {results['by_severity']['medium']}")
        print(f"   🟢 Low: {results['by_severity']['low']}")

        return results

    def generate_report(self, agtag_results: Dict, ingest_results: Dict, gap_results: Dict = None) -> str:
        """
        Generate comprehensive indexing report.

        Args:
            agtag_results: AGTAG generation results
            ingest_results: Ingestion results
            gap_results: Optional gap scan results

        Returns:
            Report text
        """
        report = []
        report.append("\n" + "=" * 60)
        report.append("📊 AGENTDB FULL INDEXING REPORT")
        report.append("=" * 60)

        # AGTAG Generation
        report.append("\n📝 AGTAG Generation:")
        report.append(f"   Total files: {agtag_results['total']}")
        report.append(f"   ✅ Succeeded: {agtag_results['succeeded']}")
        report.append(f"   ⏭️  Skipped: {agtag_results['skipped']}")
        report.append(f"   ❌ Failed: {agtag_results['failed']}")

        if agtag_results['errors']:
            report.append(f"\n   Errors (showing first 5):")
            for error in agtag_results['errors'][:5]:
                report.append(f"      - {error}")

        # Core AgentDB Ingestion
        report.append(f"\n📥 Core AgentDB Ingestion:")
        report.append(f"   Total files: {ingest_results['total']}")
        report.append(f"   ✅ Succeeded: {ingest_results['succeeded']}")
        report.append(f"   ❌ Failed: {ingest_results['failed']}")

        if ingest_results['errors']:
            report.append(f"\n   Errors (showing first 5):")
            for error in ingest_results['errors'][:5]:
                report.append(f"      - {error}")

        # Gap Scan
        if gap_results:
            report.append(f"\n🔍 Gap Detection:")
            report.append(f"   Total gaps: {gap_results['total_gaps']}")
            report.append(f"   🔴 Critical: {gap_results['by_severity']['critical']}")
            report.append(f"   🟠 High: {gap_results['by_severity']['high']}")
            report.append(f"   🟡 Medium: {gap_results['by_severity']['medium']}")
            report.append(f"   🟢 Low: {gap_results['by_severity']['low']}")

        # Success Metrics
        report.append(f"\n✨ Success Metrics:")
        agtag_success_rate = (agtag_results['succeeded'] / agtag_results['total'] * 100) if agtag_results['total'] > 0 else 0
        ingest_success_rate = (ingest_results['succeeded'] / ingest_results['total'] * 100) if ingest_results['total'] > 0 else 0

        report.append(f"   AGTAG Success Rate: {agtag_success_rate:.1f}%")
        report.append(f"   Ingest Success Rate: {ingest_success_rate:.1f}%")

        if agtag_success_rate >= 95 and ingest_success_rate >= 95:
            report.append(f"\n   🎉 EXCELLENT! System is fully indexed and operational.")
        elif agtag_success_rate >= 80 and ingest_success_rate >= 80:
            report.append(f"\n   ✅ GOOD! Most files indexed successfully.")
        else:
            report.append(f"\n   ⚠️  ATTENTION NEEDED: Multiple failures detected.")

        report.append("=" * 60)

        return "\n".join(report)

    def run_full_index(self, directory: Path, pattern: str = "*.py", max_files: int = None, skip_gaps: bool = False) -> Dict[str, Any]:
        """
        Run complete indexing workflow.

        Args:
            directory: Directory to scan
            pattern: File pattern
            max_files: Optional file limit
            skip_gaps: Skip gap detection

        Returns:
            Complete results dict
        """
        start_time = time.time()

        print(f"\n🚀 Starting Full AgentDB Indexing")
        print(f"   Directory: {directory}")
        print(f"   Pattern: {pattern}")
        if max_files:
            print(f"   Limit: {max_files} files")

        # Step 1: Scan files
        files = self.scan_project_files(directory, pattern)
        if max_files:
            files = files[:max_files]

        if not files:
            print(f"\n❌ No files found!")
            return {"error": "No files found"}

        # Step 2: Generate AGTAGs
        agtag_results = self.generate_agtags_batch(files)

        # Step 3: Initialize Core AgentDB
        if not self.init_core_agentdb():
            print(f"\n❌ Failed to initialize Core AgentDB")
            return {"error": "Core AgentDB init failed"}

        # Step 4: Ingest to Core
        ingest_results = self.ingest_to_core_batch(files)

        # Step 5: Scan gaps (optional)
        gap_results = None
        if not skip_gaps:
            gap_results = self.scan_gaps()

        # Generate report
        report = self.generate_report(agtag_results, ingest_results, gap_results)
        print(report)

        # Save report
        report_path = self.project_root / "INDEXING_REPORT.txt"
        report_path.write_text(report)
        print(f"\n💾 Report saved to: {report_path}")

        elapsed = time.time() - start_time
        print(f"\n⏱️  Total time: {elapsed:.1f}s")

        return {
            "agtag": agtag_results,
            "ingest": ingest_results,
            "gaps": gap_results,
            "elapsed_seconds": elapsed
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AgentDB Full Indexing - Complete end-to-end workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--directory", default="src", help="Directory to scan (default: src)")
    parser.add_argument("--pattern", default="*.py", help="File pattern (default: *.py)")
    parser.add_argument("--max-files", type=int, help="Limit number of files")
    parser.add_argument("--skip-gaps", action="store_true", help="Skip gap detection")

    args = parser.parse_args()

    # Get project root (script is in scripts/)
    project_root = PROJECT_ROOT

    # Resolve directory
    directory = project_root / args.directory
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        sys.exit(1)

    # Run full index
    indexer = FullIndexer(project_root)
    results = indexer.run_full_index(
        directory=directory,
        pattern=args.pattern,
        max_files=args.max_files,
        skip_gaps=args.skip_gaps
    )

    # Exit code based on success
    if "error" in results:
        sys.exit(1)

    agtag_success = results['agtag']['succeeded']
    agtag_total = results['agtag']['total']
    ingest_success = results['ingest']['succeeded']
    ingest_total = results['ingest']['total']

    if agtag_success / agtag_total >= 0.95 and ingest_success / ingest_total >= 0.95:
        print(f"\n✅ SUCCESS: 95%+ success rate achieved")
        sys.exit(0)
    else:
        print(f"\n⚠️  WARNING: Success rate below 95%")
        sys.exit(1)


if __name__ == '__main__':
    main()
