import streamlit as st
import os
import glob
from PIL import Image
from collections import Counter

# --- Page Configuration ---
# Use the wide layout for more space
st.set_page_config(
    page_title="Inference Results Viewer",
    layout="wide"
)

# --- Session State Initialization ---
# This is crucial for the interactive gallery.
if 'selected_image' not in st.session_state:
    st.session_state.selected_image = None

# --- Helper Functions ---
def get_image_files(path):
    """Returns a sorted list of image files from a directory."""
    if not path or not os.path.isdir(path):
        return []
    # Search for common image file extensions
    search_patterns = [os.path.join(path, f"*.{ext}") for ext in ["png", "jpg", "jpeg", "bmp", "gif"]]
    image_files = []
    for pattern in search_patterns:
        image_files.extend(glob.glob(pattern))
    return sorted(image_files)

def reset_gallery_view():
    """Callback function to reset the view to the main gallery."""
    st.session_state.selected_image = None

def format_bytes(size_bytes):
    """Formats bytes into a human-readable string (KB, MB, GB)."""
    if size_bytes == 0:
        return "0B"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size_bytes >= power and n < len(power_labels) - 1:
        size_bytes /= power
        n += 1
    return f"{size_bytes:.2f} {power_labels[n]}"

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("⚙️ Configuration")
    # Let the user input the root directory path to browse from
    root_dir = st.text_input(
        "Enter a root path to browse directories:",
        value=".",  # Default to the current directory
        on_change=reset_gallery_view # Also reset if the root path text is changed
    )

    image_dir = None
    try:
        # Find subdirectories in the root path
        if os.path.isdir(root_dir):
            subdirectories = [f.path for f in os.scandir(root_dir) if f.is_dir()]
            # Combine root and subdirectories for the selection
            options = [root_dir] + subdirectories
            
            # Let the user select a directory from a dropdown
            image_dir = st.selectbox(
                "Select an image directory:",
                options=options,
                format_func=lambda x: os.path.basename(x) if x != "." else "Current Directory",
                on_change=reset_gallery_view # The key fix: use a callback
            )
        else:
            st.error("The specified root path is not a valid directory.")

    except FileNotFoundError:
        st.error(f"Path not found: {root_dir}")

# --- Main App ---
st.header("🖼️ Model Inference Viewer")

# Load the images from the specified directory
image_files = get_image_files(image_dir)

# --- More robust logic to reset view when directory changes ---
# This check ensures that if the selected image is not in the new list of files, we reset to the gallery.
if st.session_state.selected_image and st.session_state.selected_image not in image_files:
    reset_gallery_view()

# Create the tabs
tab1, tab2 = st.tabs(["🖼️ Image Gallery", "📊 Analysis"])

# --- Gallery Tab ---
with tab1:
    if not image_files:
        st.warning(f"No images found in the selected directory: '{image_dir}'")
        st.info("Please select a valid directory containing images using the sidebar.")

    # If an image is selected, show the focused view
    elif st.session_state.selected_image is not None:
        
        # --- FOCUSED VIEW ---
        st.markdown("### Focused View")
        
        try:
            current_index = image_files.index(st.session_state.selected_image)
            
            # Display the selected image prominently (original, full-resolution)
            st.image(st.session_state.selected_image, use_container_width=True)

            # Navigation buttons
            col1, col2, col3, col4 = st.columns([1, 1, 5, 1])
            
            with col1:
                # Previous button
                if st.button("⬅️ Previous", use_container_width=True, disabled=(current_index == 0)):
                    st.session_state.selected_image = image_files[current_index - 1]
                    st.rerun()

            with col2:
                # Next button
                if st.button("Next ➡️", use_container_width=True, disabled=(current_index == len(image_files) - 1)):
                    st.session_state.selected_image = image_files[current_index + 1]
                    st.rerun()
            
            with col4:
                # Button to go back to the grid view
                if st.button("Back to Gallery 🖼️", use_container_width=True, on_click=reset_gallery_view):
                    st.rerun()

        except ValueError:
            st.error("The selected image could not be found. It may have been moved or deleted.")
            # Automatically reset the view if the image is not in the new list
            reset_gallery_view()
            st.rerun()

    else:
        # --- GRID VIEW (Manual implementation with column control) ---
        
        # --- NEW: Controls and Metadata Row ---
        # Create a row for metrics and controls
        meta_cols = st.columns(4)
        with meta_cols[0]:
            st.metric("Total Images", value=len(image_files) if image_files else 0)

        with meta_cols[1]:
            total_size_bytes = sum(os.path.getsize(f) for f in image_files) if image_files else 0
            st.metric("Total Size", value=format_bytes(total_size_bytes))

        with meta_cols[2]:
            st.markdown("**Image Dimensions**") # The requested title
            if image_files:
                all_dimensions = []
                for f in image_files:
                    try:
                        with Image.open(f) as img:
                            all_dimensions.append(img.size)
                    except Exception:
                        pass # Ignore files that are not valid images
                
                if not all_dimensions:
                     st.markdown("N/A")
                else:
                    total_images_with_dims = len(all_dimensions)
                    dimension_counts = Counter(all_dimensions)
                    
                    breakdown_lines = []
                    # Sort by count, descending
                    for dim, count in dimension_counts.most_common():
                        w, h = dim
                        percentage = (count / total_images_with_dims) * 100
                        breakdown_lines.append(f"- `{w}x{h}`: **{count}** ({percentage:.1f}%)")
                    
                    detailed_breakdown = "\n".join(breakdown_lines)
    
                    with st.expander(f"{len(dimension_counts)} unique sizes", expanded=False):
                        st.markdown(detailed_breakdown)
            else:
                 st.markdown("N/A")


        with meta_cols[3]:
            cols_per_row = st.selectbox(
                "Images per row:",
                options=[1, 2, 3, 4, 5, 6, 8, 10],
                index=3
            )
        
        st.divider() # Added the divider

        # Create the columns for the grid
        cols = st.columns(cols_per_row)
        
        for i, image_file in enumerate(image_files):
            # Place each image in the next available column
            with cols[i % cols_per_row]:
                st.image(image_file, use_container_width=True, caption=os.path.basename(image_file))
                
                # Add a button to select the image for the focused view
                if st.button("View", key=f"view_{image_file}"):
                    st.session_state.selected_image = image_file
                    st.rerun()


# --- Analysis Tab ---
with tab2:
    st.header("Analysis")
    st.markdown("This is a placeholder for your analysis. You can add charts, metrics, and dataframes here.")

    if image_files:
        st.subheader("Image Dimensions Analysis")
        
        image_dims = []
        for img_path in image_files:
            try:
                with Image.open(img_path) as img:
                    image_dims.append(img.size)
            except Exception as e:
                st.warning(f"Could not read {os.path.basename(img_path)}: {e}")
        
        if image_dims:
            # Display dimensions in a dataframe
            import pandas as pd
            df = pd.DataFrame(image_dims, columns=['Width', 'Height'], index=[os.path.basename(p) for p in image_files])
            st.dataframe(df)

            # Simple bar chart of image widths
            st.subheader("Distribution of Image Widths")
            st.bar_chart(df['Width'])
    else:
        st.info("No images to analyze. Please select a valid directory in the sidebar.")

