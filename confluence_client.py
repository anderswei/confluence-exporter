"""
Confluence API Client
Handles communication with Confluence REST API
"""
import re
import requests
from urllib.parse import urlparse, urljoin


class ConfluenceClient:
    """Client for interacting with Confluence REST API"""
    
    def __init__(self, page_url, username, api_token):
        """
        Initialize Confluence client
        
        Args:
            page_url: Full URL to a Confluence page or folder
            username: Confluence username (email)
            api_token: Confluence API token
        """
        self.username = username
        self.api_token = api_token
        self.page_url = page_url
        
        # Parse the URL to get base URL and page/folder ID
        self.base_url, self.page_id, self.is_folder = self._parse_confluence_url(page_url)
        self.api_base = f"{self.base_url}/rest/api"
        
        # Setup session with authentication
        self.session = requests.Session()
        self.session.auth = (username, api_token)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _parse_confluence_url(self, url):
        """
        Parse Confluence URL to extract base URL and page/folder ID
        
        Args:
            url: Confluence page or folder URL
            
        Returns:
            tuple: (base_url, page_id, is_folder)
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Try to extract page/folder ID from various Confluence URL formats
        # Format 1: /pages/viewpage.action?pageId=123456
        # Format 2: /display/SPACE/Page+Title (needs lookup)
        # Format 3: /spaces/SPACE/pages/123456/Page+Title
        # Format 4: /spaces/SPACE/folder/123456 (folder)
        
        page_id = None
        is_folder = False
        
        # Check if it's a folder URL
        if '/folder/' in url:
            match = re.search(r'/folder/(\d+)', url)
            if match:
                page_id = match.group(1)
                is_folder = True
        # Try to find pageId parameter
        elif 'pageId=' in url:
            match = re.search(r'pageId=(\d+)', url)
            if match:
                page_id = match.group(1)
        # Try to find page ID in path
        elif '/pages/' in url:
            match = re.search(r'/pages/(\d+)', url)
            if match:
                page_id = match.group(1)
        
        if not page_id:
            # If we can't extract page ID, we'll need to look it up
            # For now, raise an error with helpful message
            raise ValueError(
                "Could not extract page/folder ID from URL. "
                "Please use a URL format like:\n"
                "  Page: https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title\n"
                "  Folder: https://your-domain.atlassian.net/wiki/spaces/SPACE/folder/123456"
            )
        
        return base_url, page_id, is_folder
    
    def _make_request(self, endpoint, params=None):
        """
        Make authenticated request to Confluence API
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            dict: JSON response
        """
        url = urljoin(self.api_base, endpoint)
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_page_info(self):
        """
        Get information about the page
        
        Returns:
            dict: Page information including id, title, space
        """
        endpoint = f"/wiki/rest/api/content/{self.page_id}"
        params = {
            'expand': 'space,version,body.storage'
        }
        return self._make_request(endpoint, params)
    
    def get_page_content(self, page_id):
        """
        Get full HTML content of a page
        
        Args:
            page_id: Confluence page ID
            
        Returns:
            str: HTML content of the page
        """
        endpoint = f"/wiki/rest/api/content/{page_id}"
        params = {
            'expand': 'body.storage,body.view'
        }
        page_data = self._make_request(endpoint, params)
        
        # Try to get the rendered view first, fallback to storage format
        if 'body' in page_data:
            if 'view' in page_data['body']:
                return page_data['body']['view']['value']
            elif 'storage' in page_data['body']:
                return page_data['body']['storage']['value']
        
        return ""
    
    def get_page_properties(self, page_id):
        """
        Get page properties including all contributors from version history
        
        Args:
            page_id: Confluence page ID
            
        Returns:
            dict: Page properties including contributors list with displayName and profilePicture
        """
        all_properties = {}
        contributors = {}  # Use dict to track unique contributors by accountId
        
        try:
            # Get version history to collect all contributors
            start = 0
            limit = 25
            
            while True:
                endpoint = f"/wiki/rest/api/content/{page_id}/history"
                params = {
                    'limit': limit,
                    'start': start,
                    'expand': 'contributors.publishers'
                }
                
                history_data = self._make_request(endpoint, params)
                
                # Process contributors from this batch
                if 'contributors' in history_data:
                    # Get publishers (users who edited the page)
                    if 'publishers' in history_data['contributors']:
                        publishers = history_data['contributors']['publishers']
                        if 'users' in publishers:
                            for user in publishers['users']:
                                account_id = user.get('accountId', user.get('username', ''))
                                if account_id and account_id not in contributors:
                                    contributor_info = {
                                        'displayName': user.get('displayName', user.get('username', 'Unknown')),
                                        'accountId': account_id
                                    }
                                    
                                    # Get profile picture if available
                                    if 'profilePicture' in user:
                                        contributor_info['profilePicture'] = user['profilePicture'].get('path', '')
                                    
                                    contributors[account_id] = contributor_info
                                    print(f"      Contributor: {contributor_info['displayName']}")
                
                # Check if we've processed all history
                # The history endpoint doesn't return a paginated list in the same way
                # It returns a single history object, not a results array
                break
            
            # Also get the page creator from the main content endpoint
            try:
                endpoint = f"/wiki/rest/api/content/{page_id}"
                params = {
                    'expand': 'history.createdBy,version.by'
                }
                page_data = self._make_request(endpoint, params)
                
                # Add creator
                if 'history' in page_data and 'createdBy' in page_data['history']:
                    creator = page_data['history']['createdBy']
                    account_id = creator.get('accountId', creator.get('username', ''))
                    if account_id and account_id not in contributors:
                        contributor_info = {
                            'displayName': creator.get('displayName', creator.get('username', 'Unknown')),
                            'accountId': account_id,
                            'isCreator': True
                        }
                        if 'profilePicture' in creator:
                            contributor_info['profilePicture'] = creator['profilePicture'].get('path', '')
                        contributors[account_id] = contributor_info
                        print(f"      Creator: {contributor_info['displayName']}")
                
                # Add last modifier
                if 'version' in page_data and 'by' in page_data['version']:
                    modifier = page_data['version']['by']
                    account_id = modifier.get('accountId', modifier.get('username', ''))
                    if account_id and account_id not in contributors:
                        contributor_info = {
                            'displayName': modifier.get('displayName', modifier.get('username', 'Unknown')),
                            'accountId': account_id
                        }
                        if 'profilePicture' in modifier:
                            contributor_info['profilePicture'] = modifier['profilePicture'].get('path', '')
                        contributors[account_id] = contributor_info
                        print(f"      Last modifier: {contributor_info['displayName']}")
            except Exception as e:
                print(f"      Note: Could not retrieve creator/modifier info: {str(e)}")
            
            # Convert contributors dict to list
            all_properties['contributors'] = list(contributors.values())
            print(f"      Total unique contributors: {len(contributors)}")
            print(f"      Contributors: {[c['displayName'] for c in all_properties['contributors']]}")
                
        except Exception as e:
            print(f"      Note: Could not retrieve page history: {str(e)}")
            all_properties['contributors'] = []
        
        return all_properties
    
    def get_child_pages(self, page_id):
        """
        Get all child pages of a given page
        
        Args:
            page_id: Parent page ID
            
        Returns:
            list: List of child page dictionaries
        """
        all_children = []
        start = 0
        limit = 25
        
        while True:
            endpoint = f"/wiki/rest/api/content/{page_id}/child/page"
            params = {
                'expand': 'version',
                'limit': limit,
                'start': start
            }
            
            response = self._make_request(endpoint, params)
            results = response.get('results', [])
            all_children.extend(results)
            
            # Check if there are more pages
            if len(results) < limit:
                break
            
            start += limit
        
        # Recursively get children of children
        all_descendants = []
        for child in all_children:
            all_descendants.append(child)
            grandchildren = self.get_child_pages(child['id'])
            all_descendants.extend(grandchildren)
        
        return all_descendants
    
    def get_pages_in_folder(self, folder_id):
        """
        Get all pages within a folder and its subfolders
        
        Args:
            folder_id: Folder ID
            
        Returns:
            list: List of all page dictionaries in the folder hierarchy
        """
        all_pages = []
        
        # Get direct pages in this folder
        pages = self._get_folder_contents(folder_id, 'page')
        all_pages.extend(pages)
        
        # Get subfolders
        subfolders = self._get_folder_contents(folder_id, 'folder')
        print(f"Found {len(subfolders)} subfolder(s) in folder ID {folder_id}")
        subfolders.foreach(lambda sf: print(f"  Subfolder: {sf.get('title', 'Unnamed')} (ID: {sf.get('id')})"))
        
        # Recursively get pages from subfolders
        for subfolder in subfolders:
            subfolder_pages = self.get_pages_in_folder(subfolder['id'])
            all_pages.extend(subfolder_pages)
        
        return all_pages
    
    def _get_folder_contents(self, folder_id, content_type='page'):
        """
        Get contents of a folder (pages or subfolders)
        
        Args:
            folder_id: Folder ID
            content_type: 'page' or 'folder'
            
        Returns:
            list: List of content items
        """
        all_items = []
        start = 0
        limit = 25
        
        while True:
            endpoint = f"/wiki/rest/api/content/{folder_id}/child/{content_type}"
            params = {
                'expand': 'version',
                'limit': limit,
                'start': start
            }
            
            try:
                response = self._make_request(endpoint, params)
                results = response.get('results', [])
                all_items.extend(results)
                
                # Check if there are more items
                if len(results) < limit:
                    break
                
                start += limit
            except requests.exceptions.HTTPError as e:
                # If we get a 404, the folder might not have this content type
                if e.response.status_code == 404:
                    break
                raise
        
        return all_items
    
    def get_folder_info(self):
        """
        Get information about a folder
        
        Returns:
            dict: Folder information
        """
        endpoint = f"/wiki/rest/api/content/{self.page_id}"
        params = {
            'expand': 'space,version'
        }
        return self._make_request(endpoint, params)
    
    def get_page_attachments(self, page_id):
        """
        Get all attachments for a page
        
        Args:
            page_id: Page ID
            
        Returns:
            list: List of attachment dictionaries
        """
        all_attachments = []
        start = 0
        limit = 25
        
        while True:
            endpoint = f"/wiki/rest/api/content/{page_id}/child/attachment"
            params = {
                'expand': 'version',
                'limit': limit,
                'start': start
            }
            
            try:
                response = self._make_request(endpoint, params)
                results = response.get('results', [])
                all_attachments.extend(results)
                
                # Check if there are more attachments
                if len(results) < limit:
                    break
                
                start += limit
            except requests.exceptions.HTTPError as e:
                # If we get a 404, the page might not have attachments
                if e.response.status_code == 404:
                    break
                raise
        
        return all_attachments
    
    def download_attachment(self, attachment, output_path):
        """
        Download an attachment to a file
        
        Args:
            attachment: Attachment dictionary from API
            output_path: Path where the file should be saved
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the download URL
            if '_links' not in attachment or 'download' not in attachment['_links']:
                print(f"      ✗ No download link found in attachment data")
                return False
                
            download_url = "/wiki" + attachment['_links']['download']
            print (f"      Download URL: {download_url}")
            # Make it absolute
            if not download_url.startswith('http'):
                download_url = urljoin(self.base_url, download_url)
            print (f"      Absolute Download URL: {download_url}")
            # Download the file
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()
            
            # Save to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
        except requests.exceptions.HTTPError as e:
            print(f"      ✗ HTTP Error {e.response.status_code}: {str(e)}")
            return False
        except Exception as e:
            print(f"      ✗ Error downloading attachment: {str(e)}")
            return False
    
    def get_pages_in_folder_with_structure(self, folder_id, parent_path=''):
        """
        Get all pages within a folder and its subfolders with path information
        
        Args:
            folder_id: Folder ID
            parent_path: Path to parent folder (for recursion)
            
        Returns:
            list: List of tuples (page_dict, relative_path)
        """
        all_pages = []
        
        # Get folder info to build path
        try:
            folder_info = self._get_content_info(folder_id)
            folder_name = folder_info.get('title', f'folder_{folder_id}')
            current_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
        except:
            current_path = parent_path if parent_path else ''
        
        # Get direct pages in this folder
        pages = self._get_folder_contents(folder_id, 'page')
        for page in pages:
            all_pages.append((page, current_path))
        
        # Get subfolders
        subfolders = self._get_folder_contents(folder_id, 'folder')
        
        # Recursively get pages from subfolders
        for subfolder in subfolders:
            subfolder_pages = self.get_pages_in_folder_with_structure(subfolder['id'], current_path)
            all_pages.extend(subfolder_pages)
        
        return all_pages
    
    def _get_content_info(self, content_id):
        """
        Get basic information about any content (page/folder)
        
        Args:
            content_id: Content ID
            
        Returns:
            dict: Content information
        """
        endpoint = f"/wiki/rest/api/content/{content_id}"
        params = {
            'expand': 'version'
        }
        return self._make_request(endpoint, params)
    
    def get_child_pages_and_folders_with_structure(self, page_id, parent_path=''):
        """
        Get all child pages and folders recursively with path information
        
        Args:
            page_id: Parent page ID
            parent_path: Path to parent (for recursion)
            
        Returns:
            list: List of tuples (page_dict, relative_path)
        """
        all_pages = []
        
        # Get direct child pages
        child_pages = self._get_folder_contents(page_id, 'page')
        for page in child_pages:
            all_pages.append((page, parent_path))
        
        # Get child folders
        child_folders = self._get_folder_contents(page_id, 'folder')
        
        # Recursively get pages from child folders
        for folder in child_folders:
            folder_name = folder.get('title', f'folder_{folder["id"]}')
            folder_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
            
            # Get pages in this folder and its subfolders
            folder_pages = self.get_pages_in_folder_with_structure(folder['id'], parent_path)
            all_pages.extend(folder_pages)
        
        return all_pages
