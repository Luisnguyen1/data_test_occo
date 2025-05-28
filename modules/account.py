import requests
import random
import string
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

# Google Sheets configuration
SPREADSHEET_ID = '18kYNbaS6RtLV2r2MiqQPm0YqrGQiWYtBhIySyrWlg_M'
SHEET_NAME = 'account'
USER_INFO_SHEET_NAME = 'user_info'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# API endpoints
REGISTER_API_URL = 'http://103.147.186.168:8006/api/v1/auth/user/register/'
LOGIN_API_URL = 'http://103.147.186.168:8006/api/v1/auth/user/login/'
UPDATE_USER_INFO_URL = 'http://103.147.186.168:8006/api/v1/auth/user/update/'

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

def ensure_sheet_exists(service):
    """Ensure the 'account' sheet exists, create if not"""
    try:
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Check if 'account' sheet exists
        account_sheet_exists = any(sheet['properties']['title'] == SHEET_NAME for sheet in sheets)
        
        if not account_sheet_exists:
            # Create the 'account' sheet
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': SHEET_NAME
                    }
                }
            }]
            
            body = {'requests': requests}
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
            
            # Add header row
            header_row = [['Số điện thoại', 'Mật khẩu', 'Trạng thái', 'Phản hồi', 'Thời gian', 'ID']]
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{SHEET_NAME}!A1:F1',
                valueInputOption='RAW',
                body={'values': header_row}
            ).execute()
            
            print(f"Created sheet '{SHEET_NAME}' with headers")
        
        return True
    except Exception as e:
        print(f"Error ensuring sheet exists: {e}")
        return False

def ensure_user_info_sheet_exists(service):
    """Ensure the 'user_info' sheet exists, create if not"""
    try:
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Check if 'user_info' sheet exists
        user_info_sheet_exists = any(sheet['properties']['title'] == USER_INFO_SHEET_NAME for sheet in sheets)
        
        if not user_info_sheet_exists:
            # Create the 'user_info' sheet
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': USER_INFO_SHEET_NAME
                    }
                }
            }]
            
            body = {'requests': requests}
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
            
            # Add header row for user_info - correct order and columns
            header_row = [['Account ID', 'Full Name', 'Bio', 'Email', 'Date of Birth', 'Gender', 'Height', 'Weight', 'Country', 'Province', 'Lat', 'Lng', 'Language Code', 'Response', 'Timestamp', 'Avatar', 'Tình trạng']]
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{USER_INFO_SHEET_NAME}!A1:Q1',
                valueInputOption='RAW',
                body={'values': header_row}
            ).execute()
            
            print(f"Created sheet '{USER_INFO_SHEET_NAME}' with headers")
        
        return True
    except Exception as e:
        print(f"Error ensuring user_info sheet exists: {e}")
        return False

def generate_random_phone():
    """Generate a random Vietnamese phone number"""
    # Vietnamese phone number format: +84 + 9 digits
    # Common prefixes: 91, 96, 97, 98, 32, 33, 34, 35, 36, 37, 38, 39
    prefixes = ['91', '96', '97', '98', '32', '33', '34', '35', '36', '37', '38', '39']
    prefix = random.choice(prefixes)
    remaining_digits = ''.join(random.choices(string.digits, k=7))
    return f"+84{prefix}{remaining_digits}"

def generate_random_password():
    """Generate a random password"""
    # Simple password for testing
    return "123456"

def create_account():
    """Create a new account via API"""
    phone = generate_random_phone()
    password = generate_random_password()
    
    payload = {
        "phone_number": phone,
        "password": password
    }
    
    # Headers để tránh lỗi DisallowedHost - sử dụng localhost pretend
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Host': 'localhost:8006',
        'X-Real-IP': '127.0.0.1',
        'X-Forwarded-For': '127.0.0.1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.post(
            REGISTER_API_URL, 
            json=payload, 
            headers=headers,
            timeout=10
        )
        
        # Xử lý response dựa trên status code
        account_id = ""
        if response.status_code == 200 or response.status_code == 201:
            try:
                # Thử parse JSON response để lấy thông tin chi tiết
                response_data = response.json()
                if 'message' in response_data:
                    response_text = response_data['message']
                else:
                    response_text = "Account created successfully"
                    
                # Trích xuất ID từ response
                if 'data' in response_data and 'id' in response_data['data']:
                    account_id = response_data['data']['id']
                
                status = "created"
            except:
                response_text = "Account created successfully"
                status = "created"
        elif response.status_code == 400:
            # Kiểm tra nếu có thông tin chi tiết trong response
            try:
                error_data = response.json()
                if 'phone_number' in error_data:
                    response_text = "Phone number already exists"
                    status = "not_created"
                else:
                    response_text = "Bad request - validation error"
                    status = "not_created"
            except:
                response_text = "Bad request - phone number may already exist"
                status = "not_created"
        elif response.status_code == 403:
            response_text = "Access denied - DisallowedHost error"
            status = "not_created"
        elif response.status_code == 500:
            response_text = "Server internal error"
            status = "not_created"
        else:
            # Cắt ngắn response text để tránh lỗi Google Sheets
            error_text = response.text[:300] if response.text else "Unknown error"
            response_text = f"HTTP {response.status_code}: {error_text}"
            status = "not_created"
            
        return {
            "phone_number": phone,
            "password": password,
            "status": status,
            "response": response_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account_id": account_id
        }    
    except requests.exceptions.Timeout:
        return {
            "phone_number": phone,
            "password": password,
            "status": "not_created",
            "response": "Request timeout after 10 seconds",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account_id": ""
        }
    except requests.exceptions.ConnectionError:
        return {
            "phone_number": phone,
            "password": password,
            "status": "not_created",
            "response": "Could not connect to registration API",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account_id": ""
        }
    except Exception as e:
        return {
            "phone_number": phone,
            "password": password,
            "status": "not_created",
            "response": str(e)[:200],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account_id": ""
        }

def save_to_sheet(account_data):
    """Save account data to Google Sheets"""
    service = get_google_sheets_service()
    if not service:
        return False, "Google Sheets service not available"
    
    # Ensure sheet exists
    if not ensure_sheet_exists(service):
        return False, "Could not create or access sheet"
    
    try:
        # Prepare data row - truncate response if too long
        response_text = str(account_data["response"])
        if len(response_text) > 1000:  # Limit response to 1000 characters
            response_text = response_text[:997] + "..."
            
        row_data = [
            account_data["phone_number"],
            account_data["password"],
            str(account_data["status"]),
            response_text,
            account_data["timestamp"],
            account_data.get("account_id", "")
        ]
        
        # Append to sheet
        body = {
            'values': [row_data]
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:F',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return True, "Saved successfully"
    except Exception as e:
        print(f"Detailed error: {str(e)}")  # For debugging
        return False, f"Error saving to sheet: {str(e)}"

def get_accounts_from_sheet():
    """Get all accounts from Google Sheets"""
    service = get_google_sheets_service()
    if not service:
        return []
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:F'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return []
          # Skip header row if exists
        accounts = []
        for i, row in enumerate(values):
            if i == 0:  # Always skip first row (header)
                continue
            
            if len(row) >= 5:
                user_id = row[5] if len(row) > 5 else ""
                accounts.append({
                    'phone_number': row[0],
                    'password': row[1],
                    'status': row[2],
                    'response': row[3],
                    'timestamp': row[4],
                    'id': user_id,  # Thêm key 'id' để khớp với JavaScript
                    'account_id': user_id  # Giữ lại key cũ để backward compatibility
                })
        
        return accounts
    except Exception as e:
        print(f"Error getting accounts from sheet: {e}")
        return []

def get_accounts_with_created_status():
    """Get accounts that have been created successfully"""
    service = get_google_sheets_service()
    if not service:
        return []
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:F'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return []
          # Skip header row and filter created accounts
        created_accounts = []
        for i, row in enumerate(values):
            if i == 0:  # Skip header
                continue
                
            if len(row) >= 6 and row[2] == 'created' and row[5]:  # status is 'created' and has account_id
                user_id = row[5]
                created_accounts.append({
                    'phone_number': row[0],
                    'password': row[1],  # Thêm password để có thể login
                    'id': user_id,  # Thêm key 'id' để khớp với JavaScript
                    'account_id': user_id,  # Giữ lại để backward compatibility
                    'timestamp': row[4]
                })
        
        return created_accounts
    except Exception as e:
        print(f"Error getting created accounts: {e}")
        return []

def get_token_for_account(account_id):
    """Get token for account by logging in with stored credentials"""
    service = get_google_sheets_service()
    if not service:
        return None
    
    try:
        # Get account data from Google Sheets
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:F'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None
        
        # Find account by account_id
        phone_number = None
        password = None
        for i, row in enumerate(values):
            if i == 0:  # Skip header
                continue
            if len(row) >= 6 and row[5] == account_id:  # account_id is in column F (index 5)
                phone_number = row[0]  # column A
                password = row[1]      # column B
                break
        
        if not phone_number or not password:
            print(f"No credentials found for account_id: {account_id}")
            return None
        
        # Login to get token
        login_data = {
            'phone_number': phone_number,
            'password': password,
            'platform': 'ANDROID',
            'device_token': 'fGyH6vLm90c:APA91bH_F_lpVy9yWx3H8s9DzRmH7Vq6PwF5Vu1ZkZo9KcY8eQhGmX1V4Ue4VdX1T2Ue3WbAfMrS8rQyMgV_C7R9bVhWmWzH1VvF6N2Tzx',
            'device_name': 'ANDROID REDMI NOTE12'
        }
        
        headers = {
            'Host': 'localhost:8006',
            'X-Real-IP': '127.0.0.1',
            'X-Forwarded-For': '127.0.0.1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(LOGIN_API_URL, json=login_data, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract token from response
            if 'access_token' in response_data:
                return response_data['access_token']
            elif 'data' in response_data and 'access_token' in response_data['data']:
                return response_data['data']['access_token']
            elif 'token' in response_data:
                return response_data['token']
            else:
                print(f"No token found in login response: {response_data}")
                return None
        else:
            print(f"Login failed for account {account_id}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting token for account {account_id}: {str(e)}")
        return None

def generate_random_user_info():
    """Generate random user information"""
    vietnamese_names = [
        "Nguyễn Văn Minh", "Trần Thị Hoa", "Lê Văn Nam", "Phạm Thị Lan", "Hoàng Văn Dũng",
        "Vũ Thị Mai", "Đỗ Văn Hưng", "Bùi Thị Linh", "Ngô Văn Tùng", "Đặng Thị Hương",
        "Lý Văn Khoa", "Đinh Thị Nga", "Võ Văn Thắng", "Trương Thị Kim", "Phan Văn Long"
    ]
    
    vietnamese_bios = [
        "Yêu thích du lịch và khám phá", "Đam mê công nghệ", "Thích ẩm thực Việt Nam",
        "Yêu thể thao và sức khỏe", "Người yêu thiên nhiên", "Đam mê nhiếp ảnh",
        "Thích đọc sách và học hỏi", "Yêu âm nhạc và nghệ thuật", "Đam mê kinh doanh",
        "Thích giao lưu kết bạn"
    ]
    
    vietnamese_provinces = [
        "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ",
        "Nghệ An", "Thanh Hóa", "Thừa Thiên Huế", "Quảng Nam", "Bình Dương",
        "Đồng Nai", "Khánh Hòa", "Lâm Đồng", "Bà Rịa - Vũng Tàu", "An Giang"
    ]
    
    # Generate random data
    full_name = random.choice(vietnamese_names)
    bio = random.choice(vietnamese_bios)
    email = f"user{random.randint(1000, 9999)}@gmail.com"
    
    # Random date of birth (age 18-40)
    year = random.randint(1984, 2006)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    date_of_birth = f"{year}-{month:02d}-{day:02d}"
    
    gender = random.choice(["MALE", "FEMALE"])
    height = str(random.randint(150, 190))
    weight = str(random.randint(45, 90))
    country = "Vietnam"
    province = random.choice(vietnamese_provinces)
    
    # Random coordinates for Vietnam
    lat = f"{random.uniform(8.0, 23.4):.4f}"
    lng = f"{random.uniform(102.0, 109.5):.4f}"
    language_code = "vi"
    
    return {
        "full_name": full_name,
        "bio": bio,
        "email": email,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "height": height,
        "weight": weight,
        "country": country,
        "province": province,
        "lat": lat,
        "lng": lng,
        "language_code": language_code
    }

def update_user_info_api(account_id, token, user_info, avatar_url=None):
    """Update user info via API with multipart form data including avatar"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Host': 'localhost:8006',
        'X-Real-IP': '127.0.0.1',
        'X-Forwarded-For': '127.0.0.1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Prepare form data
    form_data = {
        'full_name': user_info['full_name'],
        'bio': user_info['bio'],
        'email': user_info['email'],
        'date_of_birth': user_info['date_of_birth'],
        'gender': user_info['gender'],
        'height': user_info['height'],
        'weight': user_info['weight'],
        'country': user_info['country'],
        'province': user_info['province'],
        'lat': user_info['lat'],
        'lng': user_info['lng'],
        'language_code': user_info['language_code']
    }
    
    files = {}
    
    # Handle avatar upload if URL is provided
    if avatar_url and avatar_url.strip():
        try:
            # Download image from URL
            avatar_response = requests.get(avatar_url, timeout=30)
            if avatar_response.status_code == 200:
                # Get file extension from URL or content type
                content_type = avatar_response.headers.get('content-type', '')
                if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                    ext = '.jpg'
                elif 'image/png' in content_type:
                    ext = '.png'
                elif 'image/gif' in content_type:
                    ext = '.gif'
                else:
                    ext = '.jpg'  # Default
                
                # Create file-like object for upload
                import io
                avatar_file = io.BytesIO(avatar_response.content)
                files['avatar'] = (f'avatar{ext}', avatar_file, content_type)
            else:
                print(f"Failed to download avatar from {avatar_url}: {avatar_response.status_code}")
        except Exception as e:
            print(f"Error downloading avatar from {avatar_url}: {str(e)}")
    
    try:
        if files:
            # Use multipart form data with files
            response = requests.put(
                UPDATE_USER_INFO_URL,
                data=form_data,
                files=files,
                headers=headers,
                timeout=30
            )
        else:
            # Use regular form data without files
            response = requests.put(
                UPDATE_USER_INFO_URL,
                data=form_data,
                headers=headers,
                timeout=30
            )
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                return {
                    "success": True,
                    "status": "updated",
                    "response": response_data.get('message', 'User info updated successfully'),
                    "data": response_data
                }
            except:
                return {
                    "success": True,
                    "status": "updated", 
                    "response": "User info updated successfully",
                    "data": None
                }
        else:
            return {
                "success": False,
                "status": "not_updated",
                "response": f"HTTP {response.status_code}: {response.text[:200]}",
                "data": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "response": str(e)[:200],
            "data": None
        }

def save_user_info_to_sheet(account_id, user_info, update_result, avatar_url=None, update_status="not_update"):
    """Save user info data to Google Sheets with Avatar and Tình trạng columns"""
    service = get_google_sheets_service()
    if not service:
        return False, "Google Sheets service not available"
    
    # Ensure user_info sheet exists
    if not ensure_user_info_sheet_exists(service):
        return False, "Could not create or access user_info sheet"
    
    try:
        # Prepare data row
        response_text = str(update_result["response"])
        if len(response_text) > 1000:
            response_text = response_text[:997] + "..."
            
        # Set tình trạng status based on update result
        tinh_trang = "updated" if update_result["success"] else "not_update"
            
        row_data = [
            account_id,
            user_info["full_name"],
            user_info["bio"],
            user_info["email"],
            user_info["date_of_birth"],
            user_info["gender"],
            user_info["height"],
            user_info["weight"],
            user_info["country"],
            user_info["province"],
            user_info["lat"],
            user_info["lng"],
            user_info["language_code"],
            response_text,                      # Response column (N)
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp column (O)
            avatar_url or "",                   # Avatar column (P)
            tinh_trang                          # Tình trạng column (Q)
        ]
        
        # Append to sheet
        body = {
            'values': [row_data]
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{USER_INFO_SHEET_NAME}!A:Q',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return True, "Saved successfully"
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        return False, f"Error saving to user_info sheet: {str(e)}"

def get_user_info_data_from_sheet():
    """Get existing user info data from Google Sheets including Avatar and Tình trạng columns"""
    service = get_google_sheets_service()
    if not service:
        return []
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{USER_INFO_SHEET_NAME}!A:Q'  # Extended range to include Avatar and Tình trạng
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:  # No data or only header
            return []
        
        # Skip header row and process data
        user_info_list = []
        headers = values[0] if values else []
        for i, row in enumerate(values):
            if i == 0:  # Skip header
                continue
                
            # Only require account_id to load the row
            if len(row) > 0 and row[0].strip():  # Has account_id and it's not empty
                user_info = {
                    'account_id': row[0] if len(row) > 0 else '',
                    'full_name': row[1] if len(row) > 1 else '',
                    'bio': row[2] if len(row) > 2 else '',
                    'email': row[3] if len(row) > 3 else '',
                    'date_of_birth': row[4] if len(row) > 4 else '',
                    'gender': row[5] if len(row) > 5 else '',
                    'height': row[6] if len(row) > 6 else '',
                    'weight': row[7] if len(row) > 7 else '',
                    'country': row[8] if len(row) > 8 else '',
                    'province': row[9] if len(row) > 9 else '',
                    'lat': row[10] if len(row) > 10 else '',
                    'lng': row[11] if len(row) > 11 else '',
                    'language_code': row[12] if len(row) > 12 else '',
                    'response': row[13] if len(row) > 13 else '',      # Response column (N)
                    'timestamp': row[14] if len(row) > 14 else '',     # Timestamp column (O)
                    'avatar': row[15] if len(row) > 15 else '',        # Avatar column (P)
                    'tinh_trang': row[16] if len(row) > 16 else ''     # Tình trạng column (Q)
                }
                user_info_list.append(user_info)
        
        return user_info_list
    except Exception as e:
        print(f"Error getting user info data: {e}")
        return []

def generate_smart_user_info(existing_user_info=None):
    """Generate user info, keeping existing data and only filling empty fields"""
    # Start with existing data or empty dict
    user_info = existing_user_info.copy() if existing_user_info else {}
    
    # Generate random data for missing fields
    random_data = generate_random_user_info()
    
    # Only fill fields that are empty or missing
    for key, value in random_data.items():
        if key not in user_info or not user_info[key] or user_info[key].strip() == '':
            user_info[key] = value
    
    return user_info

def update_existing_user_info_row(account_id, user_info, update_result, avatar_url=None):
    """Update existing user info row instead of creating new one"""
    service = get_google_sheets_service()
    if not service:
        return False, "Google Sheets service not available"
    
    try:
        # Get all data from sheet to find the row
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{USER_INFO_SHEET_NAME}!A:Q'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return False, "No data found in sheet"
        
        # Find the row with matching account_id
        row_index = None
        for i, row in enumerate(values):
            if i == 0:  # Skip header
                continue
            if len(row) > 0 and row[0] == account_id:
                row_index = i + 1  # Google Sheets is 1-indexed
                break
        
        if row_index is None:
            # If account not found, create new row
            return save_user_info_to_sheet(account_id, user_info, update_result, avatar_url)
        
        # Prepare response text
        response_text = str(update_result["response"])
        if len(response_text) > 1000:
            response_text = response_text[:997] + "..."
        
        # Set tình trạng status based on update result
        tinh_trang = "updated" if update_result["success"] else "failed"
        
        # Update entire row data
        row_data = [
            account_id,
            user_info["full_name"],
            user_info["bio"],
            user_info["email"],
            user_info["date_of_birth"],
            user_info["gender"],
            user_info["height"],
            user_info["weight"],
            user_info["country"],
            user_info["province"],
            user_info["lat"],
            user_info["lng"],
            user_info["language_code"],
            response_text,                      # Response column (N)
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp column (O)
            avatar_url or "",                   # Avatar column (P)
            tinh_trang                          # Tình trạng column (Q)
        ]
        
        # Update the entire row
        update_range = f'{USER_INFO_SHEET_NAME}!A{row_index}:Q{row_index}'
        body = {
            'values': [row_data]
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=update_range,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return True, "Updated existing row successfully"
    
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        return False, f"Error updating existing row: {str(e)}"

def get_accounts_need_update():
    """Get accounts that need update (Tình trạng = 'not_update')"""
    user_info_data = get_user_info_data_from_sheet()
    accounts_need_update = []
    
    for info in user_info_data:
        if info.get('tinh_trang', '').lower() == 'not_update':
            accounts_need_update.append(info)
    
    return accounts_need_update

def process_selective_update():
    """Process update for accounts with Tình trạng = 'not_update'"""
    try:
        # Get accounts that need update
        accounts_need_update = get_accounts_need_update()
        
        if not accounts_need_update:
            return {
                "success": True,
                "message": "No accounts found with 'not_update' status",
                "results": [],
                "total_processed": 0,
                "total_successful": 0,
                "total_failed": 0
            }
        
        results = []
        success_count = 0
        failed_count = 0
        
        for user_info in accounts_need_update:
            account_id = user_info['account_id']
            avatar_url = user_info.get('avatar', '')
            
            try:
                # Get token for this account
                token = get_token_for_account(account_id)
                
                if not token:
                    result = {
                        "account_id": account_id,
                        "success": False,
                        "message": "Could not get token for account",
                        "update_result": None
                    }
                    failed_count += 1
                else:
                    # Prepare user info for API call (exclude meta fields)
                    api_user_info = {
                        'full_name': user_info.get('full_name', ''),
                        'bio': user_info.get('bio', ''),
                        'email': user_info.get('email', ''),
                        'date_of_birth': user_info.get('date_of_birth', ''),
                        'gender': user_info.get('gender', ''),
                        'height': user_info.get('height', ''),
                        'weight': user_info.get('weight', ''),
                        'country': user_info.get('country', ''),
                        'province': user_info.get('province', ''),
                        'lat': user_info.get('lat', ''),
                        'lng': user_info.get('lng', ''),
                        'language_code': user_info.get('language_code', '')
                    }
                    
                    # Update via API
                    update_result = update_user_info_api(account_id, token, api_user_info, avatar_url)
                    
                    # Update existing row instead of creating new one
                    row_updated, row_message = update_existing_user_info_row(account_id, api_user_info, update_result, avatar_url)
                    
                    result = {
                        "account_id": account_id,
                        "success": update_result["success"],
                        "message": update_result["response"],
                        "update_result": update_result,
                        "row_updated": row_updated,
                        "row_message": row_message,
                        "user_info": api_user_info,
                        "avatar_url": avatar_url
                    }
                    
                    if update_result["success"]:
                        success_count += 1
                    else:
                        failed_count += 1
                
                results.append(result)
                
            except Exception as e:
                result = {
                    "account_id": account_id,
                    "success": False,
                    "message": f"Error processing account: {str(e)}",
                    "update_result": None
                }
                results.append(result)
                failed_count += 1
        
        return {
            "success": True,
            "message": f"Processed {len(accounts_need_update)} accounts: {success_count} successful, {failed_count} failed",
            "results": results,
            "total_processed": len(accounts_need_update),
            "total_successful": success_count,
            "total_failed": failed_count
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error in selective update process: {str(e)}",
            "results": [],
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0
        }
