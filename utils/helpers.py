import streamlit as st

def display_invoice_card(invoice_id: str, display_name: str, status: str, message: str, is_valid: bool):
    """
    Renders a styled card for an invoice in the Streamlit UI.
    """
    color = "green" if is_valid else "red"
    icon = "✅" if is_valid else "❌"
    
    st.markdown(
        f"""
        <div style="padding: 15px; border-left: 5px solid {color}; border-radius: 5px; background-color: #f9f9f9; margin-bottom: 10px;">
            <h4 style="margin-top: 0; color: #333;">{icon} {display_name}</h4>
            <p style="margin: 5px 0; color: #555;"><strong>Status:</strong> <span style="color: {color};">{status}</span></p>
            <p style="margin: 0; color: #666;"><em>{message}</em></p>
        </div>
        """,
        unsafe_allow_html=True
    )
