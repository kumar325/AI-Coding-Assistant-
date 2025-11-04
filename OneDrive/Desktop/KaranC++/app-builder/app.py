import streamlit as st
import sys
import os
from pathlib import Path
import zipfile
from io import BytesIO
from dotenv import load_dotenv  # ← ADD THIS IMPORT

# Load environment variables from .env file FIRST
load_dotenv()  # ← ADD THIS LINE

# Add agent to path
sys.path.insert(0, os.path.dirname(__file__))

from agent.graph import agent
from agent.tools import PROJECT_ROOT, init_project_root

# Get API key from environment (loaded from .env file)
# No hardcoded key needed - it reads from .env automatically
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY
else:
    st.error("⚠️ GROQ_API_KEY not found! Please add it to your .env file")
    st.stop()

st.set_page_config(
    page_title="AI Coding Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize project root
init_project_root()

# Title and description
st.title("🤖 AI Coding Assistant")
st.markdown("**AI-powered code generator** - Transform your ideas into working code!")

# Sidebar with example prompts only
with st.sidebar:
    st.markdown("### 💡 Example Prompts")
    st.markdown("""
    - Create a to-do list app with HTML, CSS, JS
    - Build a calculator with Python
    - Make a simple blog website
    - Create a weather dashboard
    - Build a landing page for a coffee shop
    - Create a digital clock with JavaScript
    """)

    st.markdown("---")
    st.markdown("### ℹ️ How it works")
    st.markdown("""
    1. Describe your project
    2. AI generates complete code
    3. Download your project
    4. Unzip your project before running
    5. Run it locally!
    """)

# Main content
st.header("📝 Describe your project:")

user_prompt = st.text_area(
    "What do you want to build?",
    placeholder="e.g., Create a simple calculator web application with HTML, CSS, and JavaScript",
    height=150,
    label_visibility="collapsed"
)

# Generate button
if st.button("🚀 Generate Project", type="primary", use_container_width=True):
    if not user_prompt:
        st.error("❌ Please enter a project description!")
    else:
        # Clear previous project
        import shutil

        if PROJECT_ROOT.exists():
            shutil.rmtree(PROJECT_ROOT)
        init_project_root()

        # Progress tracking
        progress_bar = st.progress(0, text="🤖 Coder Buddy is working...")
        status = st.empty()

        try:
            # Planning phase
            status.info("📋 Planning your project...")
            progress_bar.progress(25)

            # Architecture phase
            status.info("🏗️ Designing architecture...")
            progress_bar.progress(50)

            # Coding phase
            status.info("💻 Writing code...")
            progress_bar.progress(75)

            # Generate project
            result = agent.invoke(
                {"user_prompt": user_prompt},
                {"recursion_limit": 100}
            )

            progress_bar.progress(100)
            status.success("✅ Project generated!")

            # Display success message
            st.success("🎉 **Project generated successfully!**")

            # Extract plan from result
            if "plan" in result:
                plan = result["plan"]

                # Project overview
                st.header("📊 Project Overview")

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📦 Details")
                    st.write(f"**Name:** {plan.name}")
                    st.write(f"**Description:** {plan.description}")
                    st.write(f"**Tech Stack:** {plan.techstack}")

                with col2:
                    st.subheader("✨ Features")
                    for feature in plan.features:
                        st.write(f"- {feature}")

                # Files planned
                st.subheader("📁 Files Created")
                for file in plan.files:
                    st.write(f"- `{file.path}` - {file.purpose}")

            # Display generated files
            st.header("💻 Generated Code")

            if PROJECT_ROOT.exists():
                # Get all generated files
                files = list(PROJECT_ROOT.rglob("*"))
                file_list = [f for f in files if f.is_file()]

                if file_list:
                    st.write(f"**Total files created:** {len(file_list)}")

                    # Language mapping for syntax highlighting
                    lang_map = {
                        '.py': 'python',
                        '.js': 'javascript',
                        '.html': 'html',
                        '.css': 'css',
                        '.json': 'json',
                        '.md': 'markdown',
                        '.jsx': 'javascript',
                        '.tsx': 'typescript',
                        '.ts': 'typescript',
                        '.yml': 'yaml',
                        '.yaml': 'yaml',
                        '.txt': 'text',
                    }

                    # Display each file
                    for file_path in sorted(file_list):
                        relative_path = file_path.relative_to(PROJECT_ROOT)

                        with st.expander(f"📄 {relative_path}", expanded=False):
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()

                                # Get language for syntax highlighting
                                ext = file_path.suffix.lower()
                                lang = lang_map.get(ext, 'text')

                                # Display code with syntax highlighting
                                st.code(content, language=lang, line_numbers=True)

                                # Download button for individual file
                                st.download_button(
                                    label=f"⬇️ Download {file_path.name}",
                                    data=content,
                                    file_name=file_path.name,
                                    mime="text/plain",
                                    key=f"download_{relative_path}"
                                )

                            except Exception as e:
                                st.error(f"Could not read file: {e}")

                    # Download all as ZIP
                    st.header("📦 Download Project")

                    # Create ZIP file
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for file_path in file_list:
                            zip_file.write(
                                file_path,
                                file_path.relative_to(PROJECT_ROOT)
                            )

                    zip_buffer.seek(0)

                    # Clean filename - check if plan exists first
                    if "plan" in result and hasattr(result["plan"], "name"):
                        project_name = result["plan"].name.replace(' ', '_').replace('/', '_').lower()
                    else:
                        project_name = "generated_project"

                    st.download_button(
                        label="📥 Download Complete Project as ZIP",
                        data=zip_buffer,
                        file_name=f"{project_name}_project.zip",
                        mime="application/zip",
                        use_container_width=True
                    )

                    # ADDED THIS
                    st.markdown("""
                    **💡 Quick tip:** 
                    - **Windows:** Right-click the ZIP → "Extract All"
                    - **Mac:** Double-click the ZIP file
                    - **Linux:** Right-click → "Extract Here"

                    Or download files individually using the buttons above! 👆
                    """)

                    # Show where files are saved
                    st.info(f"📁 Files are also saved locally at: `{PROJECT_ROOT}`")

                else:
                    st.warning("⚠️ No files were generated.")
                    st.info(
                        "💡 **Tip:** Try being more specific in your prompt. For example: 'Create a calculator with HTML, CSS, and JavaScript that can add, subtract, multiply, and divide.'")
            else:
                st.warning("⚠️ Project directory not found.")
                st.info("The project folder should be created automatically. This might be a permissions issue.")

            # Show raw state only in expander for debugging
            with st.expander("🔍 Debug: View Raw State"):
                st.json(result)

        except Exception as e:
            st.error(f"❌ Error generating project: {str(e)}")
            with st.expander("🐛 View Error Details"):
                st.exception(e)

            # Provide helpful troubleshooting
            st.info("""
            **Common issues:**
            - API key not set correctly
            - Network connection problems
            - Recursion limit reached (try a simpler project)
            """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Made with ❤️ using LangGraph • Created by Karan Kumar</p>
</div>
""", unsafe_allow_html=True)