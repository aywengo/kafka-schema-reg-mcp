#!/usr/bin/env python3
"""
Simple CLI client to interact with the MCP-LLama Bridge Service
This demonstrates how to use the integrated LLama + Kafka Schema Registry MCP system
"""

import asyncio
import json
import sys
from typing import Optional
import httpx
import argparse

class MCPLlamaClient:
    def __init__(self, bridge_url: str = "http://localhost:8080"):
        self.bridge_url = bridge_url
        
    async def health_check(self) -> dict:
        """Check if the bridge service is healthy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.bridge_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def chat(self, message: str, model: str = "llama3.2:3b", use_mcp: bool = True) -> dict:
        """Send a chat message to LLama with optional MCP integration"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.bridge_url}/chat",
                json={
                    "message": message,
                    "model": model,
                    "use_mcp": use_mcp
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def interactive_chat(self, model: str = "llama3.2:3b"):
        """Start an interactive chat session"""
        print(f"🤖 Starting interactive chat with {model}")
        print("💡 Type 'help' for Schema Registry commands, 'quit' to exit")
        print("🔧 MCP tools are enabled - you can ask about schemas, subjects, etc.")
        print("-" * 60)
        
        while True:
            try:
                user_input = input("\n🧑 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                    
                if user_input.lower() == 'help':
                    self.show_help()
                    continue
                    
                if not user_input:
                    continue
                
                print("🤖 LLama: Thinking...", end="", flush=True)
                
                response = await self.chat(user_input, model=model)
                
                print(f"\r🤖 LLama: {response['response']}")
                
                if response.get('used_tools'):
                    print(f"🔧 Used tools: {', '.join(response['used_tools'])}")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def show_help(self):
        """Show help information"""
        print("""
📚 Schema Registry Commands You Can Try:

📋 Basic Operations:
  • "List all subjects in the schema registry"
  • "Show me the schemas in the user-events subject"
  • "Get the latest version of the order-schema"
  • "Show me all contexts"

🔍 Schema Analysis:
  • "Show me the structure of the user-profile schema"
  • "Compare versions 1 and 2 of the payment-events schema" 
  • "Find all schemas that contain a field called 'user_id'"

✅ Compatibility & Validation:
  • "Check if this schema is compatible: {schema_json}"
  • "Validate this schema against AVRO standards"
  • "Show me compatibility requirements for subject X"

📊 Registry Management:
  • "Export all schemas from the production context"
  • "Show me registry statistics and usage"
  • "List all schema versions for subject Y"

🔧 Configuration:
  • "Show global compatibility settings"
  • "What's the current mode of the registry?"
  • "Update compatibility mode for subject Z"

💡 You can ask in natural language - LLama will understand and use the appropriate tools!
        """)

async def main():
    parser = argparse.ArgumentParser(description="MCP-LLama Client")
    parser.add_argument("--bridge-url", default="http://localhost:8080", 
                       help="Bridge service URL")
    parser.add_argument("--model", default="llama3.2:3b", 
                       help="LLama model to use")
    parser.add_argument("--message", help="Single message to send")
    parser.add_argument("--no-mcp", action="store_true", 
                       help="Disable MCP tools")
    parser.add_argument("--health", action="store_true", 
                       help="Check service health")
    
    args = parser.parse_args()
    
    client = MCPLlamaClient(args.bridge_url)
    
    try:
        if args.health:
            print("🏥 Checking service health...")
            health = await client.health_check()
            print(json.dumps(health, indent=2))
            return
        
        # Check if service is available
        health = await client.health_check()
        if health["status"] != "healthy":
            print(f"⚠️  Service is {health['status']}")
            if health["status"] == "unhealthy":
                print("❌ Bridge service is not available")
                sys.exit(1)
        
        if args.message:
            # Single message mode
            print(f"🤖 Sending message to {args.model}...")
            response = await client.chat(
                args.message, 
                model=args.model, 
                use_mcp=not args.no_mcp
            )
            print(f"\n🤖 Response: {response['response']}")
            if response.get('used_tools'):
                print(f"🔧 Used tools: {', '.join(response['used_tools'])}")
        else:
            # Interactive mode
            await client.interactive_chat(args.model)
            
    except httpx.ConnectError:
        print("❌ Cannot connect to bridge service. Make sure it's running at:", args.bridge_url)
        print("💡 Try running: ./run-llama-mcp.sh start")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())