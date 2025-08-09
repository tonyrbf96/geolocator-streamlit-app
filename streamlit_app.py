import streamlit as st
import pandas as pd
import requests
import os
import io
from datetime import datetime

def get_lat_long(address, api_key):
    """Get latitude and longitude for an address using Google Maps API"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    params = {'address': address, 'key': api_key}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            latitude = location['lat']
            longitude = location['lng']
            return latitude, longitude
    return None, None

def process_geocoding(df, api_key, progress_bar=None, status_text=None):
    """Process geocoding for a DataFrame"""
    df = df.copy()
    df['Latitude'] = None
    df['Longitude'] = None
    
    total_rows = len(df)
    processed_count = 0
    error_count = 0
    
    for index, row in df.iterrows():
        try:
            address = f"{row['address1']}, {row['city']}, {row['sta']}, {row['zip']}"
            latitude, longitude = get_lat_long(address, api_key)
            
            df.at[index, 'Latitude'] = latitude if latitude else ''
            df.at[index, 'Longitude'] = longitude if longitude else ''
            
            processed_count += 1
            
            if progress_bar:
                progress_bar.progress(processed_count / total_rows)
            
            if status_text:
                status_text.text(f"Processing addresses: {processed_count}/{total_rows}")
                
        except Exception as e:
            error_count += 1
            st.warning(f"Error processing row {index + 1}: {str(e)}")
    
    return df, processed_count, error_count

def check_access_secret(secret):
    """Check if the provided secret is valid"""
    # You can change this secret to whatever you want
    VALID_SECRET = os.getenv('GEOCODER_SECRET', 'default_secret_2024')
    return secret == VALID_SECRET

def main():
    st.set_page_config(page_title="Geocoding Service", page_icon="📍")
    
    st.title("📍 Address Geocoding Service")
    st.write("Upload an Excel file with addresses to get latitude and longitude coordinates.")
    
    # Authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.subheader("🔐 Access Required")
        secret = st.text_input("Enter access secret:", type="password")
        
        if st.button("Authenticate"):
            if check_access_secret(secret):
                st.session_state.authenticated = True
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Invalid secret. Access denied.")
        
        st.info("Please enter the access secret to use the geocoding service.")
        return
    
    # Main application
    st.success("✅ Authenticated successfully")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose an Excel file", 
        type=['xlsx', 'xls'],
        help="Upload an Excel file with columns: address1, city, sta, zip"
    )
    
    if uploaded_file is not None:
        try:
            # Read the uploaded file
            df = pd.read_excel(uploaded_file)
            
            # Validate required columns
            required_columns = ['address1', 'city', 'sta', 'zip']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                st.write("Your file should contain columns: address1, city, sta, zip")
                return
            
            st.success(f"File uploaded successfully! Found {len(df)} addresses to process.")
            
            # Show preview
            st.subheader("Data Preview")
            st.dataframe(df.head(10))
            
            # Process button
            if st.button("🚀 Start Geocoding", type="primary"):
                api_key = os.getenv('GOOGLE_MAPS_API_KEY')
                
                if not api_key:
                    st.error("Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY environment variable.")
                    return
                
                with st.spinner("Processing addresses..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Process geocoding
                    result_df, processed, errors = process_geocoding(df, api_key, progress_bar, status_text)
                    
                    progress_bar.progress(1.0)
                    
                    # Show results
                    st.success(f"✅ Processing complete! Processed {processed} addresses with {errors} errors.")
                    
                    # Display results
                    st.subheader("Results")
                    st.dataframe(result_df)
                    
                    # Download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"geocoded_addresses_{timestamp}.xlsx"
                    
                    # Convert to Excel bytes
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Geocoded_Addresses')
                    
                    st.download_button(
                        label="📥 Download Geocoded File",
                        data=output.getvalue(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    # Logout button
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

if __name__ == "__main__":
    main()