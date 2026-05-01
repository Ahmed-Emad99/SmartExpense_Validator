from typing import  Dict, Any
from models.invoice_model import InvoiceData
from policy_check.retriever import retrieve_relevant_chunks 
from policy_check.Azure_OpenAI_Client import AzureClient    

# Create an instance of AzureClient
azure_client = AzureClient()


def build_policy_query(invoice: InvoiceData) -> str:
    """
    transform invoice values into a question query.
    """
    vendor = invoice.vendor_name or "unknown vendor"
    items = ", ".join(invoice.purchased_items) if invoice.purchased_items else "various items"
    amount = f"{invoice.total_price} {invoice.currency}" if invoice.total_price else "unspecified amount"
    tax_number = invoice.tax_number
    date = invoice.date

    messages = [
        {
            "role": "system",
            "content": """You are a compliance analysis engine that converts invoice data into precise, 
    multi-faceted search queries for retrieving travel and expense policy rules.

    Your queries must:
    - Cover EVERY compliance dimension present in the invoice (amount thresholds, vendor type, item categories, tax validity, timing)
    - Use policy-specific terminology (e.g., "per diem", "reimbursable", "approval limit", "receipt requirement")
    - Be structured to maximize retrieval of ALL potentially relevant policy clauses
    - Flag any combination of fields that could trigger multiple policy rules simultaneously"""
        },
        {
            "role": "user",
            "content": f"""Generate a comprehensive search query to retrieve ALL relevant travel and expense policy rules for this invoice.

    --- INVOICE DATA ---
    Vendor:        {vendor}
    Line Items:    {items}
    Total Amount:  {amount}
    Tax Number:    {tax_number}
    Invoice Date:  {date}
    --------------------

    Coverage requirements — your query MUST address every applicable dimension:
    1. AMOUNT    → approval thresholds, spending caps, per-item limits
    2. VENDOR    → vendor category (hotel/airline/restaurant/other), registration status, contract requirements
    3. ITEMS     → item-level eligibility, reimbursability, category-specific rules
    4. TAX       → VAT/tax number validity, tax reclaim eligibility, documentation requirements
    5. DATE      → submission deadlines, advance booking rules, blackout periods, fiscal period compliance
    6. PAYMENT   → allowed payment methods for this expense type and amount
    7. APPROVAL  → required approver level given the total amount

    Return ONLY the search query — no explanation, no preamble, no bullet points.
    The query should be a single richly-worded string that maximizes policy document retrieval coverage."""
        }
        
    ]
    
    try:
        response = azure_client.call_llm(message=messages, temp=0.0)
        return response
      
    except Exception as e:
        print(f"error occur while generate query for invoice {e}")

##################################################################################################

def build_validation_prompt(query, chunks):
    prompt = [
    {
        "role": "system",
        "content": """You are a strict travel and expense policy compliance validator.

RULES YOU MUST FOLLOW:
1. Base your decision EXCLUSIVELY on the provided policy chunks — no external knowledge, no assumptions.
2. If the policy chunks do not explicitly cover the case, return INSUFFICIENT_INFO — never guess.
3. If multiple policy rules apply, evaluate ALL of them — a single violation makes the entire expense INVALID.
4. Quote the exact policy clause that supports your decision.
5. Never invent, interpolate, or paraphrase policy rules beyond what is written."""
    },
    {
        "role": "user",
        "content": f"""
=== POLICY CHUNKS ===
{chunks}
=====================

=== EXPENSE TO VALIDATE ===
{query}
===========================

VALIDATION TASK:
Evaluate the expense against every relevant rule found in the policy chunks above.
Check ALL of the following dimensions if covered by the policy:
- Amount vs. spending limits or approval thresholds
- Vendor eligibility and registration status
- Item/category reimbursability
- Payment method compliance
- Required documentation (receipts, tax numbers, approvals)
- Date/timing rules (submission window, advance booking, etc.)

Return your response in EXACTLY this format — no extra text before or after:

Decision: VALID | INVALID | INSUFFICIENT_INFO
Violated_Rules: <list each violated clause, or "None">
Policy_Evidence: "<exact quote from the policy chunk that supports your decision>"
Reason: <2-3 sentence explanation referencing the policy evidence above>
Action_Required: <what the submitter must do to resolve this, or "None">
"""
    }
    ]
    try:
        response = azure_client.call_llm(message=prompt, temp=0.0)
        return response 
    except Exception as e:
        print(f"error occur while generate review invoice with policy{e}")

############################################################################################

def parse_policy_response(invoice: InvoiceData, response: str) -> InvoiceData:
    """
    Parse the LLM response to determine policy validity.
    """
    answer = response
    
    # Check for decision in the response
    if "Decision: INVALID" in answer or "Decision: INVALID\n" in answer:
        invoice.is_valid = False
        # Extract reason from the response
        reason = ""
        violated_rules = ""
        action_required = ""
        
        # Parse the structured response
        for line in answer.split('\n'):
            if line.startswith("Reason:"):
                reason = line.replace("Reason:", "").strip()
            elif line.startswith("Violated_Rules:"):
                violated_rules = line.replace("Violated_Rules:", "").strip()
            elif line.startswith("Action_Required:"):
                action_required = line.replace("Action_Required:", "").strip()
        
        # Build validation message
        validation_msg = f"❌ Policy Violation"
        if violated_rules and violated_rules != "None":
            validation_msg += f"\n\n**Violated Rules:** {violated_rules}"
        if reason:
            validation_msg += f"\n\n**Reason:** {reason}"
        if action_required and action_required != "None":
            validation_msg += f"\n\n**Action Required:** {action_required}"
        
        invoice.validation_message = validation_msg
    elif "Decision: INSUFFICIENT_INFO" in answer:
        # Keep as valid but note the issue
        invoice.validation_message = f"⚠️ Policy check inconclusive: {answer[:200]}"
    # If VALID, keep as valid (no changes needed)
    
    return invoice 

#####################################################################################################

def validate_against_policy( invoice: InvoiceData) -> InvoiceData:
    print("#"*70)
    try:
        #  LLM Call 1 - Generate search query
        query = build_policy_query(invoice)
        print(f"  -> Generated query: {query}")
        print("#"*70)
        
        # Search policy document.
        chunks = retrieve_relevant_chunks(question=query, top_k=5)
        print(f"  -> Search returned {len(chunks) if chunks else 0} results")
        print("#"*70)
        for ch in chunks:
            print(ch)
            print("-"*70,"\n")
        if not chunks:
            return invoice

        # LLM Call 2 - Validate against policy
        response = build_validation_prompt(query, chunks) 
        print(f"--> review invoice with policy {response}")
        print("#"*70)
        # Parse response
        invoice = parse_policy_response(invoice, response)
        print(f"--> status of invoice {invoice.is_valid}")
        print("#"*70)

        
    except Exception as e:
        print(f"\n[ERROR] Exception in Layer 3: {e}")
        
    
    
    return invoice


############################################################################################################

