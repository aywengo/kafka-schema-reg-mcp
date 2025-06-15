# Examples for Kafka Schema Registry MCP Server

This folder contains example scripts for testing, demonstrating, and manually validating features of the MCP server, especially around authentication, user roles, and remote server connectivity.

## Contents

- [`test-jwt-validation.py`](./test-jwt-validation.py):
  - **Purpose:** Demonstrates how to validate JWT tokens for various OAuth providers (Azure AD, Google, Keycloak, Okta) using the MCP server's logic.
  - **How to Run:**
    ```bash
    python test-jwt-validation.py [provider] [jwt_token]
    ```
    - Example:
      ```bash
      python test-jwt-validation.py azure "<your_jwt_token>"
      ```
    - Run without arguments to see usage instructions and configuration examples.

- [`test-user-roles.py`](./test-user-roles.py):
  - **Purpose:** Shows how user roles and scopes are extracted from JWT tokens for different OAuth providers, and how the MCP server interprets them for access control.
  - **How to Run:**
    ```bash
    python test-user-roles.py
    ```
    - No arguments needed. Prints out results for various role extraction scenarios.

- [`test-remote-mcp.py`](./test-remote-mcp.py):
  - **Purpose:** Tests connectivity and functionality of a remote MCP server, including OAuth authentication and tool/resource listing.
  - **How to Run:**
    ```bash
    python test-remote-mcp.py --url <MCP_SERVER_URL> [--auth-token <JWT_TOKEN>] [--verbose]
    ```
    - Example:
      ```bash
      python test-remote-mcp.py --url http://localhost:8000/mcp --auth-token "dev-token-read"
      ```

## Notes

- These scripts are intended for **manual testing, demonstration, and debugging**. They are not part of the automated regression test suite.
- You may need to install additional dependencies (see the main project `requirements.txt`).
- For more information on authentication and user roles, see the main project documentation. 