#!/usr/bin/env python3
"""
Test Environment Diagnostic Tool

This script checks the test environment and identifies what needs to be fixed
to run the MCP server tests successfully.
"""

import os
import sys
import subprocess
import requests
from pathlib import Path

class TestEnvironmentDiagnostic:
    def __init__(self):
        self.issues = []
        self.recommendations = []
        self.current_dir = os.getcwd()
        
    def check_python_environment(self):
        """Check Python version and basic environment."""
        print("🔍 Checking Python Environment...")
        
        python_version = sys.version_info
        print(f"   Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            self.issues.append("Python version too old")
            self.recommendations.append("Upgrade to Python 3.8 or newer")
            return False
        
        print("   ✅ Python version OK")
        return True
    
    def check_dependencies(self):
        """Check if required dependencies are installed."""
        print("\n🔍 Checking Dependencies...")
        
        required_deps = {
            "mcp": "Message Control Protocol SDK",
            "requests": "HTTP library for Schema Registry communication",
            "dotenv": "Environment variable loading",
            "asyncio": "Asynchronous programming support"
        }
        
        all_deps_ok = True
        
        for dep_name, description in required_deps.items():
            try:
                if dep_name == "asyncio":
                    # asyncio is part of standard library in Python 3.7+
                    import asyncio
                else:
                    __import__(dep_name)
                print(f"   ✅ {dep_name}: {description}")
            except ImportError:
                print(f"   ❌ {dep_name}: {description} - NOT INSTALLED")
                self.issues.append(f"Missing dependency: {dep_name}")
                all_deps_ok = False
        
        if not all_deps_ok:
            self.recommendations.append("Install dependencies: pip install -r requirements.txt")
        
        return all_deps_ok
    
    def check_mcp_server_files(self):
        """Check if MCP server files exist and are readable."""
        print("\n🔍 Checking MCP Server Files...")
        
        server_files = [
            "kafka_schema_registry_mcp.py",
            "kafka_schema_registry_multi_mcp.py"
        ]
        
        all_files_ok = True
        
        for file_name in server_files:
            file_path = Path(file_name)
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        first_line = f.readline().strip()
                    print(f"   ✅ {file_name}: Exists and readable")
                    print(f"      First line: {first_line[:60]}...")
                except Exception as e:
                    print(f"   ⚠️  {file_name}: Exists but not readable - {e}")
                    self.issues.append(f"File not readable: {file_name}")
                    all_files_ok = False
            else:
                print(f"   ❌ {file_name}: NOT FOUND")
                self.issues.append(f"Missing file: {file_name}")
                all_files_ok = False
        
        if not all_files_ok:
            self.recommendations.append("Ensure you're in the correct project directory with MCP server files")
        
        return all_files_ok
    
    def check_schema_registry_connection(self):
        """Check if Schema Registry is running and accessible."""
        print("\n🔍 Checking Schema Registry Connection...")
        
        registry_urls = [
            "http://localhost:38081",  # New test port
            "http://localhost:8081",   # Old default port
        ]
        
        registry_found = False
        
        for url in registry_urls:
            try:
                print(f"   Testing connection to {url}...")
                response = requests.get(f"{url}/subjects", timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ Schema Registry running at {url}")
                    print(f"      Response time: {response.elapsed.total_seconds():.3f}s")
                    registry_found = True
                    break
                else:
                    print(f"   ⚠️  {url}: HTTP {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"   ❌ {url}: Connection refused")
            except requests.exceptions.Timeout:
                print(f"   ❌ {url}: Connection timeout")
            except Exception as e:
                print(f"   ❌ {url}: {e}")
        
        if not registry_found:
            self.issues.append("No accessible Schema Registry found")
            self.recommendations.extend([
                "Start Schema Registry with: cd tests && ./start_test_environment.sh",
                "Or start multi-registry environment: cd tests && ./start_multi_registry_environment.sh",
                "Or start with Docker: docker-compose up -d"
            ])
        
        return registry_found
    
    def check_test_infrastructure(self):
        """Check if test infrastructure files exist."""
        print("\n🔍 Checking Test Infrastructure...")
        
        test_files = [
            "tests/test_mcp_server.py",
            "tests/test_simple_config.py",
            "tests/run_comprehensive_tests.sh"
        ]
        
        all_test_files_ok = True
        
        for file_name in test_files:
            file_path = Path(file_name)
            if file_path.exists():
                print(f"   ✅ {file_name}: Available")
            else:
                print(f"   ❌ {file_name}: NOT FOUND")
                self.issues.append(f"Missing test file: {file_name}")
                all_test_files_ok = False
        
        return all_test_files_ok
    
    def check_docker_environment(self):
        """Check if Docker is available for containerized testing."""
        print("\n🔍 Checking Docker Environment...")
        
        try:
            # Try to run docker --version
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"   ✅ Docker available: {result.stdout.strip()}")
                
                # Check if Docker daemon is running
                try:
                    result = subprocess.run(['docker', 'ps'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print("   ✅ Docker daemon is running")
                        return True
                    else:
                        print("   ⚠️  Docker installed but daemon not running")
                        self.recommendations.append("Start Docker Desktop or Docker daemon")
                        return False
                except subprocess.TimeoutExpired:
                    print("   ⚠️  Docker command timed out")
                    return False
            else:
                print(f"   ❌ Docker not working: {result.stderr}")
                return False
        except FileNotFoundError:
            print("   ❌ Docker not installed")
            self.recommendations.append("Install Docker Desktop for containerized testing")
            return False
        except subprocess.TimeoutExpired:
            print("   ❌ Docker command timed out")
            return False
        except Exception as e:
            print(f"   ❌ Docker check failed: {e}")
            return False
    
    def run_diagnosis(self):
        """Run complete diagnosis of test environment."""
        print("=" * 60)
        print("🚀 MCP Server Test Environment Diagnostic")
        print("=" * 60)
        print(f"Current directory: {self.current_dir}")
        
        # Run all checks
        python_ok = self.check_python_environment()
        deps_ok = self.check_dependencies()
        files_ok = self.check_mcp_server_files()
        registry_ok = self.check_schema_registry_connection()
        tests_ok = self.check_test_infrastructure()
        docker_ok = self.check_docker_environment()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 DIAGNOSTIC SUMMARY")
        print("=" * 60)
        
        checks = [
            ("Python Environment", python_ok),
            ("Dependencies", deps_ok),
            ("MCP Server Files", files_ok),
            ("Schema Registry", registry_ok),
            ("Test Infrastructure", tests_ok),
            ("Docker Environment", docker_ok)
        ]
        
        for check_name, is_ok in checks:
            status = "✅ OK" if is_ok else "❌ ISSUE"
            print(f"{check_name:<20} {status}")
        
        # Issues and recommendations
        if self.issues:
            print(f"\n🚨 ISSUES FOUND ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
        
        if self.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(self.recommendations)}):")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Next steps
        print(f"\n🎯 NEXT STEPS:")
        if not any([python_ok, deps_ok, files_ok]):
            print("   1. Fix Python environment and dependencies first")
            print("   2. Ensure you're in the correct project directory")
        elif not registry_ok:
            print("   1. Start Schema Registry using one of the recommended methods")
            print("   2. Then run tests with: cd tests && ./run_comprehensive_tests.sh --basic")
        elif all([python_ok, deps_ok, files_ok, registry_ok]):
            print("   ✅ Environment looks good! You can run tests:")
            print("      cd tests && python test_mcp_server.py")
            print("      cd tests && ./run_comprehensive_tests.sh --basic")
        else:
            print("   1. Fix the issues listed above")
            print("   2. Re-run this diagnostic: python tests/diagnose_test_environment.py")
        
        print("\n" + "=" * 60)
        
        # Return overall status
        return all([python_ok, deps_ok, files_ok, registry_ok, tests_ok])

def main():
    diagnostic = TestEnvironmentDiagnostic()
    success = diagnostic.run_diagnosis()
    
    if success:
        print("🎉 Test environment is ready!")
        return 0
    else:
        print("⚠️  Test environment needs attention")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 