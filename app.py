import streamlit as st
import os
import glob
from PIL import Image
from collections import Counter
import json

# --- Page Configuration ---
# Use the wide layout for more space
st.set_page_config(
    page_title="Inference Results Viewer",
    layout="wide"
)

# --- Constants ---
SAVED_PATHS_FILE = "saved_paths.json"

# --- Session State Initialization ---
if 'selected_image' not in st.session_state:
    st.session_state.selected_image = None

# --- Helper Functions ---

def load_paths():
    """Loads the list of saved directory paths from the JSON file."""
    if not os.path.exists(SAVED_PATHS_FILE):
        return ["."]  # Return a default if the file doesn't exist
    try:
        with open(SAVED_PATHS_FILE, "r") as f:
            paths = json.load(f)
            return paths if paths else ["."]
    except (json.JSONDecodeError, FileNotFoundError):
        return ["."]

def save_paths(paths):
    """Saves the list of directory paths to the JSON file."""
    # Ensure no duplicates and maintain order
    unique_paths = sorted(list(set(paths)))
    with open(SAVED_PATHS_FILE, "w") as f:
        json.dump(unique_paths, f, indent=4)

def get_image_files(path):
    """Returns a sorted list of image files from a directory."""
    if not path or not os.path.isdir(path):
        return []
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
    power = 1024; n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size_bytes >= power and n < len(power_labels) - 1:
        size_bytes /= power; n += 1
    return f"{size_bytes:.2f} {power_labels[n]}"

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("📁 Directory Setup")
    
    saved_paths = load_paths()
    
    # Dropdown to select a saved directory
    image_dir = st.selectbox(
        "Select a saved directory:",
        options=saved_paths,
        format_func=lambda x: os.path.basename(x) if x != "." else "Current Directory",
        on_change=reset_gallery_view
    )
    
    st.divider()
    
    # Section to add a new directory
    st.markdown("##### Add a New Directory")
    new_path = st.text_input("Enter a new path to save:", key="new_path_input")
    
    if st.button("Save Path"):
        if new_path and os.path.isdir(new_path):
            # Add the absolute path to avoid ambiguity
            abs_path = os.path.abspath(new_path)
            if abs_path not in saved_paths:
                saved_paths.append(abs_path)
                save_paths(saved_paths)
                st.success(f"Saved: {abs_path}")
                st.rerun() # Rerun to update the dropdown
            else:
                st.info("This path is already saved.")
        else:
            st.error("The specified path is not a valid directory.")


# --- Main App ---
st.header("🖼️ Model Inference Viewer")

# Load the images from the specified directory
image_files = get_image_files(image_dir)

# More robust logic to reset view when directory changes
if st.session_state.selected_image and st.session_state.selected_image not in image_files:
    reset_gallery_view()

# Create the tabs
tab1, tab2 = st.tabs(["🖼️ Image Gallery", "📊 Analysis"])

# --- Gallery Tab ---
with tab1:
    if not image_files:
        st.warning(f"No images found in the selected directory.")
        st.info("Please select a valid directory containing images using the sidebar.")

    elif st.session_state.selected_image is not None:
        # --- FOCUSED VIEW ---
        st.markdown("### Focused View")
        try:
            current_index = image_files.index(st.session_state.selected_image)
            st.image(st.session_state.selected_image, use_container_width=True)
            col1, col2, col3, col4 = st.columns([1, 1, 5, 1])
            if col1.button("⬅️ Previous", use_container_width=True, disabled=(current_index == 0)):
                st.session_state.selected_image = image_files[current_index - 1]; st.rerun()
            if col2.button("Next ➡️", use_container_width=True, disabled=(current_index == len(image_files) - 1)):
                st.session_state.selected_image = image_files[current_index + 1]; st.rerun()
            if col4.button("Back to Gallery 🖼️", use_container_width=True, on_click=reset_gallery_view):
                st.rerun()
        except ValueError:
            st.error("The selected image could not be found."); reset_gallery_view(); st.rerun()

    else:
        # --- GRID VIEW ---
        meta_cols = st.columns(4)
        with meta_cols[0]:
            st.metric("Total Images", value=len(image_files) if image_files else 0)
        with meta_cols[1]:
            total_size_bytes = sum(os.path.getsize(f) for f in image_files) if image_files else 0
            st.metric("Total Size", value=format_bytes(total_size_bytes))
        with meta_cols[2]:
            st.markdown("**Image Dimensions**")
            if image_files:
                all_dims = [img.size for f in image_files if (img := Image.open(f)) is not None]
                if not all_dims: st.markdown("N/A")
                else:
                    dim_counts = Counter(all_dims)
                    breakdown = [f"- `{w}x{h}`: **{c}** ({(c / len(all_dims)) * 100:.1f}%)" for (w, h), c in dim_counts.most_common()]
                    with st.expander(f"{len(dim_counts)} unique sizes"):
                        st.markdown("\n".join(breakdown))
            else: st.markdown("N/A")
        with meta_cols[3]:
            cols_per_row = st.selectbox("Images per row:", options=[1, 2, 3, 4, 5, 6, 8, 10], index=3)
        st.divider()
        cols = st.columns(cols_per_row)
        for i, image_file in enumerate(image_files):
            with cols[i % cols_per_row]:
                st.image(image_file, use_container_width=True, caption=os.path.basename(image_file))
                if st.button("View", key=f"view_{image_file}"):
                    st.session_state.selected_image = image_file; st.rerun()

# --- Analysis Tab ---
with tab2:
    st.header("Analysis")
    if image_files:
        st.subheader("Image Dimensions Analysis")
        image_dims = []
        for img_path in image_files:
            try:
                with Image.open(img_path) as img: image_dims.append(img.size)
            except Exception as e:
                st.warning(f"Could not read {os.path.basename(img_path)}: {e}")
        if image_dims:
            import pandas as pd
            df = pd.DataFrame(image_dims, columns=['Width', 'Height'], index=[os.path.basename(p) for p in image_files])
            st.dataframe(df)
            st.subheader("Distribution of Image Widths")
            st.bar_chart(df['Width'])
    else: st.info("No images to analyze.")