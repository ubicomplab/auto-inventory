import os
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Initialize the Gemini Client
# Ensure GOOGLE_API_KEY is set in your environment variables
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

class InventoryItem(BaseModel):
    """
    Represents a single line item in the lab inventory, 
    covering both hardware (components, tools) and software (licenses, SaaS).
    """
    # -- Core Identity --
    product_name: str = Field(
        description="Short name or title of the product. e.g., 'nRF5340 Audio DK' or 'ChatGPT Team Subscription'."
    )
    category: Literal['hardware', 'software', 'consumable', 'equipment'] = Field(
        description="Broad category to facilitate filtering."
    )
    subcategory: Optional[str] = Field(
        description="Specific type. e.g., 'dev board', 'sensor', 'license_key', 'cloud_credits'."
    )
    
    # -- Purchasing Details --
    vendor: Optional[str] = Field(
        description="The name of the vendor/supplier (e.g., DigiKey, Mouser, OpenAI, AWS)."
    )
    manufacturer_part_number: Optional[str] = Field(
        description="MPN for hardware. For software, use SKU or Plan ID if available."
    )
    quantity: int = Field(
        default=1, 
        description="Number of units purchased or seats in a license."
    )
    unit_price: Optional[float] = Field(
        description="Price per individual unit in USD."
    )
    total_price: Optional[float] = Field(
        description="Total cost (unit_price * quantity). Useful for validation."
    )
    
    # -- Logistics & Ownership --
    funding_source: Optional[str] = Field(
        description="The grant, gift fund, or project code used (e.g., 'Google Academic Research Awards', 'NSF-CNS-X')."
    )
    requester: Optional[str] = Field(
        description="Full name of the person requesting the item (e.g., 'Zhihan Zhang')."
    )
    pi_name: Optional[str] = Field(
        description="The PI responsible for this expenditure."
    )
    order_date: Optional[str] = Field(
        description="Date of purchase in YYYY-MM-DD format."
    )

    # -- Lifecycle --
    expiration_date: Optional[str] = Field(
        description="For software/licenses: When does this expire? YYYY-MM-DD."
    )
    billing_cycle: Optional[Literal['One-time', 'Monthly', 'Annual']] = Field(
        description="Frequency of payment for subscriptions."
    )
    location_or_owner: Optional[str] = Field(
        description="Physical location (e.g., 'Cabinet B') or Digital Owner (e.g., 'Registered to lab-admin@uw.edu')."
    )

class InventoryResponse(BaseModel):
    """Container for the list of items returned by the LLM."""
    items: List[InventoryItem]


# --- 2. The Extraction Function ---

def extract_inventory_items(
    email_body: str, 
    pdf_attachments: Optional[List[Dict[str, bytes]]] = None,
    model_name: str = "gemini-3-flash-preview"
) -> List[Dict]:
    """
    Extracts structured inventory data from order emails and attached PDFs using Gemini.

    Args:
        email_body (str): The raw text content of the order confirmation email.
        pdf_attachments (List[Dict], optional): A list of dictionaries, where each dict contains 'content' (bytes). Defaults to None.
        model_name (str): The Gemini model version to use. 
            Defaults to "gemini-3-flash-preview".

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents 
        a validated InventoryItem. Returns an empty list on error.
    """
    
    # Initialize empty list if no attachments provided to avoid mutable default arg issues
    if pdf_attachments is None:
        pdf_attachments = []

    # 1. Build the Prompt Context
    # We combine system instructions, the specific email text, and any file parts.
    contents = []

    # Define strict extraction rules to ensure consistent data entry
    system_prompt = f"""You are an Lab Manager and Procurement Specialist for an academic research lab.
Your task is to audit purchase documents (text and PDFs) and extract into a structured inventory database.

### Rules:
1. ***PI Identification**: Identify the Principal Investigator (Professor). Look for titles like "Prof.", "PI", or context implying lab leadership.
    - If the document lists a different name (e.g., a student), list them as the 'requester', not the PI.
    - If the funding source is clear, infer the PI associated with that grant if possible.
2. **Categorization**: 
    - Hardware: Physical items (PCBs, tools).
    - Software: API credits, SaaS subscriptions (e.g., ChatGPT, Overleaf).
3. **Software Specifics**: If extracting a software license, look for "Renews on", "Expiry", or "Billing Cycle".
4. **Quantity**: Default to 1 if not explicitly stated.

### Input Text:
{email_body}
    """
    contents.append(system_prompt)

    # 2. Process Attachments
    for file_data in pdf_attachments:
        if file_data.get("content"):
            pdf_part = types.Part.from_bytes(
                data=file_data["content"],
                mime_type="application/pdf",
            )
            contents.append(pdf_part)

    try:
        # 3. Call the Gemini API
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": InventoryResponse.model_json_schema(),
            },
        )

        # 4. Validate and Parse
        # Convert the raw JSON string back into our Pydantic model for validation
        inventory_data = InventoryResponse.model_validate_json(response.text)
        
        # Return as a list of pure Python dictionaries for easy spreadsheet insertion
        return [item.model_dump() for item in inventory_data.items]

    except Exception as e:
        # Log the error for debugging (in a real app, use the logging module)
        print(f"Error during Gemini extraction: {e}")
        return []
