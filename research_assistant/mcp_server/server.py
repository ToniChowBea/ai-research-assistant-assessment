from fastmcp import FastMCP
from research_assistant.mcp_server import tools

mcp = FastMCP(
    name="research-assistant-mcp",
    instructions=(
        "Tools for discovering research projects and datasets on a research "
        "platform, and for running governed analytical queries against synthetic "
        "research data. Discover first, then inspect, then query."
    ),
)

# ----- Discovery Tools -----------
mcp.tool(tools.list_projects)
mcp.tool(tools.get_project)
mcp.tool(tools.search_projects)
mcp.tool(tools.search_datasets)
mcp.tool(tools.list_datasets)
mcp.tool(tools.get_dataset_metadata)
mcp.tool(tools.list_researchers)
mcp.tool(tools.describe_schema)
mcp.tool(tools.sample_rows)
mcp.tool(tools.list_distinct_values)

# ----- Analysis Tools -----------
mcp.tool(tools.run_analysis)

if __name__ == "__main__":
    # DNS-rebinding protection allowlists localhost by default; add the Docker
    # service name so the api container can reach us over the compose network.
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8001,
        allowed_hosts=["mcp-server", "mcp-server:8001"],
    )
