import streamlit as st
import requests
import io
import json
from datetime import datetime

def fetch_results(results_url, headers=None):
    """Fetch the list of processing results from the API."""
    try:
        response = requests.get(results_url, headers=headers or {}, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch results: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}

def fetch_specific_result(results_url, filename, headers=None):
    """Fetch a specific result file from the API."""
    try:
        url = f"{results_url}/{filename}"
        response = requests.get(url, headers=headers or {}, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch result: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}

def main():
    st.set_page_config(
        page_title="Invoice Processor",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Invoice Processor")
    st.markdown("Upload your invoice files to process them automatically.")
    
    # Configuration section
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_base_url = st.text_input(
            "API Base URL", 
            value="http://localhost:8000",
            help="Enter the base URL of the processing API"
        )
        api_url = f"{api_base_url.rstrip('/')}/process"
        results_url = f"{api_base_url.rstrip('/')}/results"
        
        # Optional headers for authentication
        use_auth = st.checkbox("Use API Key Authentication")
        api_key = ""
        if use_auth:
            api_key = st.text_input(
                "API Key", 
                type="password",
                help="Enter your API key for authentication"
            )
    
    # Main upload section
    st.header("📤 Upload Invoice")
    
    uploaded_file = st.file_uploader(
        "Choose an invoice file",
        type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'doc', 'docx'],
        help="Supported formats: PDF, PNG, JPG, JPEG, TIFF, DOC, DOCX"
    )
    
    if uploaded_file is not None:
        # Display file details
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
        with col3:
            st.metric("File Type", uploaded_file.type)
        
        # Process button
        if st.button("🚀 Process Invoice", type="primary"):
            if not api_url:
                st.error("Please enter a valid API URL in the sidebar.")
                return
            
            with st.spinner("Processing your invoice..."):
                try:
                    # Prepare the file for upload
                    files = {
                        'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    
                    # Prepare headers
                    headers = {}
                    if use_auth and api_key:
                        headers['Authorization'] = f'Bearer {api_key}'
                    
                    # Send HTTP request
                    response = requests.post(
                        api_url,
                        files=files,
                        headers=headers,
                        timeout=30
                    )
                    
                    # Handle response
                    if response.status_code == 200 or response.status_code == 202:
                        st.success("✅ Invoice processed successfully!")
                        
                        # Display response if it's JSON
                        try:
                            result = response.json()
                            st.subheader("📊 Processing Results")
                            st.json(result)
                        except:
                            # If not JSON, display as text
                            if response.text:
                                st.subheader("📄 Response")
                                st.text(response.text)
                    
                    elif response.status_code == 400:
                        st.error(f"❌ Bad Request: {response.text}")
                    elif response.status_code == 401:
                        st.error("❌ Unauthorized: Please check your API key.")
                    elif response.status_code == 500:
                        st.error("❌ Server Error: The processing service encountered an error.")
                    else:
                        st.error(f"❌ Error {response.status_code}: {response.text}")
                
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. Please try again.")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to the processing service. Please check the URL.")
                except Exception as e:
                    st.error(f"❌ An unexpected error occurred: {str(e)}")
    
    # Results section
    st.header("📊 Processing Results")
    st.markdown("View and manage your processed invoice results.")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🔄 Refresh Results", help="Fetch the latest processing results"):
            with st.spinner("Fetching results..."):
                # Prepare headers
                headers = {}
                if use_auth and api_key:
                    headers['Authorization'] = f'Bearer {api_key}'
                
                results_data = fetch_results(results_url, headers)
                
                if "error" in results_data:
                    st.error(f"❌ {results_data['error']}")
                else:
                    st.session_state['results_data'] = results_data
                    st.success("✅ Results refreshed!")
    
    with col2:
        if st.button("📈 Auto-refresh", help="Toggle automatic refresh every 30 seconds"):
            st.session_state['auto_refresh'] = not st.session_state.get('auto_refresh', False)
            if st.session_state['auto_refresh']:
                st.success("Auto-refresh enabled")
            else:
                st.info("Auto-refresh disabled")
    
    with col3:
        st.write(f"Auto-refresh: {'🟢 ON' if st.session_state.get('auto_refresh', False) else '🔴 OFF'}")
    
    # Display results if available
    if 'results_data' in st.session_state:
        results_data = st.session_state['results_data']
        
        if results_data.get('total_results', 0) > 0:
            st.subheader(f"📄 Found {results_data['total_results']} processed files")
            
            # Create a table of results
            results_list = results_data.get('results', [])
            
            for i, result in enumerate(results_list):
                with st.expander(f"📄 {result.get('original_document', 'Unknown')} - {result.get('status', 'Unknown').title()}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**File Info:**")
                        st.write(f"• Original: {result.get('original_document', 'N/A')}")
                        st.write(f"• Type: {result.get('document_type', 'N/A')}")
                        st.write(f"• Status: {result.get('status', 'N/A')}")
                    
                    with col2:
                        st.write("**Processing:**")
                        timestamp = result.get('processed_timestamp', '')
                        if timestamp:
                            try:
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                st.write(f"• Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                            except:
                                st.write(f"• Time: {timestamp}")
                        st.write(f"• Result File: {result.get('filename', 'N/A')}")
                    
                    with col3:
                        st.write("**Actions:**")
                        if st.button(f"👁️ View Details", key=f"view_{i}"):
                            # Fetch and display the full result
                            with st.spinner("Loading result details..."):
                                headers = {}
                                if use_auth and api_key:
                                    headers['Authorization'] = f'Bearer {api_key}'
                                
                                full_result = fetch_specific_result(results_url, result['filename'], headers)
                                
                                if "error" in full_result:
                                    st.error(f"❌ {full_result['error']}")
                                else:
                                    st.session_state[f'full_result_{i}'] = full_result
                        
                        # Show download button for result file
                        if st.button(f"💾 Download JSON", key=f"download_{i}"):
                            headers = {}
                            if use_auth and api_key:
                                headers['Authorization'] = f'Bearer {api_key}'
                            
                            full_result = fetch_specific_result(results_url, result['filename'], headers)
                            if "error" not in full_result:
                                json_str = json.dumps(full_result, indent=2)
                                st.download_button(
                                    label="📥 Download",
                                    data=json_str,
                                    file_name=result['filename'],
                                    mime="application/json",
                                    key=f"download_btn_{i}"
                                )
                    
                    # Display full result details if loaded
                    if f'full_result_{i}' in st.session_state:
                        st.subheader("📋 Full Result Details")
                        full_result = st.session_state[f'full_result_{i}']
                        
                        # Extracted data
                        if 'extracted_data' in full_result:
                            st.write("**🎯 Extracted Data:**")
                            st.json(full_result['extracted_data'])
                        
                        # Metadata
                        if 'metadata' in full_result:
                            st.write("**📊 Metadata:**")
                            st.json(full_result['metadata'])
                        
                        # Raw OCR text (collapsible)
                        if 'raw_ocr_text' in full_result and full_result['raw_ocr_text']:
                            with st.expander("📝 Raw OCR Text", expanded=False):
                                st.text_area("OCR Output", full_result['raw_ocr_text'], height=200, disabled=True)
        else:
            st.info("📭 No processing results found. Upload and process some invoices first!")
    else:
        st.info("🔄 Click 'Refresh Results' to load processed files.")
    
    # Auto-refresh functionality
    if st.session_state.get('auto_refresh', False):
        import time
        time.sleep(30)
        st.rerun()
    
    # Instructions section
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        ## 📤 Processing Invoices
        1. **Configure the API URL** in the sidebar - this is where your invoice will be sent for processing
        2. **Add API Key** (optional) if your processing service requires authentication
        3. **Upload an invoice file** using the file uploader above
        4. **Click "Process Invoice"** to send the file to your processing service
        5. **View immediate confirmation** that your file is being processed
        
        ## 📊 Viewing Results
        1. **Click "Refresh Results"** to fetch the latest processed files
        2. **Enable Auto-refresh** for automatic updates every 30 seconds
        3. **Expand any result** to see processing details
        4. **Click "View Details"** to see the full extracted data
        5. **Download JSON files** of the extracted data for further use
        
        **Supported file formats:** PDF (recommended), PNG, JPG, JPEG, TIFF, DOC, DOCX
        
        **Note:** Processing happens in the background, so you can upload multiple files and check results later!
        """)

if __name__ == "__main__":
    main()
