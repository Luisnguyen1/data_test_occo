import requests
import random
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

# Google Sheets configuration
SPREADSHEET_ID = '18kYNbaS6RtLV2r2MiqQPm0YqrGQiWYtBhIySyrWlg_M'
NEWS_SHEET_NAME = 'news'
BLOG_SHEET_NAME = 'blog'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# API endpoints
NEWS_CREATE_URL = 'http://103.147.186.168:8006/api/v1/news/create/'
BLOG_CREATE_URL = 'http://103.147.186.168:8006/api/v1/blog/create/'
UPLOAD_MULTI_URL = 'http://103.147.186.168:8006/api/v1/general/upload-multi/'

def get_google_sheets_service():
    """Initialize Google Sheets service"""
    try:
        # Sử dụng file credentials.json nếu có
        if os.path.exists('credentials.json'):
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        else:
            # Nếu không có file credentials, sẽ trả về None
            return None
        
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Sheets service: {e}")
        return None

def ensure_news_sheet_exists(service):
    """Ensure the 'news' sheet exists, create if not"""
    try:
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Check if 'news' sheet exists
        news_sheet_exists = any(sheet['properties']['title'] == NEWS_SHEET_NAME for sheet in sheets)
        
        if not news_sheet_exists:
            # Create the 'news' sheet
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': NEWS_SHEET_NAME
                    }
                }
            }]
            
            body = {'requests': requests}
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
            
            # Add header row for news sheet
            header_row = [['User ID', 'Tiêu đề', 'Nội dung', 'Quyền riêng tư', 'File URLs', 'Trạng Thái', 'News ID']]
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{NEWS_SHEET_NAME}!A1:G1',
                valueInputOption='RAW',
                body={'values': header_row}
            ).execute()
            
            print(f"Created sheet '{NEWS_SHEET_NAME}' with headers")
        
        return True
    except Exception as e:
        print(f"Error ensuring news sheet exists: {e}")
        return False

def ensure_blog_sheet_exists(service):
    """Ensure the 'blog' sheet exists, create if not"""
    try:
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Check if 'blog' sheet exists
        blog_sheet_exists = any(sheet['properties']['title'] == BLOG_SHEET_NAME for sheet in sheets)
        
        if not blog_sheet_exists:
            # Create the 'blog' sheet
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': BLOG_SHEET_NAME
                    }
                }
            }]
            
            body = {'requests': requests}
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
            
            # Add header row for blog sheet
            header_row = [['User ID', 'Tiêu đề', 'Nội dung', 'Quyền riêng tư', 'File URLs', 'Trạng Thái', 'Blog ID']]
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{BLOG_SHEET_NAME}!A1:G1',
                valueInputOption='RAW',
                body={'values': header_row}
            ).execute()
            
            print(f"Created sheet '{BLOG_SHEET_NAME}' with headers")
        
        return True
    except Exception as e:
        print(f"Error ensuring blog sheet exists: {e}")
        return False

def upload_files_to_api(file_urls, token):
    """Upload files to API and return file IDs"""
    if not file_urls:
        return []
    
    file_ids = []
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    for file_url in file_urls:
        try:
            print(f"Processing file URL: {file_url}")
            # Download file from URL
            file_response = requests.get(file_url.strip(), timeout=30)
            if file_response.status_code != 200:
                print(f"Failed to download file from {file_url}, status code: {file_response.status_code}")
                continue
            
            # Get filename from URL or use default
            try:
                # Lấy tên file từ URL
                if '?' in file_url:
                    clean_url = file_url.split('?')[0]  # Loại bỏ query parameters
                else:
                    clean_url = file_url
                
                filename = clean_url.split('/')[-1]
                if not filename:
                    filename = 'uploaded_file'
                
                # Đảm bảo filename không chứa ký tự đặc biệt
                filename = ''.join(c for c in filename if c.isalnum() or c in ['.', '-', '_'])
                
                # Thêm phần mở rộng nếu cần
                if '.' not in filename:
                    content_type = file_response.headers.get('content-type', '')
                    if 'image/jpeg' in content_type:
                        filename += '.jpg'
                    elif 'image/png' in content_type:
                        filename += '.png'
                    else:
                        filename += '.dat'
                        
                print(f"Extracted filename: {filename}")
            except Exception as name_error:
                print(f"Error extracting filename, using default: {str(name_error)}")
                filename = f"uploaded_file_{random.randint(10000, 99999)}.dat"
            
            # Prepare files for upload
            files = {
                'file': (filename, file_response.content),
                'upload_to': (None, 'BLOG')
            }
            
            # Upload to API
            upload_response = requests.post(
                UPLOAD_MULTI_URL,
                headers=headers,
                files=files,
                timeout=30
            )
            status_code = upload_response.status_code
            print(f"Uploading file {filename} - Response code: {status_code}")
            
            try:
                response_data = upload_response.json()
                print(f"Response data: {response_data}")
                
                # Các mã 200, 201, 202 đều được coi là thành công
                if status_code in [200, 201, 202]:
                    if 'data' in response_data and isinstance(response_data['data'], list) and len(response_data['data']) > 0:
                        file_data = response_data['data'][0]
                        if 'id' in file_data:
                            file_id = file_data['id']
                            file_ids.append(file_id)
                            print(f"Successfully uploaded file: {filename}, ID: {file_id}")
                        else:
                            print(f"No id field in response data for {filename}: {file_data}")
                    else:
                        print(f"No valid data returned for {filename}: {response_data}")
                else:
                    print(f"Upload failed for {filename}: {status_code}")
            except Exception as parse_error:
                print(f"Error parsing response for {filename}: {str(parse_error)}")
                print(f"Raw response content: {upload_response.content[:200]}")
                
        except Exception as e:
            print(f"Error uploading file {file_url}: {str(e)}")
            continue
    
    return file_ids

def create_news_post(title, content, privacy, file_ids, token):
    """Create news post via API"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {
        "title": title,
        "content": content,
        "privacy": privacy.upper(),
        "file": file_ids
    }
    
    try:
        response = requests.post(
            NEWS_CREATE_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            response_data = response.json()
            news_id = ""
            if 'data' in response_data and 'id' in response_data['data']:
                news_id = response_data['data']['id']
            
            return {
                'success': True,
                'news_id': news_id,
                'response': response_data,
                'status_code': response.status_code
            }
        else:
            return {
                'success': False,
                'news_id': '',
                'response': response.text,
                'status_code': response.status_code
            }
            
    except Exception as e:
        return {
            'success': False,
            'news_id': '',
            'response': str(e),
            'status_code': 0
        }

def create_blog_post(title, content, privacy, file_ids, token):
    """Create blog post via API"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {
        "title": title,
        "content": content,
        "privacy": privacy.upper(),
        "file": file_ids
    }
    
    try:
        response = requests.post(
            BLOG_CREATE_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            response_data = response.json()
            blog_id = ""
            if 'data' in response_data and 'id' in response_data['data']:
                blog_id = response_data['data']['id']
            
            return {
                'success': True,
                'blog_id': blog_id,
                'response': response_data,
                'status_code': response.status_code
            }
        else:
            return {
                'success': False,
                'blog_id': '',
                'response': response.text,
                'status_code': response.status_code
            }
            
    except Exception as e:
        return {
            'success': False,
            'blog_id': '',
            'response': str(e),
            'status_code': 0
        }

def save_news_to_sheet(user_id, title, content, privacy, result):
    """Save news data to Google Sheets"""
    service = get_google_sheets_service()
    if not service:
        return False, "Google Sheets service not available"
    
    # Ensure news sheet exists
    if not ensure_news_sheet_exists(service):
        return False, "Could not create or access news sheet"
    
    try:
        # Set status based on result
        status = "posted" if result["success"] else "failed"
        
        row_data = [
            user_id,
            title,
            content[:500] + "..." if len(content) > 500 else content,  # Truncate content
            privacy,
            result.get("file", ""),  # Original file URLs as string
            status,
            result.get("news_id", "")
        ]
        
        # Append to sheet
        body = {
            'values': [row_data]
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{NEWS_SHEET_NAME}!A:G',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return True, "Saved successfully"
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        return False, f"Error saving to news sheet: {str(e)}"

def save_blog_to_sheet(user_id, title, content, privacy, result):
    """Save blog data to Google Sheets"""
    service = get_google_sheets_service()
    if not service:
        return False, "Google Sheets service not available"
    
    # Ensure blog sheet exists
    if not ensure_blog_sheet_exists(service):
        return False, "Could not create or access blog sheet"
    
    try:
        # Set status based on result
        status = "posted" if result["success"] else "failed"
        
        row_data = [
            user_id,
            title,
            content[:500] + "..." if len(content) > 500 else content,  # Truncate content
            privacy,
            result.get("file", ""),  # Original file URLs as string
            status,
            result.get("blog_id", "")
        ]
        
        # Append to sheet
        body = {
            'values': [row_data]
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{BLOG_SHEET_NAME}!A:G',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return True, "Saved successfully"
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        return False, f"Error saving to blog sheet: {str(e)}"

def get_news_from_sheet():
    """Get all news from Google Sheets"""
    service = get_google_sheets_service()
    if not service:
        return []
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{NEWS_SHEET_NAME}!A:G'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return []
        
        # Skip header row if exists
        news_list = []
        for i, row in enumerate(values):
            if i == 0:  # Always skip first row (header)
                continue
            
            if len(row) >= 1:  # At least user_id
                news_list.append({
                    'user_id': row[0] if len(row) > 0 else '',
                    'title': row[1] if len(row) > 1 else '',
                    'content': row[2] if len(row) > 2 else '',
                    'privacy': row[3] if len(row) > 3 else '',
                    'files': row[4] if len(row) > 4 else '',
                    'status': row[5] if len(row) > 5 else '',
                    'news_id': row[6] if len(row) > 6 else ''
                })
        
        return news_list
    except Exception as e:
        print(f"Error getting news from sheet: {e}")
        return []

def get_blog_from_sheet():
    """Get all blog from Google Sheets"""
    service = get_google_sheets_service()
    if not service:
        return []
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{BLOG_SHEET_NAME}!A:G'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return []
        
        # Skip header row if exists
        blog_list = []
        for i, row in enumerate(values):
            if i == 0:  # Always skip first row (header)
                continue
            
            if len(row) >= 1:  # At least user_id
                blog_list.append({
                    'user_id': row[0] if len(row) > 0 else '',
                    'title': row[1] if len(row) > 1 else '',
                    'content': row[2] if len(row) > 2 else '',
                    'privacy': row[3] if len(row) > 3 else '',
                    'files': row[4] if len(row) > 4 else '',
                    'status': row[5] if len(row) > 5 else '',
                    'blog_id': row[6] if len(row) > 6 else ''
                })
        
        return blog_list
    except Exception as e:
        print(f"Error getting blog from sheet: {e}")
        return []

def process_news_from_sheet(token):
    """Process news posts from sheet - read and post them"""
    service = get_google_sheets_service()
    if not service:
        return {"success": False, "message": "Google Sheets service not available"}
    
    try:
        # Get all data from news sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{NEWS_SHEET_NAME}!A:G'
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return {"success": False, "message": "No data found in news sheet"}
        
        processed_count = 0
        success_count = 0
        results = []
        
        # Process each row (skip header)
        for i, row in enumerate(values):
            if i == 0:  # Skip header
                continue
            
            if len(row) < 2:  # Need at least user_id and title
                continue
                
            user_id = row[0] if len(row) > 0 else ''
            title = row[1] if len(row) > 1 else ''
            content = row[2] if len(row) > 2 else ''
            privacy = row[3] if len(row) > 3 else 'PUBLIC'
            files = row[4] if len(row) > 4 else ''
            status = row[5] if len(row) > 5 else ''
            news_id = row[6] if len(row) > 6 else ''
            
            # Only process rows with "not_upload" status
            if status.lower() != 'not_upload':
                continue
                
            if not title.strip():
                continue
            
            processed_count += 1
            
            # Process file URLs
            file_urls = []
            if files:
                file_urls = [url.strip() for url in files.split(',') if url.strip()]
            
            # Upload files and get IDs
            file_ids = upload_files_to_api(file_urls, token)
            
            # Create news post
            post_result = create_news_post(title, content, privacy, file_ids, token)
            
            # Update status and news_id in sheet
            new_status = "uploaded" if post_result["success"] else "failed"
            new_news_id = post_result.get("news_id", "")
            
            # Update the row in sheet
            update_range = f'{NEWS_SHEET_NAME}!F{i+1}:G{i+1}'
            update_body = {
                'values': [[new_status, new_news_id]]
            }
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=update_range,
                valueInputOption='RAW',
                body=update_body
            ).execute()
            
            if post_result["success"]:
                success_count += 1
            
            results.append({
                "row": i + 1,
                "user_id": user_id,
                "title": title,
                "success": post_result["success"],
                "news_id": new_news_id,
                "file_count": len(file_ids)
            })
        
        return {
            "success": True,
            "message": f"Processed {processed_count} posts, {success_count} successful",
            "processed_count": processed_count,
            "success_count": success_count,
            "results": results
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error processing news: {str(e)}"}

def process_blog_from_sheet(token):
    """Process blog posts from sheet - read and post them"""
    service = get_google_sheets_service()
    if not service:
        return {"success": False, "message": "Google Sheets service not available"}
    
    try:
        # Get all data from blog sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{BLOG_SHEET_NAME}!A:G'
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return {"success": False, "message": "No data found in blog sheet"}
        
        processed_count = 0
        success_count = 0
        results = []
        
        # Process each row (skip header)
        for i, row in enumerate(values):
            if i == 0:  # Skip header
                continue
            
            if len(row) < 2:  # Need at least user_id and title
                continue
                
            user_id = row[0] if len(row) > 0 else ''
            title = row[1] if len(row) > 1 else ''
            content = row[2] if len(row) > 2 else ''
            privacy = row[3] if len(row) > 3 else 'PUBLIC'
            files = row[4] if len(row) > 4 else ''
            status = row[5] if len(row) > 5 else ''
            blog_id = row[6] if len(row) > 6 else ''
            
            # Only process rows with "not_upload" status
            if status.lower() != 'not_upload':
                continue
                
            if not title.strip():
                continue
            
            processed_count += 1
            
            # Process file URLs
            file_urls = []
            if files:
                file_urls = [url.strip() for url in files.split(',') if url.strip()]
            
            # Upload files and get IDs
            file_ids = upload_files_to_api(file_urls, token)
            
            # Create blog post
            post_result = create_blog_post(title, content, privacy, file_ids, token)
            
            # Update status and blog_id in sheet
            new_status = "uploaded" if post_result["success"] else "failed"
            new_blog_id = post_result.get("blog_id", "")
            
            # Update the row in sheet
            update_range = f'{BLOG_SHEET_NAME}!F{i+1}:G{i+1}'
            update_body = {
                'values': [[new_status, new_blog_id]]
            }
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=update_range,
                valueInputOption='RAW',
                body=update_body
            ).execute()
            
            if post_result["success"]:
                success_count += 1
            
            results.append({
                "row": i + 1,
                "user_id": user_id,
                "title": title,
                "success": post_result["success"],
                "blog_id": new_blog_id,
                "file_count": len(file_ids)
            })
        
        return {
            "success": True,
            "message": f"Processed {processed_count} posts, {success_count} successful",
            "processed_count": processed_count,
            "success_count": success_count,
            "results": results
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error processing blog: {str(e)}"}

def update_news_status_in_sheet(row_number, status, news_id=""):
    """Update status and news_id for specific row in news sheet"""
    service = get_google_sheets_service()
    if not service:
        return False, "Google Sheets service not available"
    
    try:
        # Update the status and news_id columns (F and G)
        update_range = f'{NEWS_SHEET_NAME}!F{row_number}:G{row_number}'
        body = {
            'values': [[status, news_id]]
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=update_range,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return True, f"Updated row {row_number} status to {status}"
    
    except Exception as e:
        return False, f"Error updating row {row_number}: {str(e)}"

def update_blog_status_in_sheet(row_number, status, blog_id=""):
    """Update status and blog_id for specific row in blog sheet"""
    service = get_google_sheets_service()
    if not service:
        return False, "Google Sheets service not available"
    
    try:
        # Update the status and blog_id columns (F and G)
        update_range = f'{BLOG_SHEET_NAME}!F{row_number}:G{row_number}'
        body = {
            'values': [[status, blog_id]]
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=update_range,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return True, f"Updated row {row_number} status to {status}"
    
    except Exception as e:
        return False, f"Error updating row {row_number}: {str(e)}"
