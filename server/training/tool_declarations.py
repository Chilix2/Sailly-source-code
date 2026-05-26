"""Tool declarations for Vertex AI Prompt Optimizer."""

from typing import List, Dict, Any
import json


def get_tool_declarations() -> Dict[str, Any]:
    """
    Define all Sailly restaurant tools as FunctionDeclarations for the optimizer.
    
    Returns:
        Dictionary with 'function_declarations' containing all tool definitions
    """
    
    tools = [
        {
            "name": "get_menu",
            "description": "Retrieve the restaurant menu with available dishes, prices, and descriptions",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "check_availability",
            "description": "Check table availability for a given date, time, and party size",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "date": {"type": "STRING", "description": "Reservation date"},
                    "time": {"type": "STRING", "description": "Reservation time"},
                    "party_size": {"type": "INTEGER", "description": "Number of people"}
                },
                "required": []
            }
        },
        {
            "name": "create_reservation",
            "description": "Create a table reservation at the restaurant",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "date": {"type": "STRING"},
                    "time": {"type": "STRING"},
                    "party_size": {"type": "INTEGER"},
                    "name": {"type": "STRING"},
                    "phone": {"type": "STRING"}
                },
                "required": []
            }
        },
        {
            "name": "create_order",
            "description": "Create a food order for takeaway or delivery",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "items": {"type": "STRING", "description": "Ordered dishes"},
                    "phone": {"type": "STRING", "description": "Customer phone number"},
                    "address": {"type": "STRING", "description": "Delivery address if applicable"}
                },
                "required": []
            }
        },
        {
            "name": "send_sms",
            "description": "Send SMS confirmation to customer phone number",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "phone": {"type": "STRING", "description": "Recipient phone number"},
                    "message": {"type": "STRING", "description": "SMS message content"}
                },
                "required": []
            }
        },
        {
            "name": "verify_address",
            "description": "Verify and validate delivery address",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "address": {"type": "STRING"}
                },
                "required": []
            }
        },
        {
            "name": "technical_issues_callback",
            "description": "Register callback for technical issues or app problems",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "update_state",
            "description": "Update conversation state with customer information",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "transfer_to_human",
            "description": "Transfer conversation to a human agent",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "transfer_to_ordering",
            "description": "Transfer to the ordering system for checkout",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "transfer_to_tier2",
            "description": "Transfer to Tier 2 advanced agent",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_date_info",
            "description": "Get information about specific dates (holidays, special hours)",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "date": {"type": "STRING"}
                },
                "required": []
            }
        },
        {
            "name": "get_weather",
            "description": "Get weather information for the restaurant location",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "end_call",
            "description": "End the phone call gracefully",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "faq",
            "description": "Answer frequently asked questions about the restaurant",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "question": {"type": "STRING"}
                },
                "required": []
            }
        }
    ]
    
    return {
        "function_declarations": tools
    }


def get_tool_config() -> Dict[str, Any]:
    """
    Define tool configuration for the optimizer.
    
    Returns:
        ToolConfig dictionary
    """
    
    tool_names = [
        "get_menu", "check_availability", "create_reservation",
        "create_order", "send_sms", "technical_issues_callback",
        "verify_address", "update_state", "transfer_to_human",
        "transfer_to_ordering", "transfer_to_tier2",
        "get_date_info", "get_weather", "end_call", "faq"
    ]
    
    return {
        "function_calling_config": {
            "mode": "ANY",
            "allowed_function_names": tool_names
        }
    }


def validate_and_export(output_path: str = "/tmp/optimizer_tools.json") -> str:
    """
    Validate tool definitions and export as JSON for the optimizer.
    
    Args:
        output_path: Path to save tool definitions JSON
        
    Returns:
        Path to exported JSON
    """
    
    declarations = get_tool_declarations()
    config = get_tool_config()
    
    combined = {
        "tools": declarations,
        "toolConfig": config
    }
    
    with open(output_path, "w") as f:
        json.dump(combined, f, indent=2)
    
    print(f"✅ Tool definitions exported: {output_path}")
    print(f"   Total tools: {len(declarations['function_declarations'])}")
    
    return output_path


if __name__ == "__main__":
    validate_and_export()
