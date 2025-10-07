"""
PDF Exporter
Converts Confluence HTML content to PDF files
"""
import os
import re
import base64
from io import BytesIO
from urllib.parse import urljoin
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup


class PDFExporter:
    """Exports Confluence pages to PDF format"""
    
    def __init__(self, output_dir):
        """
        Initialize PDF exporter
        
        Args:
            output_dir: Directory to save PDF files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def _parse_and_sort_contributors(self, contributors_data):
        """
        Parse contributors data and sort alphabetically by first name
        
        Args:
            contributors_data: Contributors information from Confluence (list of dicts with displayName, profilePicture, etc.)
            
        Returns:
            list: Sorted list of contributor dictionaries
        """
        contributors = []
        
        # Handle different data formats
        if isinstance(contributors_data, list):
            # Already in the expected format from get_page_properties
            contributors = contributors_data
        elif isinstance(contributors_data, str):
            # Fallback: Split by common delimiters and create simple dict entries
            names = re.split(r'[,;\n]+', contributors_data)
            contributors = [{'displayName': name.strip()} for name in names if name.strip()]
        elif isinstance(contributors_data, dict):
            # Single contributor as dict
            contributors = [contributors_data]
        
        # Sort by first name from displayName
        def get_first_name(contributor):
            if isinstance(contributor, dict):
                name = contributor.get('displayName', '')
            else:
                name = str(contributor)
            
            name = name.strip()
            # Handle "Last, First" format
            if ',' in name:
                parts = name.split(',')
                if len(parts) > 1:
                    return parts[1].strip().lower()
            # Handle "First Last" format
            parts = name.split()
            if parts:
                return parts[0].lower()
            return name.lower()
        
        contributors.sort(key=get_first_name)
        
        return contributors
    
    def _sanitize_path(self, path):
        """
        Sanitize a path to be filesystem-safe
        
        Args:
            path: Original path
            
        Returns:
            str: Sanitized path
        """
        # Remove or replace invalid characters
        path = re.sub(r'[<>:"|?*]', '', path)
        # Clean up multiple slashes
        path = re.sub(r'/+', '/', path)
        return path.strip('/')
    
    def _sanitize_filename(self, filename):
        """
        Sanitize filename to be filesystem-safe
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def _clean_html(self, html_content):
        """
        Clean and prepare HTML content for PDF conversion
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            str: Cleaned HTML content
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove Confluence-specific macros that might not render well
        for macro in soup.find_all('ac:structured-macro'):
            macro.decompose()
        
        # Convert relative URLs to absolute if needed
        # (This would require the base URL - simplified for now)
        
        return str(soup)
    
    def _create_html_template(self, title, content):
        """
        Create a complete HTML document with styling
        
        Args:
            title: Page title
            content: HTML content
            
        Returns:
            str: Complete HTML document
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-right {{
                content: counter(page);
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #172B4D;
            max-width: 100%;
        }}
        h1 {{
            color: #172B4D;
            border-bottom: 2px solid #0052CC;
            padding-bottom: 10px;
            margin-top: 20px;
        }}
        h2 {{
            color: #172B4D;
            border-bottom: 1px solid #DFE1E6;
            padding-bottom: 8px;
            margin-top: 18px;
        }}
        h3, h4, h5, h6 {{
            color: #172B4D;
            margin-top: 16px;
        }}
        code {{
            background-color: #F4F5F7;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #F4F5F7;
            padding: 12px;
            border-radius: 3px;
            overflow-x: auto;
            border-left: 3px solid #0052CC;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }}
        th, td {{
            border: 1px solid #DFE1E6;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #F4F5F7;
            font-weight: 600;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        a {{
            color: #0052CC;
            text-decoration: none;
        }}
        blockquote {{
            border-left: 4px solid #0052CC;
            padding-left: 16px;
            margin-left: 0;
            color: #5E6C84;
        }}
        .page-title {{
            font-size: 2em;
            color: #172B4D;
            margin-bottom: 20px;
            border-bottom: 3px solid #0052CC;
            padding-bottom: 10px;
        }}
        .owners-section {{
            margin-top: 10px;
            margin-bottom: 30px;
            padding: 15px;
            background-color: #E3FCEF;
            border-radius: 5px;
            border-left: 4px solid #00875A;
        }}
        .owners-title {{
            font-size: 1.1em;
            color: #006644;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        .owners-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .owner-item {{
            padding: 8px 0;
            color: #172B4D;
            font-weight: 500;
            display: flex;
            align-items: center;
        }}
        .contributor-avatar {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            margin-right: 10px;
            border: 2px solid #00875A;
            object-fit: cover;
        }}
        .contributor-name {{
            flex: 1;
        }}
        .creator-badge {{
            font-size: 0.85em;
            color: #006644;
            font-weight: 600;
            margin-left: 8px;
        }}
        .attachments-section {{
            margin-top: 40px;
            padding: 20px;
            background-color: #F4F5F7;
            border-radius: 5px;
            border-left: 4px solid #0052CC;
        }}
        .attachments-title {{
            font-size: 1.3em;
            color: #172B4D;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        .attachment-list {{
            list-style: none;
            padding: 0;
        }}
        .attachment-item {{
            padding: 8px 0;
            border-bottom: 1px solid #DFE1E6;
        }}
        .attachment-item:last-child {{
            border-bottom: none;
        }}
        .attachment-link {{
            color: #0052CC;
            text-decoration: none;
            font-weight: 500;
        }}
        .attachment-info {{
            font-size: 0.9em;
            color: #5E6C84;
            margin-left: 10px;
        }}
        .version-history-section {{
            margin-top: 40px;
            padding: 20px;
            background-color: #F4F5F7;
            border-radius: 5px;
            border-left: 4px solid #6554C0;
            page-break-before: auto;
        }}
        .version-history-title {{
            font-size: 1.3em;
            color: #172B4D;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        .version-history-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        .version-history-table th {{
            background-color: #DFE1E6;
            color: #172B4D;
            font-weight: 600;
            padding: 8px 12px;
            text-align: left;
            border: 1px solid #C1C7D0;
        }}
        .version-history-table td {{
            padding: 6px 12px;
            border: 1px solid #DFE1E6;
            color: #172B4D;
        }}
        .version-history-table tr:nth-child(even) {{
            background-color: #FAFBFC;
        }}
        .version-number {{
            font-weight: 600;
            color: #6554C0;
        }}
    </style>
</head>
<body>
    <div class="page-title">{title}</div>
    <div class="content">
        {content}
    </div>
</body>
</html>
"""
        return html
    
    def _create_contributors_html(self, contributors, confluence_client=None):
        """
        Create HTML section for page contributors with profile pictures
        
        Args:
            contributors: List of contributor dictionaries (already sorted)
            confluence_client: ConfluenceClient instance for downloading profile pictures (optional)
            
        Returns:
            str: HTML content for contributors section
        """
        if not contributors:
            return ""
        
        html = '<div class="owners-section">\n'
        html += '  <div class="owners-title">� Contributor'
        if len(contributors) > 1:
            html += 's'
        html += '</div>\n'
        html += '  <ul class="owners-list">\n'
        
        for contributor in contributors:
            if isinstance(contributor, dict):
                display_name = contributor.get('displayName', 'Unknown')
                profile_pic = contributor.get('profilePicture', '')
                is_creator = contributor.get('isCreator', False)
                
                # Generate avatar HTML
                avatar_html = ''
                if profile_pic and confluence_client:
                    # Download and convert profile picture to base64 data URL
                    profile_data_url = self._get_profile_picture_data_url(profile_pic, confluence_client)
                    if profile_data_url:
                        avatar_html = f'<img src="{profile_data_url}" class="contributor-avatar" alt="{display_name}">'
                    else:
                        # Use default avatar emoji if download fails
                        avatar_html = '<span style="font-size: 32px; margin-right: 10px;">👤</span>'
                else:
                    # Use default avatar emoji if no profile picture
                    avatar_html = '<span style="font-size: 32px; margin-right: 10px;">👤</span>'
                
                # Add creator badge if applicable
                creator_badge = ''
                if is_creator:
                    creator_badge = '<span class="creator-badge">✨ Creator</span>'
                
                html += f'    <li class="owner-item">\n'
                html += f'      {avatar_html}\n'
                html += f'      <span class="contributor-name">{display_name}{creator_badge}</span>\n'
                html += f'    </li>\n'
            else:
                # Fallback for simple string format
                html += f'    <li class="owner-item">\n'
                html += f'      <span style="font-size: 32px; margin-right: 10px;">👤</span>\n'
                html += f'      <span class="contributor-name">{contributor}</span>\n'
                html += f'    </li>\n'
        
        html += '  </ul>\n'
        html += '</div>\n'
        
        return html
    
    def _get_profile_picture_data_url(self, profile_pic_path, confluence_client):
        """
        Download profile picture and convert to base64 data URL
        
        Args:
            profile_pic_path: Path to profile picture from Confluence API
            confluence_client: ConfluenceClient instance for downloading
            
        Returns:
            str: Base64 data URL or None if download fails
        """
        try:
            # Make profile picture URL absolute
            if not profile_pic_path.startswith('http'):
                profile_url = urljoin(confluence_client.base_url, profile_pic_path)
            else:
                profile_url = profile_pic_path
            
            # Download the image
            response = confluence_client.session.get(profile_url, timeout=5)
            response.raise_for_status()
            
            # Get content type
            content_type = response.headers.get('Content-Type', 'image/png')
            
            # Convert to base64
            image_data = base64.b64encode(response.content).decode('utf-8')
            data_url = f"data:{content_type};base64,{image_data}"
            
            return data_url
        except Exception as e:
            print(f"      Warning: Could not download profile picture from {profile_pic_path}: {str(e)}")
            return None
    
    def _create_attachments_html(self, attachments, attachments_folder_name):
        """
        Create HTML section for attachments list
        
        Args:
            attachments: List of attachment dictionaries
            attachments_folder_name: Name of the attachments folder
            
        Returns:
            str: HTML content for attachments section
        """
        if not attachments:
            return ""
        
        html = '<div class="attachments-section">\n'
        html += '  <div class="attachments-title">📎 Attachments</div>\n'
        html += '  <ul class="attachment-list">\n'
        
        for att in attachments:
            title = att.get('title', 'Untitled')
            size = att.get('extensions', {}).get('fileSize', 0)
            # Convert size to human readable
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            
            rel_path = f"{attachments_folder_name}/{title}"
            html += f'    <li class="attachment-item">\n'
            html += f'      <span class="attachment-link">{title}</span>\n'
            html += f'      <span class="attachment-info">({size_str}) → {rel_path}</span>\n'
            html += f'    </li>\n'
        
        html += '  </ul>\n'
        html += '</div>\n'
        
        return html
    
    def _create_version_history_html(self, versions):
        """
        Create HTML section for version history
        
        Args:
            versions: List of version dictionaries with number, when, by, and message
            
        Returns:
            str: HTML content for version history section
        """
        if not versions:
            return ""
        
        html = '<div class="version-history-section">\n'
        html += '  <div class="version-history-title">📜 Version History</div>\n'
        html += '  <table class="version-history-table">\n'
        html += '    <thead>\n'
        html += '      <tr>\n'
        html += '        <th>Version</th>\n'
        html += '        <th>Created</th>\n'
        html += '        <th>Author</th>\n'
        html += '      </tr>\n'
        html += '    </thead>\n'
        html += '    <tbody>\n'
        
        # Sort versions by number descending (newest first)
        sorted_versions = sorted(versions, key=lambda v: v.get('number', 0), reverse=True)
        
        for version in sorted_versions:
            version_num = version.get('number', 'N/A')
            when = version.get('when', 'Unknown')
            by = version.get('by', 'Unknown')
            
            # Format the date to be more readable
            try:
                from datetime import datetime
                if when and when != 'Unknown':
                    # Parse ISO format date
                    dt = datetime.fromisoformat(when.replace('Z', '+00:00'))
                    when = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass  # Keep original format if parsing fails
            
            html += f'      <tr>\n'
            html += f'        <td><span class="version-number">v{version_num}</span></td>\n'
            html += f'        <td>{when}</td>\n'
            html += f'        <td>{by}</td>\n'
            html += f'      </tr>\n'
        
        html += '    </tbody>\n'
        html += '  </table>\n'
        html += '</div>\n'
        
        return html
    
    def export_to_pdf(self, page_info, html_content, attachments=None, relative_path='', confluence_client=None, owners=None):
        """
        Export a Confluence page to PDF
        
        Args:
            page_info: Dictionary containing page information (id, title)
            html_content: HTML content of the page
            attachments: List of attachment dictionaries (optional)
            relative_path: Relative path for organizing output (optional)
            confluence_client: ConfluenceClient instance for downloading attachments (optional)
            owners: List or string of page owners (optional)
        """
        print(f"  Exporting page ID {page_info.get('id')} - '{page_info.get('title')}'  - owners: {owners}")
        # Get page title and create filename
        title = page_info.get('title', 'Untitled')
        page_id = page_info.get('id', 'unknown')
        
        # Create subdirectory if relative_path is provided
        if relative_path:
            safe_path = self._sanitize_path(relative_path)
            output_subdir = os.path.join(self.output_dir, safe_path)
            os.makedirs(output_subdir, exist_ok=True)
        else:
            output_subdir = self.output_dir
        
        filename = f"{self._sanitize_filename(title)}_{page_id}.pdf"
        filepath = os.path.join(output_subdir, filename)
        
        # Handle attachments if present
        attachments_folder_name = None
        if attachments and len(attachments) > 0:
            # Create attachments folder
            attachments_folder_name = f"{self._sanitize_filename(title)}_{page_id}_attachments"
            attachments_dir = os.path.join(output_subdir, attachments_folder_name)
            os.makedirs(attachments_dir, exist_ok=True)
            
            # Download attachments
            print(f"    Downloading {len(attachments)} attachment(s)...")
            for att in attachments:
                att_filename = att.get('title', 'unknown')
                att_filepath = os.path.join(attachments_dir, att_filename)
                
                if confluence_client:
                    if confluence_client.download_attachment(att, att_filepath):
                        print(f"      ✓ {att_filename}")
                    else:
                        print(f"      ✗ Failed: {att_filename}")
        
        # Clean HTML content
        cleaned_content = self._clean_html(html_content)
        
        # Process and add contributors section if provided
        contributors_html = ""
        if owners:  # Parameter is named 'owners' but now contains contributors list
            sorted_contributors = self._parse_and_sort_contributors(owners)
            if sorted_contributors:
                contributors_html = self._create_contributors_html(sorted_contributors, confluence_client)
        
        # Prepend contributors section to content (after title, before main content)
        if contributors_html:
            cleaned_content = contributors_html + cleaned_content
        
        # Add attachments section to HTML if attachments exist
        if attachments and len(attachments) > 0:
            attachments_html = self._create_attachments_html(attachments, attachments_folder_name)
            cleaned_content += attachments_html
        
        # Add version history section if confluence_client is available
        if confluence_client:
            try:
                print(f"    Fetching version history...")
                versions = confluence_client.get_version_history(page_id)
                if versions:
                    version_history_html = self._create_version_history_html(versions)
                    cleaned_content += version_history_html
                    print(f"    ✓ Added {len(versions)} version(s) to history")
            except Exception as e:
                print(f"    Note: Could not add version history: {str(e)}")
        
        # Create complete HTML document
        full_html = self._create_html_template(title, cleaned_content)
        
        # Convert to PDF
        try:
            HTML(string=full_html).write_pdf(filepath)
            relative_output = os.path.relpath(filepath, self.output_dir)
            print(f"  ✓ Saved: {relative_output}")
        except Exception as e:
            print(f"  ✗ Error saving {filename}: {str(e)}")
            # Save HTML for debugging if PDF generation fails
            html_filepath = filepath.replace('.pdf', '.html')
            with open(html_filepath, 'w', encoding='utf-8') as f:
                f.write(full_html)
            print(f"  → HTML saved for debugging: {html_filepath}")
