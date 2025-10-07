"""
Confluence to PDF Exporter
Downloads all pages from a Confluence space, folder, or page URL and exports them as PDFs.
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
    print("Confluence Page/Folder/Space to PDF Exporter")
    print("=" * 60)
    confluence_url = input("\nEnter the Confluence page, folder, or space URL: ").strip()
    
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
        space_name = None
        
        # Queue-based approach: (content_id, content_type, relative_path, content_dict)
        # content_dict is None if we need to fetch it, or the actual dict if we already have it
        todo_queue = []
        processed_ids = set()
        
        # Initialize queue based on entry point
        if confluence.is_space:
            print("Detected space URL")
            print("Fetching space information...")
            space_info = confluence.get_space_info(confluence.space_key)
            space_name = space_info.get('name', confluence.space_key)
            print(f"Space: {space_name} ({confluence.space_key})")
            
            # Create space-specific output directory
            space_output_dir = os.path.join(output_dir, space_name)
            os.makedirs(space_output_dir, exist_ok=True)
            exporter = PDFExporter(space_output_dir)
            print(f"Output directory: {space_output_dir}")
            
            # Get all top-level content in space
            print("\nFetching all content in space...")
            space_content = confluence.get_space_content(confluence.space_key)
            print(f"Found {len(space_content)} top-level item(s) in space")
            
            # Add all top-level items to queue
            for content in space_content:
                content_type = content.get('type', 'page')
                # Top-level pages go in root, top-level folders create subdirectories
                if content_type == 'folder':
                    folder_name = content.get('title', f'folder_{content["id"]}')
                    todo_queue.append((content['id'], content_type, folder_name, content))
                else:
                    todo_queue.append((content['id'], content_type, '', content))
            
        elif confluence.is_folder:
            print("Detected folder URL")
            print("Fetching folder information...")
            folder_info = confluence.get_folder_info()
            folder_name = folder_info.get('title', 'Unnamed Folder')
            print(f"Folder: {folder_name}")
            
            # Start with the folder itself - it should create a subdirectory
            todo_queue.append((confluence.page_id, 'folder', folder_name, folder_info))
            
        else:
            print("Detected page URL")
            print("Fetching page information...")
            parent_page = confluence.get_page_info()
            print(f"Parent page: {parent_page['title']}")
            
            # Start with the page itself
            todo_queue.append((parent_page['id'], 'page', '', parent_page))
        
        # Process queue
        print("\nDiscovering all pages in hierarchy...")
        while todo_queue:
            content_id, content_type, current_path, content_dict = todo_queue.pop(0)
            
            # Skip if already processed
            if content_id in processed_ids:
                continue
            processed_ids.add(content_id)
            
            # Fetch content info if we don't have it
            if content_dict is None:
                try:
                    content_dict = confluence._get_content_info(content_id)
                except Exception as e:
                    print(f"Warning: Could not fetch info for content ID {content_id}: {str(e)}")
                    continue
            
            content_title = content_dict.get('title', f'untitled_{content_id}')
            
            if content_type == 'page':
                # Add page to export list
                all_pages_with_paths.append((content_dict, current_path))
                print(f"  Found page: {content_title}" + (f" (in {current_path})" if current_path else ""))
                
                # Children of this page should be in a subfolder named after this page
                page_folder_name = content_dict.get('title', f'page_{content_id}')
                child_path = f"{current_path}/{page_folder_name}" if current_path else page_folder_name
                
                # Get child pages and folders
                try:
                    child_pages = confluence._get_folder_contents(content_id, 'page')
                    for child_page in child_pages:
                        if child_page['id'] not in processed_ids:
                            todo_queue.append((child_page['id'], 'page', child_path, child_page))
                except Exception as e:
                    print(f"    Warning: Could not fetch child pages: {str(e)}")
                
                try:
                    child_folders = confluence._get_folder_contents(content_id, 'folder')
                    for child_folder in child_folders:
                        if child_folder['id'] not in processed_ids:
                            folder_name = child_folder.get('title', f'folder_{child_folder["id"]}')
                            folder_path = f"{child_path}/{folder_name}"
                            todo_queue.append((child_folder['id'], 'folder', folder_path, child_folder))
                except Exception as e:
                    print(f"    Warning: Could not fetch child folders: {str(e)}")
            
            elif content_type == 'folder':
                print(f"  Processing folder: {content_title}" + (f" (path: {current_path})" if current_path else ""))
                
                # Get pages in folder
                try:
                    folder_pages = confluence._get_folder_contents(content_id, 'page')
                    for page in folder_pages:
                        if page['id'] not in processed_ids:
                            # Pages in folder should use the folder's path
                            todo_queue.append((page['id'], 'page', current_path, page))
                except Exception as e:
                    print(f"    Warning: Could not fetch pages in folder: {str(e)}")
                
                # Get subfolders
                try:
                    subfolders = confluence._get_folder_contents(content_id, 'folder')
                    for subfolder in subfolders:
                        if subfolder['id'] not in processed_ids:
                            subfolder_name = subfolder.get('title', f'folder_{subfolder["id"]}')
                            # Subfolders should append their name to current path
                            subfolder_path = f"{current_path}/{subfolder_name}" if current_path else subfolder_name
                            todo_queue.append((subfolder['id'], 'folder', subfolder_path, subfolder))
                except Exception as e:
                    print(f"    Warning: Could not fetch subfolders: {str(e)}")
        
        if not all_pages_with_paths:
            print("No pages found")
            sys.exit(0)
        
        print(f"\nTotal pages discovered: {len(all_pages_with_paths)}")
        
        # Export all pages
        print(f"\n{'=' * 60}")
        print(f"Exporting {len(all_pages_with_paths)} page(s) to PDF...")
        print(f"{'=' * 60}\n")
        
        for i, (page, relative_path) in enumerate(all_pages_with_paths, 1):
            print(f"[{i}/{len(all_pages_with_paths)}] Exporting: {page['title']}")
            if relative_path:
                print(f"    Output path: {relative_path}/{page['title']}.pdf")
            else:
                print(f"    Output path: {page['title']}.pdf (root)")
            
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
        if confluence.is_space:
            print(f"Export completed! PDFs saved in: {os.path.abspath(os.path.join(output_dir, space_name))}")
        else:
            print(f"Export completed! PDFs saved in: {os.path.abspath(output_dir)}")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
