"""
Confluence to PDF Exporter
Downloads all pages from a Confluence space, folder, or page URL and exports them as PDFs.
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from confluence_client import ConfluenceClient
from pdf_exporter import PDFExporter


def setup_logging(debug=False):
    """Configure logging for the application"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler()]
    )


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Export Confluence pages to PDF')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    username = os.getenv('CONFLUENCE_USERNAME')
    api_token = os.getenv('CONFLUENCE_API_TOKEN')
    
    if not username or not api_token:
        logger.error("Missing credentials!")
        logger.error("Please create a .env file with CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN")
        logger.error("You can copy .env.example to .env and fill in your credentials")
        sys.exit(1)
    
    # Get Confluence URL from user
    print("=" * 60)
    print("Confluence Page/Folder/Space to PDF Exporter")
    print("=" * 60)
    confluence_url = input("\nEnter the Confluence page, folder, or space URL: ").strip()
    
    if not confluence_url:
        logger.error("URL cannot be empty")
        sys.exit(1)
    
    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize clients
        logger.info("Connecting to Confluence...")
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
            logger.info("Detected space URL")
            logger.info("Fetching space information...")
            space_info = confluence.get_space_info(confluence.space_key)
            space_name = space_info.get('name', confluence.space_key)
            logger.info(f"Space: {space_name} ({confluence.space_key})")
            
            # Create space-specific output directory
            space_output_dir = os.path.join(output_dir, space_name)
            os.makedirs(space_output_dir, exist_ok=True)
            exporter = PDFExporter(space_output_dir)
            logger.info(f"Output directory: {space_output_dir}")
            
            # Get all top-level content in space
            logger.info("Fetching all content in space...")
            space_content = confluence.get_space_content(confluence.space_key)
            logger.info(f"Found {len(space_content)} top-level item(s) in space")
            
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
            logger.info("Detected folder URL")
            logger.info("Fetching folder information...")
            folder_info = confluence.get_folder_info()
            folder_name = folder_info.get('title', 'Unnamed Folder')
            logger.info(f"Folder: {folder_name}")
            
            # Start with the folder itself - it should create a subdirectory
            todo_queue.append((confluence.page_id, 'folder', folder_name, folder_info))
            
        else:
            logger.info("Detected page URL")
            logger.info("Fetching page information...")
            parent_page = confluence.get_page_info()
            logger.info(f"Parent page: {parent_page['title']}")
            
            # Start with the page itself
            todo_queue.append((parent_page['id'], 'page', '', parent_page))
        
        # Process queue
        logger.info("Discovering all pages in hierarchy...")
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
                    logger.warning(f"Could not fetch info for content ID {content_id}: {str(e)}")
                    continue
            
            content_title = content_dict.get('title', f'untitled_{content_id}')
            
            if content_type == 'page':
                # Add page to export list
                all_pages_with_paths.append((content_dict, current_path))
                logger.debug(f"Found page: {content_title}" + (f" (in {current_path})" if current_path else ""))
                
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
                    logger.debug(f"Could not fetch child pages: {str(e)}")
                
                try:
                    child_folders = confluence._get_folder_contents(content_id, 'folder')
                    for child_folder in child_folders:
                        if child_folder['id'] not in processed_ids:
                            folder_name = child_folder.get('title', f'folder_{child_folder["id"]}')
                            folder_path = f"{child_path}/{folder_name}"
                            todo_queue.append((child_folder['id'], 'folder', folder_path, child_folder))
                except Exception as e:
                    logger.debug(f"Could not fetch child folders: {str(e)}")
            
            elif content_type == 'folder':
                logger.debug(f"Processing folder: {content_title}" + (f" (path: {current_path})" if current_path else ""))
                
                # Get pages in folder
                try:
                    folder_pages = confluence._get_folder_contents(content_id, 'page')
                    for page in folder_pages:
                        if page['id'] not in processed_ids:
                            # Pages in folder should use the folder's path
                            todo_queue.append((page['id'], 'page', current_path, page))
                except Exception as e:
                    logger.debug(f"Could not fetch pages in folder: {str(e)}")
                
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
                    logger.debug(f"Could not fetch subfolders: {str(e)}")
        
        if not all_pages_with_paths:
            logger.info("No pages found")
            sys.exit(0)
        
        logger.info(f"Total pages discovered: {len(all_pages_with_paths)}")
        
        # Export all pages
        logger.info("=" * 60)
        logger.info(f"Exporting {len(all_pages_with_paths)} page(s) to PDF...")
        logger.info("=" * 60)
        
        for i, (page, relative_path) in enumerate(all_pages_with_paths, 1):
            logger.info(f"[{i}/{len(all_pages_with_paths)}] Exporting: {page['title']}")
            if relative_path:
                logger.debug(f"Output path: {relative_path}/{page['title']}.pdf")
            else:
                logger.debug(f"Output path: {page['title']}.pdf (root)")
            
            # Get page content
            page_content = confluence.get_page_content(page['id'])
            
            # Get page properties (including contributors/owners)
            contributors = []
            try:
                properties = confluence.get_page_properties(page['id'])
                # Extract contributors list from properties
                if 'contributors' in properties:
                    contributors = properties['contributors']
                    logger.debug(f"Contributors: {', '.join([c.get('displayName', 'Unknown') for c in contributors])}")
            except Exception as e:
                logger.debug(f"Could not fetch contributors: {str(e)}")
            
            # Get attachments for this page
            try:
                attachments = confluence.get_page_attachments(page['id'])
                if attachments:
                    logger.debug(f"Found {len(attachments)} attachment(s)")
            except Exception as e:
                logger.debug(f"Could not fetch attachments: {str(e)}")
                attachments = []
            
            # Export to PDF with attachments, path, and contributors
            exporter.export_to_pdf(page, page_content, attachments, relative_path, confluence, contributors)
        
        logger.info("=" * 60)
        if confluence.is_space:
            logger.info(f"Export completed! PDFs saved in: {os.path.abspath(os.path.join(output_dir, space_name))}")
        else:
            logger.info(f"Export completed! PDFs saved in: {os.path.abspath(output_dir)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
