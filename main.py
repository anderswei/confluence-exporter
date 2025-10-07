"""
Confluence Page to PDF Exporter
Downloads all sub-pages from a Confluence URL and exports them as PDFs.
"""
import os
import sys
from dotenv import load_dotenv
from confluence_client import ConfluenceClient
from pdf_exporter import PDFExporter


def main():
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    username = os.getenv('CONFLUENCE_USERNAME')
    api_token = os.getenv('CONFLUENCE_API_TOKEN')
    
    if not username or not api_token:
        print("Error: Missing credentials!")
        print("Please create a .env file with CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN")
        print("You can copy .env.example to .env and fill in your credentials")
        sys.exit(1)
    
    # Get Confluence URL from user
    print("=" * 60)
    print("Confluence Page/Folder to PDF Exporter")
    print("=" * 60)
    confluence_url = input("\nEnter the Confluence page or folder URL: ").strip()
    
    if not confluence_url:
        print("Error: URL cannot be empty")
        sys.exit(1)
    
    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize clients
        print("\nConnecting to Confluence...")
        confluence = ConfluenceClient(confluence_url, username, api_token)
        exporter = PDFExporter(output_dir)
        
        all_pages_with_paths = []
        
        # Check if it's a folder or a page
        if confluence.is_folder:
            print("Detected folder URL")
            print("Fetching folder information...")
            folder_info = confluence.get_folder_info()
            folder_name = folder_info.get('title', 'Unnamed Folder')
            print(f"Folder: {folder_name}")
            
            # Get all pages in folder and subfolders with structure
            print("\nFetching all pages in folder hierarchy...")
            all_pages_with_paths = confluence.get_pages_in_folder_with_structure(confluence.page_id)
            
            if not all_pages_with_paths:
                print("No pages found in this folder")
                sys.exit(0)
            
            print(f"Found {len(all_pages_with_paths)} page(s) in folder hierarchy")
        else:
            print("Detected page URL")
            print("Fetching page information...")
            parent_page = confluence.get_page_info()
            print(f"Parent page: {parent_page['title']}")
            
            # Add parent page to list (no path for single page exports)
            all_pages_with_paths.append((parent_page, ''))
            
            # Get and add all child pages and folders with structure
            print("\nFetching child pages and folders...")
            child_pages_with_paths = confluence.get_child_pages_and_folders_with_structure(parent_page['id'])
            
            if child_pages_with_paths:
                print(f"Found {len(child_pages_with_paths)} child page(s) in hierarchy")
                all_pages_with_paths.extend(child_pages_with_paths)
            else:
                print("No child pages found")
        
        # Export all pages
        print(f"\n{'=' * 60}")
        print(f"Exporting {len(all_pages_with_paths)} page(s) to PDF...")
        print(f"{'=' * 60}\n")
        
        for i, (page, relative_path) in enumerate(all_pages_with_paths, 1):
            print(f"[{i}/{len(all_pages_with_paths)}] Exporting: {page['title']}")
            if relative_path:
                print(f"    Path: {relative_path}")
            
            # Get page content
            page_content = confluence.get_page_content(page['id'])
            
            # Get page properties (including contributors/owners)
            contributors = []
            try:
                properties = confluence.get_page_properties(page['id'])
                # Extract contributors list from properties
                if 'contributors' in properties:
                    contributors = properties['contributors']
                    print(f"    Contributors: {', '.join([c.get('displayName', 'Unknown') for c in contributors])}")
            except Exception as e:
                print(f"    Warning: Could not fetch contributors: {str(e)}")
            
            # Get attachments for this page
            try:
                attachments = confluence.get_page_attachments(page['id'])
                if attachments:
                    print(f"    Found {len(attachments)} attachment(s)")
            except Exception as e:
                print(f"    Warning: Could not fetch attachments: {str(e)}")
                attachments = []
            
            # Export to PDF with attachments, path, and contributors
            exporter.export_to_pdf(page, page_content, attachments, relative_path, confluence, contributors)
        
        print(f"\n{'=' * 60}")
        print(f"Export completed! PDFs saved in: {os.path.abspath(output_dir)}")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
